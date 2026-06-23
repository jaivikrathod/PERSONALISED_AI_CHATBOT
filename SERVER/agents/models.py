"""Agent presence + conversation assignment models."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class AgentAvailability(BaseModel):
    """Tracks whether a human agent is online and ready to take chats."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability",
    )
    online = models.BooleanField(default=False, db_index=True)
    last_seen = models.DateTimeField(default=timezone.now)
    # Concurrency control: how many active chats this agent can hold.
    max_active_chats = models.PositiveIntegerField(default=5)

    class Meta:
        db_table = "agents_availability"

    def __str__(self):
        return f"{self.user_id} {'online' if self.online else 'offline'}"

    @property
    def company_id(self):
        return self.user.company_id

    def touch(self, online: bool | None = None):
        if online is not None:
            self.online = online
        self.last_seen = timezone.now()
        self.save(update_fields=["online", "last_seen"])


class ConversationAssignment(BaseModel):
    """Links a conversation to the agent currently handling it.

    History is preserved: transferring creates a new active row and deactivates
    the previous one, so we keep a full audit trail of who handled what.
    """

    conversation = models.ForeignKey(
        "conversations.Conversation",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_at = models.DateTimeField(default=timezone.now)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "agents_conversation_assignment"
        ordering = ["-assigned_at"]
        indexes = [models.Index(fields=["conversation", "is_active"])]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation"],
                condition=models.Q(is_active=True),
                name="one_active_assignment_per_conversation",
            )
        ]

    def __str__(self):
        return f"conv={self.conversation_id} -> agent={self.agent_id}"

    @property
    def company_id(self):
        return self.conversation.company_id

    def release(self):
        self.is_active = False
        self.released_at = timezone.now()
        self.save(update_fields=["is_active", "released_at"])
