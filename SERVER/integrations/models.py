"""Widget configuration: per-chatbot embeddable widget settings + allowed origins."""

from django.db import models

from core.models import BaseModel


class WidgetConfig(BaseModel):
    """Customisation + security settings for a chatbot's website widget."""

    chatbot = models.OneToOneField(
        "chatbot.Chatbot",
        on_delete=models.CASCADE,
        related_name="widget_config",
    )
    # Display
    title = models.CharField(max_length=255, default="Support")
    subtitle = models.CharField(max_length=255, blank=True)
    position = models.CharField(
        max_length=16,
        choices=[("bottom-right", "Bottom right"), ("bottom-left", "Bottom left")],
        default="bottom-right",
    )
    primary_color = models.CharField(max_length=9, default="#4f46e5")
    launcher_icon = models.URLField(blank=True)

    # Security: domains permitted to embed this widget (CORS-style allowlist).
    allowed_origins = models.JSONField(default=list, blank=True)
    collect_visitor_email = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "integrations_widget_config"

    def __str__(self):
        return f"WidgetConfig<{self.chatbot_id}>"

    @property
    def company_id(self):
        return self.chatbot.company_id

    def get_object_company_id(self):
        return self.chatbot.company_id

    def origin_allowed(self, origin: str) -> bool:
        if not self.allowed_origins:
            return True  # no allowlist configured -> allow all (dev default)
        return origin in self.allowed_origins
