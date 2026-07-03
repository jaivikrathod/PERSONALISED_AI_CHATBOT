from rest_framework import viewsets, filters, status
from rest_framework.response import Response

from .models import Question
from .serializers import QuestionSerializer


class QuestionViewSet(viewsets.ModelViewSet):

    serializer_class = QuestionSerializer

    # Enable DRF search/ordering. `search_fields` powers ?search=.
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["question"]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):

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

        Clear the embedding too so an archived row doesn't keep a stale vector.
        """
        instance = self.get_object()
        instance.is_archived = True
        instance.is_vectorized = False
        instance.embedding = None
        instance.save(
            update_fields=["is_archived", "is_vectorized", "embedding", "updated_at"]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
