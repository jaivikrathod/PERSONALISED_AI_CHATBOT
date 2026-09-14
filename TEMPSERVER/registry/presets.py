"""Presets: the onboarding answer to "what kind of chatbot?" (WORKFLOW.md B0).

A preset is **data**. It writes `Tool` rows once, at onboarding, and is never
read again at runtime (Part D rule 3a). There must be no `if preset == ...`
anywhere in the orchestrator — preset 2 is a strict superset of preset 1, and
one company will want both modes inside one conversation.

Upgrading a company from Q&A to catalogue is therefore `provision_tools()` with
the other preset name: it inserts the rows preset 1 did not have and leaves the
rest alone. No migration, no redeploy.
"""

from __future__ import annotations

from django.db import transaction
from django.utils.text import slugify

from .models import Chatbot, Tool


# --- Fixed schemas -----------------------------------------------------------
# KNOWLEDGE_SEARCH and HANDOFF take the same arguments for every tenant, so
# their schema is a constant rather than something compiled from registry rows.

SEARCH_KNOWLEDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The customer's question, in their own words.",
        },
        "top_k": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 3,
            "description": "How many passages to return.",
        },
    },
    "required": ["query"],
}

REQUEST_HUMAN_AGENT_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {
            "type": "string",
            "description": "Why a human is needed, in one sentence.",
        },
        "summary": {
            "type": "string",
            "description": "What the customer wants, for the agent to read first.",
        },
    },
    "required": ["reason"],
}


# The two tools Phase 1 ships. Both presets get both; preset 2 adds a
# STRUCTURED_SEARCH row per data source in Phase 2, which is why that row is
# absent here rather than stubbed.
_SEARCH_KNOWLEDGE = {
    "name": "search_knowledge",
    "tool_type": Tool.ToolType.KNOWLEDGE_SEARCH,
    "description": (
        "Search the company's own documented answers, policies and product "
        "information. Use whenever the customer asks something factual about "
        "this company. Do not use for greetings or small talk. An empty result "
        "means nothing relevant is documented — say so, do not guess."
    ),
    "input_schema": SEARCH_KNOWLEDGE_SCHEMA,
    "configuration": {},
}

_REQUEST_HUMAN_AGENT = {
    "name": "request_human_agent",
    "tool_type": Tool.ToolType.HANDOFF,
    "description": (
        "Hand the conversation to a human colleague. Use when the customer "
        "asks for a person, is upset, or when you cannot help after genuinely "
        "trying. Do not use as a first response to a hard question."
    ),
    "input_schema": REQUEST_HUMAN_AGENT_SCHEMA,
    "configuration": {"queue": "default", "reason_required": True},
}


QNA = "qna"
CATALOGUE = "catalogue"

PRESETS = {
    # Preset 1 — "customers ask questions, you give answers."
    QNA: [_SEARCH_KNOWLEDGE, _REQUEST_HUMAN_AGENT],
    # Preset 2 — "customers search your catalogue." Identical in Phase 1; its
    # search_<thing> tool is generated from the tenant's data source once
    # Phase 2 lands, because its schema does not exist until they upload data.
    CATALOGUE: [_SEARCH_KNOWLEDGE, _REQUEST_HUMAN_AGENT],
}

DEFAULT_PRESET = QNA


def unique_slug(name: str, *, fallback: str = "chatbot") -> str:
    """A URL-safe, platform-unique slug derived from a company name.

    Unique across all tenants, since the slug is resolved before any tenant is
    known. Collisions get a numeric suffix rather than an error, because this
    runs inside registration where failing is worse than an ugly URL.
    """
    base = slugify(name)[:56].strip("-") or fallback
    candidate = base
    suffix = 2
    while Chatbot.objects.filter(slug=candidate).exists():
        candidate = f"{base}-{suffix}"[:64]
        suffix += 1
    return candidate


def provision_tools(chatbot: Chatbot, preset: str = DEFAULT_PRESET) -> list[Tool]:
    """Create this preset's tool rows, skipping ones the bot already has.

    Idempotent by `(chatbot, name)`, so re-running it — or running it with a
    richer preset to upgrade a bot — never duplicates and never overwrites a
    description a company has since edited.
    """
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset {preset!r}. Known: {sorted(PRESETS)}")

    existing = set(chatbot.tools.values_list("name", flat=True))
    created = []
    for spec in PRESETS[preset]:
        if spec["name"] in existing:
            continue
        created.append(Tool.objects.create(chatbot=chatbot, **spec))
    return created


@transaction.atomic
def provision_chatbot(company, preset: str = DEFAULT_PRESET, **overrides) -> Chatbot:
    """Create a company's chatbot and its preset tools. Step 2 of the B0 flow."""
    name = overrides.pop("name", None) or f"{company.name} Assistant"
    slug = overrides.pop("slug", None) or unique_slug(company.name)

    chatbot = Chatbot.objects.create(company=company, name=name, slug=slug, **overrides)
    provision_tools(chatbot, preset)
    return chatbot
