from rest_framework import serializers

from .models import WidgetConfig


class WidgetConfigSerializer(serializers.ModelSerializer):
    chatbot = serializers.UUIDField(source="chatbot.uuid", read_only=True)

    class Meta:
        model = WidgetConfig
        fields = [
            "uuid",
            "chatbot",
            "title",
            "subtitle",
            "position",
            "primary_color",
            "launcher_icon",
            "allowed_origins",
            "collect_visitor_email",
            "enabled",
        ]
        read_only_fields = ["uuid", "chatbot"]


class WidgetStartSerializer(serializers.Serializer):
    """Public: begin / resume a visitor session."""

    session_id = serializers.CharField(max_length=128)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)


class WidgetChatSerializer(serializers.Serializer):
    """Public: send a message in a visitor session."""

    session_id = serializers.CharField(max_length=128)
    message = serializers.CharField()
