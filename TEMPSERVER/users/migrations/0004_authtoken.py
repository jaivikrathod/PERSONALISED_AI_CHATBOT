"""Bearer-token sessions for the standalone `users.User` model.

Replaces the previous non-authentication, where `IsAdminOrManager` accepted any
request carrying `?user_type=Admin` in the query string.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_update_user_types"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuthToken",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                # SHA-256 digest of the raw token; the raw value is never stored.
                ("key_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auth_tokens",
                        to="users.user",
                    ),
                ),
            ],
            options={
                "db_table": "auth_tokens",
                "ordering": ("-created_at",),
            },
        ),
    ]
