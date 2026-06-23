from rest_framework import serializers

from .models import Chatbot, Visitor


class ChatbotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chatbot
        fields = [
            "uuid",
            "name",
            "welcome_message",
            "theme_color",
            "system_prompt",
            "widget_token",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid", "widget_token", "created_at", "updated_at"]


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
