from rest_framework import serializers

from .models import Chatbot, Visitor


class ChatbotSerializer(serializers.ModelSerializer):
    # The dashboard speaks "status" ('active' | 'inactive'); the model stores a
    # boolean `active`. Expose both and map between them so the UI just works.
    status = serializers.CharField(required=False)

    class Meta:
        model = Chatbot
        fields = [
            "id",
            "uuid",
            "name",
            "welcome_message",
            "theme_color",
            "system_prompt",
            "widget_token",
            "active",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "uuid", "widget_token", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["status"] = "active" if instance.active else "inactive"
        return data

    def validate(self, attrs):
        status = attrs.pop("status", None)
        if status is not None:
            attrs["active"] = status == "active"
        return attrs


class PublicChatbotSerializer(serializers.ModelSerializer):
    """Safe representation served to the browser widget (no secrets)."""

    class Meta:
        model = Chatbot
        fields = ["uuid", "name", "welcome_message", "theme_color", "active"]


class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ["uuid", "session_id", "name", "email", "metadata", "created_at"]
        read_only_fields = ["uuid", "created_at"]
