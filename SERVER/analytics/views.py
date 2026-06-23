"""Analytics dashboard + unanswered-question curation endpoints."""

from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.enums import UserRole
from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import HasCompanyRole

from .models import ConversationMetrics, UnansweredQuestion
from .serializers import (
    ConversationMetricsSerializer,
    ConvertToFaqSerializer,
    UnansweredQuestionSerializer,
)
from .services import (
    compute_daily_metrics,
    conversations_series,
    convert_unanswered_to_faq,
    overview_metrics,
    top_faqs,
)


def _resolve_company_id(request):
    """Return the company id to scope analytics to, or a 400 Response.

    Mirrors the tenant rules used elsewhere: regular users are pinned to their
    own company; a SUPER_ADMIN must pass ?company=<uuid>.
    """
    user = request.user
    if user.company_id is not None:
        return user.company_id, None
    if user.role == UserRole.SUPER_ADMIN:
        company_uuid = request.query_params.get("company")
        if not company_uuid:
            return None, Response(
                {"success": False, "message": "Provide ?company=<uuid>."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from companies.models import Company

        try:
            return Company.objects.values_list("id", flat=True).get(uuid=company_uuid), None
        except Company.DoesNotExist:
            return None, Response(
                {"success": False, "message": "Unknown company."},
                status=status.HTTP_404_NOT_FOUND,
            )
    return None, Response(
        {"success": False, "message": "User is not bound to a company."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _parse_date(value):
    """Parse an ISO date (YYYY-MM-DD); return None on missing/invalid input."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@extend_schema(tags=["analytics"])
class OverviewView(APIView):
    """GET /analytics/overview/?from=&to= — KPI cards for the dashboard."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company_id, err = _resolve_company_id(request)
        if err:
            return err
        return Response(
            overview_metrics(
                company_id,
                date_from=_parse_date(request.query_params.get("from")),
                date_to=_parse_date(request.query_params.get("to")),
            )
        )


@extend_schema(tags=["analytics"])
class ConversationsSeriesView(APIView):
    """GET /analytics/conversations-series/?granularity=day|week&from=&to="""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company_id, err = _resolve_company_id(request)
        if err:
            return err
        granularity = request.query_params.get("granularity", "day")
        if granularity not in {"day", "week"}:
            granularity = "day"
        return Response(
            conversations_series(
                company_id,
                granularity=granularity,
                date_from=_parse_date(request.query_params.get("from")),
                date_to=_parse_date(request.query_params.get("to")),
            )
        )


@extend_schema(tags=["analytics"])
class TopFaqsView(APIView):
    """GET /analytics/top-faqs/?from=&to=&limit= — most asked questions."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company_id, err = _resolve_company_id(request)
        if err:
            return err
        try:
            limit = min(int(request.query_params.get("limit", 5)), 50)
        except (TypeError, ValueError):
            limit = 5
        return Response(
            top_faqs(
                company_id,
                date_from=_parse_date(request.query_params.get("from")),
                date_to=_parse_date(request.query_params.get("to")),
                limit=limit,
            )
        )


@extend_schema(tags=["analytics"])
class MetricsViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ConversationMetrics.objects.select_related("company").all()
    serializer_class = ConversationMetricsSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["date"]
    ordering_fields = ["date"]

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Compute + return today's live metrics for the caller's company."""
        company_id = request.user.company_id
        if company_id is None and request.user.role == UserRole.SUPER_ADMIN:
            company_uuid = request.query_params.get("company")
            if not company_uuid:
                return Response(
                    {"success": False, "message": "Provide ?company=<uuid>."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from companies.models import Company

            company_id = Company.objects.get(uuid=company_uuid).id

        metrics = compute_daily_metrics(company_id)
        return Response(
            {"success": True, "metrics": ConversationMetricsSerializer(metrics).data}
        )


@extend_schema(tags=["analytics"])
class UnansweredQuestionViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = UnansweredQuestion.objects.select_related("company").all()
    serializer_class = UnansweredQuestionSerializer
    permission_classes = [IsAuthenticated, HasCompanyRole]
    allowed_roles = [UserRole.COMPANY_ADMIN, UserRole.MANAGER]
    lookup_field = "uuid"
    filterset_fields = ["is_resolved"]
    search_fields = ["question"]
    ordering_fields = ["occurrence_count", "updated_at"]

    @extend_schema(request=ConvertToFaqSerializer)
    @action(detail=True, methods=["post"])
    def convert_to_faq(self, request, uuid=None):
        """Manager converts an unanswered question into a knowledge-base FAQ."""
        unanswered = self.get_object()
        serializer = ConvertToFaqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qa = convert_unanswered_to_faq(
            unanswered,
            knowledge_base=serializer.validated_data["knowledge_base"],
            answer=serializer.validated_data["answer"],
        )
        return Response(
            {"success": True, "qa_uuid": str(qa.uuid)},
            status=status.HTTP_201_CREATED,
        )
