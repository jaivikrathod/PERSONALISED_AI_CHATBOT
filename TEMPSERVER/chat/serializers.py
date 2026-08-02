from rest_framework import serializers

from .models import ChatMessage, ChatSession


class ChatMessageSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    sender = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "session",
            "company",
            "message",
            "sent_by_us",
            "is_ai",
            "this_user",
            "customer_user_name",
            "message_type",
            "attachments",
            "created_at",
            "role",
            "sender",
        ]
        read_only_fields = fields

    def get_role(self, obj):
        return "bot" if obj.is_ai or obj.sent_by_us else "user"

    def get_sender(self, obj):
        """Finer-grained than `role`: the agent console needs ai vs agent."""
        if obj.is_ai:
            return "ai"
        return "agent" if obj.sent_by_us else "customer"


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "company",
            "agent_needed",
            "agent",
            "status",
            "closed_at",
            "created_at",
            "updated_at",
            "messages",
        ]
        read_only_fields = fields


class ChatSessionListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "company",
            "agent_needed",
            "agent",
            "status",
            "closed_at",
            "created_at",
            "updated_at",
            "last_message",
            "last_message_at",
            "message_count",
        ]
        read_only_fields = fields

    def get_last_message(self, obj):
        message = getattr(obj, "last_message_obj", None)
        return message.message if message else ""

    def get_last_message_at(self, obj):
        message = getattr(obj, "last_message_obj", None)
        # ISO string rather than a datetime: this payload is also pushed down
        # the agent socket with plain json.dumps, which can't encode datetimes.
        return message.created_at.isoformat() if message else None
