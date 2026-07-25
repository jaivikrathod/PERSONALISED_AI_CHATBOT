from rest_framework import viewsets, mixins, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from vector_question.services import _build_text, generate_embedding

from .models import Question, UnansweredMessage
from .serializers import QuestionSerializer, UnansweredMessageSerializer


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


class UnansweredMessageViewSet(
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Inbox of customer messages the chatbot couldn't answer.

    GET  /api/unanswered-messages/?company_id=<id>   -> list
    POST /api/unanswered-messages/{id}/resolve/       -> add answer + vectorize
    DELETE /api/unanswered-messages/{id}/             -> dismiss without answering
    """

    serializer_class = UnansweredMessageSerializer

    def get_queryset(self):
        queryset = UnansweredMessage.objects.select_related("company").all()
        company_id = self.request.query_params.get("company_id")
        if company_id is not None:
            queryset = queryset.filter(company_id=company_id)
        return queryset

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Turn an unanswered message into a vectorized Question.

        Body: {"answer": "<the answer text>"}

        Creates a Question (message becomes the question text), generates its
        embedding immediately, then deletes the unanswered message.
        """
        unanswered = self.get_object()

        answer = (request.data.get("answer") or "").strip()
        if not answer:
            return Response(
                {"error": "Answer cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        question = Question.objects.create(
            company_id=unanswered.company_id,
            question=unanswered.message,
            answer=answer,
        )

        # Vectorize this single question right away so it can immediately serve
        # future chats, then drop it from the unanswered inbox.
        try:
            embedding = generate_embedding(_build_text(question.question, question.answer))
        except Exception:  # noqa: BLE001 - surface a clean error, keep the inbox row
            question.delete()
            return Response(
                {"error": "Failed to vectorize the answer. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        question.embedding = embedding
        question.is_vectorized = True
        question.save(update_fields=["embedding", "is_vectorized", "updated_at"])

        unanswered.delete()

        return Response(
            QuestionSerializer(question).data,
            status=status.HTTP_201_CREATED,
        )
