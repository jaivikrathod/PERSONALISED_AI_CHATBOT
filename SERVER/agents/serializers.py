from rest_framework import serializers

from .models import AgentAvailability, ConversationAssignment


class AgentAvailabilitySerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = AgentAvailability
        fields = ["email", "full_name", "online", "last_seen", "max_active_chats"]
        read_only_fields = ["email", "full_name", "last_seen"]


class ConversationAssignmentSerializer(serializers.ModelSerializer):
    agent_email = serializers.EmailField(source="agent.email", read_only=True)
    conversation_uuid = serializers.UUIDField(source="conversation.uuid", read_only=True)

    class Meta:
        model = ConversationAssignment
        fields = [
            "uuid",
            "conversation_uuid",
            "agent_email",
            "is_active",
            "assigned_at",
            "released_at",
        ]
        read_only_fields = fields


class AssignSerializer(serializers.Serializer):
    conversation = serializers.UUIDField()
    # Optional: assign to a specific agent (defaults to the caller).
    agent = serializers.UUIDField(required=False)


class TransferSerializer(serializers.Serializer):
    conversation = serializers.UUIDField()
    to_agent = serializers.UUIDField()
