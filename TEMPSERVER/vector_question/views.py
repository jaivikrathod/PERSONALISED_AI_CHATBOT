import logging

from rest_framework import status, viewsets, mixins
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VectorJob
from .serializers import VectorJobSerializer
from .services import CompanyNotFound, vectorize_company

logger = logging.getLogger(__name__)


class VectorizeCompanyView(APIView):
    """POST /api/vectorize/{company_id}/

    Thin HTTP wrapper around the service layer. The view only:
      * translates the URL into a call to `vectorize_company`,
      * maps the service result / exceptions to HTTP status codes.

    All vectorization logic lives in `services.py` (Part 7). This same call
    can later be dispatched to Celery for async processing without changing
    this endpoint's contract (Part 10).
    """

    def post(self, request, company_id: int):
        try:
            result = vectorize_company(company_id)
        except CompanyNotFound:
            return Response(
                {"error": "Company not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:  # noqa: BLE001 - unexpected failure -> 500 with safe message
            logger.exception("Unexpected error vectorizing company %s", company_id)
            return Response(
                {"error": "An unexpected error occurred during vectorization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Nothing to do -> 200 with the informative message.
        if result.get("all_vectorized"):
            return Response(
                {"message": result["message"]},
                status=status.HTTP_200_OK,
            )

        # Completed (possibly with per-question failures).
        return Response(
            {
                "message": result["message"],
                "total_questions": result["total_questions"],
                "processed_questions": result["processed_questions"],
                "failed_questions": result["failed_questions"],
            },
            status=status.HTTP_200_OK,
        )


class VectorJobViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only API to inspect vectorization jobs and their progress.

    GET /api/vector-jobs/           -> list (optionally ?company_id=)
    GET /api/vector-jobs/{id}/      -> retrieve one job
    """

    serializer_class = VectorJobSerializer

    def get_queryset(self):
        queryset = VectorJob.objects.select_related("company").all()
        company_id = self.request.query_params.get("company_id")
        if company_id is not None:
            queryset = queryset.filter(company_id=company_id)
        return queryset
