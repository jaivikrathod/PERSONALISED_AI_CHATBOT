"""One Chatbot per existing Company, with its two preset tools.

Every company that works today must keep working with no client change, so the
backfill runs here rather than being an onboarding step nobody performs for
existing tenants.

Deliberately *not* importing `registry.presets`: a data migration must keep
behaving the way it did on the day it was written, and that module will grow a
third preset. The tool specs are copied in, frozen.
"""

from django.db import migrations
from django.utils.text import slugify


PRESET_TOOLS = [
    {
        "name": "search_knowledge",
        "tool_type": "KNOWLEDGE_SEARCH",
        "description": (
            "Search the company's own documented answers, policies and product "
            "information. Use whenever the customer asks something factual about "
            "this company. Do not use for greetings or small talk. An empty result "
            "means nothing relevant is documented — say so, do not guess."
        ),
        "input_schema": {
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
        },
        "configuration": {},
    },
    {
        "name": "request_human_agent",
        "tool_type": "HANDOFF",
        "description": (
            "Hand the conversation to a human colleague. Use when the customer "
            "asks for a person, is upset, or when you cannot help after genuinely "
            "trying. Do not use as a first response to a hard question."
        ),
        "input_schema": {
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
        },
        "configuration": {"queue": "default", "reason_required": True},
    },
]


def _unique_slug(Chatbot, name, taken):
    base = (slugify(name)[:56].strip("-")) or "chatbot"
    candidate = base
    suffix = 2
    while candidate in taken or Chatbot.objects.filter(slug=candidate).exists():
        candidate = f"{base}-{suffix}"[:64]
        suffix += 1
    taken.add(candidate)
    return candidate


def forwards(apps, schema_editor):
    Company = apps.get_model("company", "Company")
    Chatbot = apps.get_model("registry", "Chatbot")
    Tool = apps.get_model("registry", "Tool")

    # `policy` is left empty on purpose. The model's default lives in Python and
    # will change; `Chatbot.get_policy()` falls back to it, so backfilled rows
    # inherit new budgets instead of being pinned to today's values.
    taken = set()
    for company in Company.objects.all().order_by("id"):
        if Chatbot.objects.filter(company_id=company.id).exists():
            continue

        chatbot = Chatbot.objects.create(
            company_id=company.id,
            slug=_unique_slug(Chatbot, company.name, taken),
            name=f"{company.name} Assistant",
            policy={},
        )
        for spec in PRESET_TOOLS:
            Tool.objects.create(chatbot=chatbot, **spec)


def backwards(apps, schema_editor):
    # Rows created here are indistinguishable from ones an admin created since,
    # so unwinding would delete real configuration. Reversing the schema
    # migration drops the tables anyway.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0001_initial"),
        ("company", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
