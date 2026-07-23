from django.db import models

from company.models import Company
from users.models import User


class ChatSession(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        CLOSED = "closed", "Closed"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )

    agent_needed = models.BooleanField(default=False)

    agent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="assigned_chat_sessions",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_session"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session #{self.id}"
    
    
class ChatMessage(models.Model):
    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        FILE = "file", "File"
        SYSTEM = "system", "System"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    # Customer Details
    customer_user_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    customer_user_name = models.CharField(
        max_length=255,
        blank=True,
    )

    customer_user_email = models.EmailField(
        blank=True,
    )

    # Message
    message = models.TextField(blank=True)

    # Sender Information
    sent_by_us = models.BooleanField(default=False)

    is_ai = models.BooleanField(default=False)

    this_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_messages",
    )

    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )

    attachments = models.JSONField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at"]

    def __str__(self):
        return f"Message #{self.id} - Session #{self.session_id}"