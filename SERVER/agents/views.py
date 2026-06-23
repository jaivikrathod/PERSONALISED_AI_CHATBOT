"""Agent endpoints: presence + assign / transfer / close chats."""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from conversations.models import Conversation
from core.enums import UserRole

from .models import AgentAvailability, ConversationAssignment
from .serializers import (
    AgentAvailabilitySerializer,
    AssignSerializer,
    ConversationAssignmentSerializer,
    TransferSerializer,
)
from .services import (
    assign_conversation,
    close_conversation,
    transfer_conversation,
)

User = get_user_model()


def _company_conversations(user):
    qs = Conversation.objects.all()
    if user.role == UserRole.SUPER_ADMIN:
        return qs
    return qs.filter(company_id=user.company_id)


def _company_agent(user, agent_uuid):
    """Resolve an agent UUID within the caller's company."""
    qs = User.objects.filter(uuid=agent_uuid)
    if user.role != UserRole.SUPER_ADMIN:
        qs = qs.filter(company_id=user.company_id)
    return get_object_or_404(qs)


@extend_schema(tags=["agents"])
class AgentAvailabilityViewSet(viewsets.GenericViewSet):
    serializer_class = AgentAvailabilitySerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        """Get or update the caller's own availability (online/offline)."""
        availability, _ = AgentAvailability.objects.get_or_create(user=request.user)
        if request.method == "PATCH":
            serializer = self.get_serializer(availability, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            availability.touch()
            return Response({"success": True, **serializer.data})
        return Response({"success": True, **self.get_serializer(availability).data})

    @action(detail=False, methods=["get"])
    def online(self, request):
        """List online agents in the caller's company."""
        qs = AgentAvailability.objects.filter(online=True).select_related("user")
        if request.user.role != UserRole.SUPER_ADMIN:
            qs = qs.filter(user__company_id=request.user.company_id)
        return Response(
            {"success": True, "results": self.get_serializer(qs, many=True).data}
        )


@extend_schema(tags=["agents"])
class AssignmentViewSet(viewsets.GenericViewSet):
    serializer_class = ConversationAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ConversationAssignment.objects.select_related("conversation", "agent")
        user = self.request.user
        if getattr(self, "swagger_fake_view", False) or not user.is_authenticated:
            return qs.none()
        if user.role != UserRole.SUPER_ADMIN:
            qs = qs.filter(conversation__company_id=user.company_id)
        return qs

    @action(detail=False, methods=["get"])
    def mine(self, request):
        """Active conversations assigned to the caller."""
        qs = self.get_queryset().filter(agent=request.user, is_active=True)
        return Response({"success": True, "results": self.get_serializer(qs, many=True).data})

    @extend_schema(request=AssignSerializer)
    @action(detail=False, methods=["post"])
    def assign(self, request):
        """Assign a waiting conversation to an agent (defaults to the caller)."""
        serializer = AssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = get_object_or_404(
            _company_conversations(request.user),
            uuid=serializer.validated_data["conversation"],
        )
        agent_uuid = serializer.validated_data.get("agent")
        agent = _company_agent(request.user, agent_uuid) if agent_uuid else request.user

        assignment = assign_conversation(conversation, agent)
        return Response(
            {"success": True, **ConversationAssignmentSerializer(assignment).data},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=TransferSerializer)
    @action(detail=False, methods=["post"])
    def transfer(self, request):
        """Transfer a conversation to another agent."""
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = get_object_or_404(
            _company_conversations(request.user),
            uuid=serializer.validated_data["conversation"],
        )
        to_agent = _company_agent(request.user, serializer.validated_data["to_agent"])

        assignment = transfer_conversation(conversation, to_agent)
        return Response({"success": True, **ConversationAssignmentSerializer(assignment).data})

    @action(detail=False, methods=["post"])
    def close(self, request):
        """Close a conversation and release its agent."""
        conv_uuid = request.data.get("conversation")
        conversation = get_object_or_404(_company_conversations(request.user), uuid=conv_uuid)
        close_conversation(conversation)
        return Response({"success": True, "status": conversation.status})
