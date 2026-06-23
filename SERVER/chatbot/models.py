"""Chatbot + Visitor models.

A Chatbot is a company's configurable assistant exposed on their website via a
secret widget_token. A Visitor is an anonymous (or self-identified) end user who
chats with a bot in a browser session.
"""

import secrets

from django.db import models

from core.models import BaseModel


def generate_widget_token() -> str:
    """URL-safe public token used to authenticate widget traffic."""
    return secrets.token_urlsafe(32)


class Chatbot(BaseModel):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="chatbots",
    )
    name = models.CharField(max_length=255)
    welcome_message = models.TextField(default="Hi! How can I help you today?")
    theme_color = models.CharField(max_length=9, default="#4f46e5")  # hex
    widget_token = models.CharField(
        max_length=64, unique=True, default=generate_widget_token, db_index=True
    )
    # Optional persona / behaviour prompt fed to the LLM.
    system_prompt = models.TextField(blank=True)
    active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "chatbot_chatbot"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.company_id})"

    def get_object_company_id(self):
        return self.company_id

    def rotate_widget_token(self):
        self.widget_token = generate_widget_token()
        self.save(update_fields=["widget_token", "updated_at"])
        return self.widget_token


class Visitor(BaseModel):
    chatbot = models.ForeignKey(
        Chatbot,
        on_delete=models.CASCADE,
        related_name="visitors",
    )
    session_id = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # ip, user agent, page url

    class Meta:
        db_table = "chatbot_visitor"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["chatbot", "session_id"], name="uniq_visitor_session"
            )
        ]

    def __str__(self):
        return self.name or self.email or self.session_id

    @property
    def company_id(self):
        return self.chatbot.company_id

    def get_object_company_id(self):
        return self.chatbot.company_id
