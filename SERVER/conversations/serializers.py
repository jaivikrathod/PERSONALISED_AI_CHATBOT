from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_agent_email = serializers.EmailField(
        source="sender_agent.email", read_only=True, allow_null=True
    )

    class Meta:
        model = Message
        fields = [
            "uuid",
            "sender_type",
            "sender_agent_email",
            "message",
            "metadata",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.__str__", read_only=True)
    chatbot_name = serializers.CharField(source="chatbot.name", read_only=True)
    message_count = serializers.IntegerField(source="messages.count", read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "uuid",
            "status",
            "chatbot_name",
            "visitor_name",
            "last_confidence",
            "message_count",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]


class AgentReplySerializer(serializers.Serializer):
    message = serializers.CharField()


class EscalateSerializer(serializers.Serializer):
    conversation = serializers.UUIDField()
    reason = serializers.CharField(required=False, default="manual")
