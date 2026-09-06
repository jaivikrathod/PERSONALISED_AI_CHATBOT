"""Give every chat session an unguessable handle for anonymous visitors.

Session ids are sequential integers, so `/api/chat/history/?session_id=` alone
let any visitor read any other visitor's conversation. The token is issued when
the session is created and is the only thing a browser presents to reclaim its
own chat.

Added in three steps because a callable default is evaluated once for the whole
table during ALTER, which would collide against the unique constraint.
"""

import chat.models
from django.db import migrations, models


def backfill_tokens(apps, schema_editor):
    ChatSession = apps.get_model("chat", "ChatSession")
    for session in ChatSession.objects.filter(public_token__isnull=True).iterator():
        session.public_token = chat.models.new_public_token()
        session.save(update_fields=["public_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="public_token",
            field=models.CharField(max_length=64, null=True, editable=False),
        ),
        migrations.RunPython(backfill_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="chatsession",
            name="public_token",
            field=models.CharField(
                default=chat.models.new_public_token,
                editable=False,
                max_length=64,
                unique=True,
            ),
        ),
    ]
