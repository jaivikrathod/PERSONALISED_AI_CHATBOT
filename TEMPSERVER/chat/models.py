import secrets

from django.db import models

from company.models import Company
from users.models import User


def new_public_token() -> str:
    """Unguessable handle a browser uses to reclaim its own anonymous chat."""
    return secrets.token_urlsafe(24)


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

    # Anonymous visitors have no account, so this is the only thing that proves
    # a browser owns this conversation. Issued when the session is created and
    # required to read its history over HTTP; without it, session ids are
    # sequential integers and one visitor could read another's chat.
    public_token = models.CharField(
        max_length=64,
        unique=True,
        default=new_public_token,
        editable=False,
    )

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

    # --- Orchestration (WORKFLOW.md B2.5) ------------------------------------
    # The bot this conversation runs against. Nullable only so rows from before
    # the registry existed survive the migration; `chat.0004` backfills it.
    chatbot = models.ForeignKey(
        "registry.Chatbot",
        on_delete=models.SET_NULL,
        related_name="chat_sessions",
        null=True,
        blank=True,
    )

    visitor_id = models.CharField(max_length=128, blank=True)

    channel = models.CharField(max_length=32, default="web")

    # A cache, not a source of truth (B7): never read by a validator, cleared on
    # close, reconstructible from the message log.
    working_set = models.JSONField(default=dict, blank=True)

    summary = models.TextField(blank=True)
    summary_upto_message_id = models.PositiveBigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_session"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session #{self.id}"
    
    
class ChatMessageQuerySet(models.QuerySet):
    def transcript(self):
        """What a person reads: customer, agent and bot text — no tool plumbing.

        The model replays every row (B7); the widget and the agent console only
        see these. Same rows, filtered, never a second table (Part D rule 5).
        """
        return self.filter(
            role__in=(ChatMessage.Role.USER, ChatMessage.Role.ASSISTANT),
            tool_name="",
        )


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"
        SYSTEM = "system", "System"

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

    # --- Orchestration (WORKFLOW.md B2.5) ------------------------------------
    # An assistant row with `tool_name` set is the model *calling* a tool; a
    # `tool` row is that call's result. Both are replayed to the model and
    # hidden from people by `ChatMessage.objects.transcript()`.
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.USER)
    tool_call_id = models.CharField(max_length=128, blank=True)
    tool_name = models.CharField(max_length=64, blank=True)
    tool_args = models.JSONField(null=True, blank=True)
    tool_result = models.JSONField(null=True, blank=True)
    # What replaces `tool_result` in context once the turn is old (B7 step 4).
    tool_result_summary = models.TextField(blank=True)
    tokens = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ChatMessageQuerySet.as_manager()

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Message #{self.id} - Session #{self.session_id}"


class ToolExecution(models.Model):
    """Gate G10: one row per tool call the model made, including rejected ones."""

    class Status(models.TextChoices):
        OK = "ok", "OK"
        REJECTED = "rejected", "Rejected by a gate"
        ERROR = "error", "Executor error"
        TIMEOUT = "timeout", "Timed out"
        CACHED = "cached", "Repeat call served from cache"
        RATE_LIMITED = "rate_limited", "Rate limited"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="tool_executions",
    )

    conversation = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="tool_executions",
    )

    # The assistant row that carried the call.
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.SET_NULL,
        related_name="tool_executions",
        null=True,
        blank=True,
    )

    # Null when the model named a tool this chatbot does not have (G2).
    tool = models.ForeignKey(
        "registry.Tool",
        on_delete=models.SET_NULL,
        related_name="executions",
        null=True,
        blank=True,
    )
    tool_name = models.CharField(max_length=64)

    raw_arguments = models.JSONField(default=dict, blank=True)
    validated_arguments = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    error_code = models.CharField(max_length=64, blank=True)
    rows_returned = models.PositiveIntegerField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tool_executions"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["conversation", "tool_name"],
                name="tool_exec_conversation_idx",
            ),
        ]

    def __str__(self):
        return f"{self.tool_name} [{self.status}] @ session {self.conversation_id}"