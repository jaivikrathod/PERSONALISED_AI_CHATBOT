"""Knowledge API: the backend for the Phase 4 Knowledge screen.

    GET/POST /api/knowledge-sources/                  list, create {name, kind: document|text}
    POST     /api/knowledge-sources/{id}/upload/      multipart `file` → 202 + job (200 if unchanged)
    POST     /api/knowledge-sources/{id}/text/        {title, content} → 202 + job
    GET      /api/knowledge-sources/{id}/documents/
    DELETE   /api/knowledge-documents/{id}/
    GET      /api/ingestion-jobs/?source=<id>         progress polling

FAQ pairs are still authored at /api/questions/ and mirrored automatically.
"""

from django.utils.text import slugify
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from config.tenancy import CompanyScopedQuerysetMixin, require_company
from orchestration.orchestrator import resolve_chatbot
from users.permissions import IsAdminOrManager

from .extraction import SUPPORTED_TYPES, file_type_for
from .ingest import submit_document
from .models import IngestionJob, KnowledgeDocument, KnowledgeSource
from .serializers import IngestionJobSerializer, KnowledgeDocumentSerializer, KnowledgeSourceSerializer

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class KnowledgeSourceViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = KnowledgeSource.objects.all()
    serializer_class = KnowledgeSourceSerializer
    permission_classes = [IsAdminOrManager]

    def perform_create(self, serializer):
        company_id = require_company(self.request)
        chatbot = resolve_chatbot(company_id)
        if chatbot is None:
            raise ValidationError("Your company has no active chatbot.")
        serializer.save(company_id=company_id, chatbot=chatbot)

    def perform_destroy(self, instance):
        if instance.kind == KnowledgeSource.Kind.FAQ:
            raise ValidationError("The FAQ source is managed from the Knowledge Base questions.")
        instance.delete()

    def _writable(self):
        source = self.get_object()
        if source.kind == KnowledgeSource.Kind.FAQ:
            raise ValidationError("Add FAQ pairs from the Knowledge Base questions instead.")
        return source

    def _queued(self, source, filename, content):
        document, job = submit_document(source, filename, content)
        if job is None:
            return Response({"unchanged": True, "document": KnowledgeDocumentSerializer(document).data})
        return Response(
            {"unchanged": False, "document": KnowledgeDocumentSerializer(document).data, "job": IngestionJobSerializer(job).data},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def upload(self, request, pk=None):
        source = self._writable()
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "Upload a file as `file`."}, status=400)
        if file_type_for(upload.name) is None:
            return Response({"detail": f"Unsupported file type. Use one of {sorted(SUPPORTED_TYPES)}."}, status=400)
        if upload.size > MAX_UPLOAD_BYTES:
            return Response({"detail": "File is larger than 20 MB."}, status=400)
        return self._queued(source, upload.name[:255], upload.read())

    @action(detail=True, methods=["post"])
    def text(self, request, pk=None):
        source = self._writable()
        title = (request.data.get("title") or "").strip()
        content = (request.data.get("content") or "").strip()
        if not title or not content:
            return Response({"detail": "title and content are required."}, status=400)
        filename = f"{slugify(title)[:200] or 'text'}.md"
        return self._queued(source, filename, f"# {title}\n\n{content}".encode())

    @action(detail=True, methods=["get"])
    def documents(self, request, pk=None):
        source = self.get_object()
        return Response(KnowledgeDocumentSerializer(source.documents.all(), many=True).data)


class KnowledgeDocumentViewSet(mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [IsAdminOrManager]

    def get_queryset(self):
        return KnowledgeDocument.objects.filter(source__company_id=require_company(self.request))

    def perform_destroy(self, instance):
        if instance.source.kind == KnowledgeSource.Kind.FAQ:
            raise ValidationError("Delete the question from the Knowledge Base instead.")
        instance.delete()


class IngestionJobViewSet(CompanyScopedQuerysetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = IngestionJob.objects.defer("payload")
    serializer_class = IngestionJobSerializer
    permission_classes = [IsAdminOrManager]

    def get_queryset(self):
        queryset = super().get_queryset()
        source = self.request.query_params.get("source")
        return queryset.filter(source_id=source) if source else queryset
