"""Conversation + Message models.

A Conversation is a single chat thread between a Visitor and a company's bot /
agents. Messages are the individual turns. Status transitions:

    BOT --(low confidence / explicit ask)--> WAITING_AGENT
        --(agent picks up)--> ACTIVE_AGENT
        --(resolved)--> RESOLVED
"""

from django.conf import settings
from django.db import models

from core.enums import ConversationStatus, SenderType
from core.models import BaseModel


class Conversation(BaseModel):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    chatbot = models.ForeignKey(
        "chatbot.Chatbot",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    visitor = models.ForeignKey(
        "chatbot.Visitor",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    status = models.CharField(
        max_length=16,
        choices=ConversationStatus.choices,
        default=ConversationStatus.BOT,
        db_index=True,
    )
    last_confidence = models.FloatField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conversations_conversation"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["chatbot", "status"]),
        ]

    def __str__(self):
        return f"Conversation<{self.uuid}> [{self.status}]"

    def get_object_company_id(self):
        return self.company_id

    @property
    def is_with_agent(self) -> bool:
        return self.status in {
            ConversationStatus.WAITING_AGENT,
            ConversationStatus.ACTIVE_AGENT,
        }


class Message(BaseModel):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender_type = models.CharField(max_length=16, choices=SenderType.choices, db_index=True)
    # Set only when sender_type == AGENT.
    sender_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_messages",
    )
    message = models.TextField()
    # Free-form: confidence, retrieved QA ids, read_at, provider model, etc.
    metadata = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conversations_message"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self):
        return f"{self.sender_type}: {self.message[:50]}"

    @property
    def company_id(self):
        return self.conversation.company_id

    def get_object_company_id(self):
        return self.conversation.company_id
