"""Knowledge base CRUD, bulk upload, and search endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.mixins import CompanyCreateMixin, CompanyScopedQuerysetMixin

from .models import KnowledgeBase, QuestionAnswer
from .permissions import CanEditKnowledgeBase
from .serializers import (
    BulkUploadSerializer,
    FaqSerializer,
    KnowledgeBaseSerializer,
    QuestionAnswerSerializer,
    SearchSerializer,
)
from .services import BulkUploadService, SearchService
from .tasks import generate_embeddings_for_kb


def _default_knowledge_base(company_id):
    """Return (creating on first use) a company's catch-all knowledge base.

    The dashboard presents FAQs as one flat list with no notion of KB
    containers, so every FAQ created there is filed under a single auto-managed
    "General" knowledge base per company.
    """
    kb, _ = KnowledgeBase.objects.get_or_create(
        company_id=company_id,
        title="General",
        defaults={"description": "Default knowledge base for dashboard FAQs."},
    )
    return kb


@extend_schema(tags=["knowledge-base"])
class KnowledgeBaseViewSet(
    CompanyScopedQuerysetMixin, CompanyCreateMixin, viewsets.ModelViewSet
):
    queryset = KnowledgeBase.objects.select_related("company").all()
    serializer_class = KnowledgeBaseSerializer
    permission_classes = [IsAuthenticated, CanEditKnowledgeBase]
    lookup_field = "uuid"
    search_fields = ["title", "description"]
    filterset_fields = ["is_active"]

    @action(detail=False, methods=["post"])
    def search(self, request):
        """Semantic search across this company's FAQ entries."""
        serializer = SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = SearchService(company_id=request.user.company_id)
        results = service.semantic_search(
            serializer.validated_data["query"],
            top_k=serializer.validated_data["top_k"],
        )
        return Response({"success": True, "results": results})


@extend_schema(tags=["knowledge-base"])
class QuestionAnswerViewSet(
    CompanyScopedQuerysetMixin, viewsets.ModelViewSet
):
    """CRUD for FAQ pairs. Embeddings are generated asynchronously on save."""

    queryset = QuestionAnswer.objects.select_related("knowledge_base").all()
    serializer_class = QuestionAnswerSerializer
    permission_classes = [IsAuthenticated, CanEditKnowledgeBase]
    company_field = "knowledge_base__company"
    lookup_field = "uuid"
    search_fields = ["question", "answer"]
    filterset_fields = ["knowledge_base__uuid", "embedding_status"]

    def perform_create(self, serializer):
        # Tenant safety: the chosen KB must belong to the caller's company.
        kb = serializer.validated_data["knowledge_base"]
        user = self.request.user
        if not user.is_super_admin and kb.company_id != user.company_id:
            from core.exceptions import TenantIsolationError

            raise TenantIsolationError()
        serializer.save()

    @extend_schema(request=BulkUploadSerializer)
    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def bulk_upload(self, request):
        """Upload a CSV/Excel of question,answer rows into a knowledge base."""
        serializer = BulkUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kb = serializer.validated_data["knowledge_base"]
        user = request.user
        if not user.is_super_admin and kb.company_id != user.company_id:
            return Response(
                {"success": False, "message": "Knowledge base belongs to another company."},
                status=status.HTTP_403_FORBIDDEN,
            )

        upload = serializer.validated_data["file"]
        try:
            created = BulkUploadService(kb).ingest(upload, upload.name)
        except ValueError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Kick off embedding generation for the freshly imported rows.
        generate_embeddings_for_kb.delay(kb.id)

        return Response(
            {"success": True, "imported": len(created)},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["knowledge-base"])
class FaqViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """Flat FAQ CRUD backing the dashboard Knowledge Base page.

    Exposes QuestionAnswer rows as simple {id, question, answer} records and
    auto-files new rows under the company's default knowledge base, so the UI
    never has to deal with KB containers. Search via ?search=, paginate via
    ?page=&page_size=.
    """

    queryset = QuestionAnswer.objects.select_related("knowledge_base").all()
    serializer_class = FaqSerializer
    permission_classes = [IsAuthenticated, CanEditKnowledgeBase]
    company_field = "knowledge_base__company"
    search_fields = ["question", "answer"]

    def perform_create(self, serializer):
        kb = _default_knowledge_base(self.request.user.company_id)
        serializer.save(knowledge_base=kb)

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def bulk_upload(self, request):
        """Import a CSV/Excel of question,answer rows into the default KB."""
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"success": False, "message": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not upload.name.lower().endswith((".csv", ".xlsx", ".xls")):
            return Response(
                {"success": False, "message": "Only CSV or Excel files are accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        kb = _default_knowledge_base(request.user.company_id)
        try:
            created = BulkUploadService(kb).ingest(upload, upload.name)
        except ValueError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        generate_embeddings_for_kb.delay(kb.id)
        return Response(
            {"success": True, "imported": len(created)},
            status=status.HTTP_201_CREATED,
        )
