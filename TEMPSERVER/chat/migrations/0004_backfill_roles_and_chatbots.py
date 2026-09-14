"""Backfill the B2.5 columns added by `chat.0003`.

- `chat_message.role`: rows written before orchestration are either the
  customer (`sent_by_us=False` → `user`) or us, AI or human (`assistant`).
- `chat_session.chatbot`: each session gets its company's first chatbot, which
  `registry.0002` guarantees exists.
"""

from django.db import migrations
from django.db.models import OuterRef, Subquery


def forwards(apps, schema_editor):
    ChatMessage = apps.get_model("chat", "ChatMessage")
    ChatSession = apps.get_model("chat", "ChatSession")
    Chatbot = apps.get_model("registry", "Chatbot")

    ChatMessage.objects.filter(sent_by_us=False).update(role="user")
    ChatMessage.objects.filter(sent_by_us=True).update(role="assistant")

    first_bot = (
        Chatbot.objects.filter(company_id=OuterRef("company_id"))
        .order_by("id")
        .values("id")[:1]
    )
    ChatSession.objects.filter(chatbot__isnull=True).update(chatbot_id=Subquery(first_bot))


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_conversation_schema"),
        ("registry", "0002_backfill_chatbots"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
