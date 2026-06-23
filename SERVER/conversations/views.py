"""Conversation endpoints for the authenticated agent dashboard."""

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.enums import SenderType
from core.mixins import CompanyScopedQuerysetMixin

from .models import Conversation
from .serializers import (
    AgentReplySerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    EscalateSerializer,
)
from .services import ChatService, mark_resolved


@extend_schema(tags=["conversations"])
class ConversationViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = (
        Conversation.objects.select_related("chatbot", "visitor", "company")
        .prefetch_related("messages")
        .all()
    )
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    filterset_fields = ["status", "chatbot__uuid"]
    ordering_fields = ["created_at", "updated_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ConversationDetailSerializer
        return ConversationSerializer

    @extend_schema(request=AgentReplySerializer)
    @action(detail=True, methods=["post"])
    def reply(self, request, uuid=None):
        """An agent posts a message into the conversation."""
        conversation = self.get_object()
        serializer = AgentReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ChatService(conversation)
        msg = service._save_message(
            SenderType.AGENT,
            serializer.validated_data["message"],
            sender_agent=request.user,
        )
        return Response(
            {"success": True, "message_id": msg.id},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def resolve(self, request, uuid=None):
        """Close the conversation."""
        conversation = self.get_object()
        mark_resolved(conversation)
        return Response({"success": True, "status": conversation.status})

    @extend_schema(request=EscalateSerializer)
    @action(detail=False, methods=["post"])
    def escalate(self, request):
        """POST /conversations/escalate/ — push a chat to the human queue."""
        serializer = EscalateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = get_object_or_404(
            self.get_queryset(), uuid=serializer.validated_data["conversation"]
        )
        ChatService(conversation).escalate(reason=serializer.validated_data["reason"])
        return Response({"success": True, "status": conversation.status})
