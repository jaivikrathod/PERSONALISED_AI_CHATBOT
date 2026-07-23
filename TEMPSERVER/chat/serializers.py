from rest_framework import serializers

from .models import ChatMessage, ChatSession


class ChatMessageSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "session",
            "company",
            "message",
            "sent_by_us",
            "is_ai",
            "message_type",
            "attachments",
            "created_at",
            "role",
        ]
        read_only_fields = fields

    def get_role(self, obj):
        return "bot" if obj.is_ai or obj.sent_by_us else "user"


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
        return message.created_at if message else None
