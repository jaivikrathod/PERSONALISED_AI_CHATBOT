"""Data-source API: the backend the Phase 4 "Connect data" screens call.

    POST   /api/data-sources/                      create {display_name, description}
    POST   /api/data-sources/{id}/import/          multipart file (CSV/JSON), mode
    GET    /api/data-sources/{id}/fields/          inferred schema, cardinality, values
    PATCH  /api/data-source-fields/{id}/           confirm or correct one field
    POST   /api/data-sources/{id}/confirm-schema/  a human accepted the types
    POST   /api/data-sources/{id}/publish/         checks → indexes → search tool
    POST   /api/data-sources/{id}/unpublish/
    GET    /api/data-sources/{id}/declaration/     "what the AI sees"
    GET    /api/data-sources/{id}/syncs/           import history

Tenancy comes from the token (A3); the chatbot is the caller's company's bot.
"""

from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from config.tenancy import CompanyScopedQuerysetMixin, require_company
from orchestration.orchestrator import resolve_chatbot
from registry.models import Tool
from users.permissions import IsAdminOrManager

from .declarations import DeclarationError, compile_input_schema, tool_description
from .ingest import import_records
from .models import DataSource, DataSourceField, DataSourceSync
from .publishing import PublishError, publish, unpublish
from .serializers import (
    DataSourceFieldSerializer,
    DataSourceSerializer,
    DataSourceSyncSerializer,
    unique_source_name,
)


class DataSourceViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = DataSource.objects.select_related("chatbot")
    serializer_class = DataSourceSerializer
    permission_classes = [IsAdminOrManager]

    def perform_create(self, serializer):
        company_id = require_company(self.request)
        chatbot = resolve_chatbot(company_id)
        if chatbot is None:
            raise ValidationError("Your company has no active chatbot.")
        name = serializer.validated_data.get("name") or unique_source_name(
            chatbot, serializer.validated_data["display_name"]
        )
        serializer.save(company_id=company_id, chatbot=chatbot, name=name)

    def perform_destroy(self, instance):
        Tool.objects.filter(
            chatbot=instance.chatbot,
            tool_type=Tool.ToolType.STRUCTURED_SEARCH,
            configuration__data_source_id=instance.id,
        ).delete()
        instance.delete()

    @action(detail=True, methods=["post"], url_path="import")
    def import_data(self, request, pk=None):
        source = self.get_object()
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "Upload a CSV or JSON file as `file`."}, status=400)
        mode = request.data.get("mode") or DataSourceSync.Mode.UPSERT
        if mode not in DataSourceSync.Mode.values:
            return Response({"detail": f"mode must be one of {DataSourceSync.Mode.values}."}, status=400)

        sync = import_records(source, upload.name, upload.read(), mode=mode)
        source.refresh_from_db()
        ok = source.sync_status != DataSource.SyncStatus.FAILED
        return Response(
            {
                "sync": DataSourceSyncSerializer(sync).data,
                "data_source": DataSourceSerializer(source).data,
                "fields": DataSourceFieldSerializer(source.fields.all(), many=True).data,
            },
            status=status.HTTP_201_CREATED if ok else status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["get"])
    def fields(self, request, pk=None):
        source = self.get_object()
        return Response(DataSourceFieldSerializer(source.fields.all(), many=True).data)

    @action(detail=True, methods=["get"])
    def syncs(self, request, pk=None):
        source = self.get_object()
        return Response(DataSourceSyncSerializer(source.syncs.all()[:20], many=True).data)

    @action(detail=True, methods=["post"], url_path="confirm-schema")
    def confirm_schema(self, request, pk=None):
        source = self.get_object()
        if source.row_count == 0:
            return Response({"detail": "Import data before confirming its schema."}, status=400)
        source.schema_confirmed_at = timezone.now()
        source.save(update_fields=["schema_confirmed_at", "updated_at"])
        return Response(DataSourceSerializer(source).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        source = self.get_object()
        try:
            tool = publish(source)
        except PublishError as exc:
            return Response({"errors": exc.errors}, status=400)
        source.refresh_from_db()
        return Response({"data_source": DataSourceSerializer(source).data, "tool": tool.declaration()})

    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        source = self.get_object()
        unpublish(source)
        source.refresh_from_db()
        return Response(DataSourceSerializer(source).data)

    @action(detail=True, methods=["get"])
    def declaration(self, request, pk=None):
        source = self.get_object()
        try:
            parameters = compile_input_schema(
                source, source.fields.all(), max_rows=source.chatbot.get_policy("max_rows_returned")
            )
        except DeclarationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            {"name": source.tool_name, "description": tool_description(source), "parameters": parameters}
        )


class DataSourceFieldViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Fields are created by import, never by hand; they are reviewed here."""

    serializer_class = DataSourceFieldSerializer
    permission_classes = [IsAdminOrManager]

    def get_queryset(self):
        queryset = DataSourceField.objects.select_related("data_source").filter(
            data_source__company_id=require_company(self.request)
        )
        data_source = self.request.query_params.get("data_source")
        if data_source:
            queryset = queryset.filter(data_source_id=data_source)
        return queryset
