from rest_framework import viewsets, filters, status
from rest_framework.response import Response

from .models import Question
from .serializers import QuestionSerializer


class QuestionViewSet(viewsets.ModelViewSet):
    """Full CRUD API for Question with soft delete.

    Features:
      * Default queryset excludes archived rows (is_archived=True).
      * Filter by company:  /api/questions/?company_id=1
      * Search by question: /api/questions/?search=refund
      * DELETE performs a soft delete (sets is_archived=True).
    """

    serializer_class = QuestionSerializer

    # Enable DRF search/ordering. `search_fields` powers ?search=.
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["question"]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Base queryset: only non-archived rows, optionally filtered by company.

        `select_related("company")` avoids N+1 queries when serializing
        the related company name.
        """
        queryset = (
            Question.objects.select_related("company")
            .filter(is_archived=False)
        )

        # Optional ?company_id=<id> filter.
        company_id = self.request.query_params.get("company_id")
        if company_id is not None:
            queryset = queryset.filter(company_id=company_id)

        return queryset

    def destroy(self, request, *args, **kwargs):
        """Soft delete: mark the record archived instead of removing it.

        If the question has an associated vector, remove it from the vector
        DB first (Part 6) so we never leave orphaned embeddings behind.
        """
        instance = self.get_object()
        # Remove the vector before archiving; clear local state to stay consistent.
        instance._cleanup_vector()
        instance.is_archived = True
        instance.is_vectorized = False
        instance.vector_id = None
        instance.save(
            update_fields=["is_archived", "is_vectorized", "vector_id", "updated_at"]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
