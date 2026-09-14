"""The per-tenant tool registry (WORKFLOW.md B2.1 / B2.4).

Two tables, and the whole universality claim rests on them:

- `Chatbot` is the thing every later table hangs off. Today the tenant key is
  `company_id` and every knob (threshold, persona, model) is a global constant;
  `chatbots.policy` is where those knobs move to, per bot.
- `Tool` is what the model is allowed to call. Adding a capability to a tenant
  is inserting a row here plus an executor for its `tool_type` — never a branch
  in the consumer (Part D rule 7).

Nothing in this module knows what industry a bot serves. A preset (B0) writes
rows at onboarding and is never read again at runtime (Part D rule 3a).
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from company.models import Company


def default_policy() -> dict:
    """Budgets and gates from B5/B4, per chatbot instead of per deployment.

    A `Chatbot` row created before a budget exists still has to run, so the
    orchestrator reads these through `Chatbot.get_policy()` rather than
    indexing `policy` directly — a missing key falls back to the default here,
    which keeps adding a budget from being a data migration over every row.
    """
    return {
        # B5 budgets.
        "tool_calls_per_turn": 4,
        "model_round_trips": 3,
        "wall_clock_ms": 20000,
        "single_tool_timeout_ms": 6000,
        "repeat_identical_call": 1,
        # B4 retrieval gate. `accept_threshold` is today's
        # CHAT_CONFIDENCE_THRESHOLD, which is measured and pinned by
        # tests/test_retrieval.py — do not "fix" it upward (Part D rule 2).
        "retrieval_floor": 0.32,
        "accept_threshold": 0.40,
        "margin_rule": 0.15,
        # A best cosine this high is a clear match; the margin rule only
        # guards the ambiguous band between accept_threshold and here.
        "margin_bypass_score": 0.55,
        # Hard ceiling on knowledge tokens handed to the model per search.
        "max_context_tokens": 1200,
        # B5 server-side handoff safety net, independent of the model.
        "handoff_after_barren_turns": 3,
        # G7 caps.
        "max_rows_returned": 20,
    }


class Chatbot(models.Model):
    """One configured bot. The anchor for tools, knowledge and conversations."""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="chatbots",
    )

    # The public URL key. `/chat/acme-support` instead of `/chat/7`, so a link
    # recipient cannot enumerate tenants by incrementing an integer (B2.1).
    # Unique platform-wide, not per company, because it is resolved before any
    # tenant is known.
    slug = models.SlugField(max_length=64, unique=True)

    name = models.CharField(max_length=255)

    # Appended to the platform system prompt (B7 step 1), never replacing it.
    persona_prompt = models.TextField(blank=True)

    # Empty means "whatever GEMINI_MODEL says". Pinning a model per bot is what
    # lets one tenant stay on a known-good version through an upgrade.
    model = models.CharField(max_length=100, blank=True)

    temperature = models.FloatField(
        default=0.2,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
    )

    locale = models.CharField(max_length=16, default="en")

    is_active = models.BooleanField(default=True)

    policy = models.JSONField(default=default_policy, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chatbots"
        ordering = ("id",)
        indexes = [
            models.Index(fields=["company", "is_active"], name="chatbots_company_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def get_policy(self, key: str):
        """Read one budget, falling back to the shipped default."""
        policy = self.policy or {}
        if key in policy:
            return policy[key]
        return default_policy()[key]


class Tool(models.Model):
    """One capability this chatbot's model may call.

    `input_schema` is the *compiled* JSON Schema actually sent to the model.
    For `KNOWLEDGE_SEARCH` and `HANDOFF` it is fixed and written at creation;
    for `STRUCTURED_SEARCH` and `API_ACTION` it is regenerated from
    `data_source_fields` / `action_parameters` when those rows change (B2.4),
    which is why `schema_version` exists — the declaration cache is keyed on
    `(chatbot_id, schema_version)` (Phase 2).
    """

    class ToolType(models.TextChoices):
        KNOWLEDGE_SEARCH = "KNOWLEDGE_SEARCH", "Knowledge search"
        STRUCTURED_SEARCH = "STRUCTURED_SEARCH", "Structured search"
        API_ACTION = "API_ACTION", "API action"
        HANDOFF = "HANDOFF", "Handoff"

    chatbot = models.ForeignKey(
        Chatbot,
        on_delete=models.CASCADE,
        related_name="tools",
    )

    # What the model calls it. Must be a valid function name for the provider.
    name = models.CharField(max_length=64)

    # Prompt engineering whether or not anyone calls it that: this string is
    # how the model decides between two tools. B8 screen 6 edits it live.
    description = models.TextField()

    tool_type = models.CharField(max_length=32, choices=ToolType.choices)

    # Executor input the model never sees: {"data_source_id": 12},
    # {"source_ids": [...]}, {"action_id": 45}, {"queue": "..."}.
    configuration = models.JSONField(default=dict, blank=True)

    input_schema = models.JSONField(default=dict, blank=True)

    schema_version = models.PositiveIntegerField(default=1)

    is_active = models.BooleanField(default=True)

    # Enforced server-side by the orchestrator (B6), never by prompt text.
    requires_confirmation = models.BooleanField(default=False)

    # G9. e.g. {"per_conversation": 10, "per_company_per_minute": 120}
    rate_limit = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tools"
        ordering = ("chatbot_id", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["chatbot", "name"], name="tools_unique_name_per_chatbot"
            ),
        ]
        indexes = [
            models.Index(fields=["chatbot", "is_active"], name="tools_chatbot_idx"),
        ]

    def __str__(self):
        return f"{self.name} @ {self.chatbot_id}"

    def declaration(self) -> dict:
        """The tool as the provider adapter will send it (B3).

        Deliberately omits `configuration`, `tool_type` and every id: the model
        sees a business capability, the backend keeps the mapping.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema or {"type": "object", "properties": {}},
        }
