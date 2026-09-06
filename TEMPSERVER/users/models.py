import hashlib
import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone

from company.models import Company


class User(models.Model):
    """Application user that belongs to a Company."""

    # --- Choice definitions -------------------------------------------------
    # Using TextChoices keeps the stored value and the human-readable label
    # together and makes the choices reusable across serializers/forms.
    class Gender(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"
        OTHER = "Other", "Other"

    class Type(models.TextChoices):
        ADMIN = "Admin", "Admin"
        AGENT = "Agent", "Agent"
        MANAGER = "Manager", "Manager"

    # --- Fields -------------------------------------------------------------
    # `id` is created automatically by Django as an AutoField primary key,
    # so it is declared explicitly here only to match the spec.
    id = models.AutoField(primary_key=True)

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    # Hashed password (never stored in plain text). Set via
    # `user.set_password(raw)` / checked via `user.check_password(raw)`.
    password = models.CharField(max_length=255)

    gender = models.CharField(max_length=10, choices=Gender.choices)
    dob = models.DateField()

    # ForeignKey stored in the DB column `company_id` (Django's default for
    # a FK named `company`). CASCADE removes users when their company is deleted.
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="users",
    )

    type = models.CharField(max_length=10, choices=Type.choices)

    active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        ordering = ("-created_at",)

    def __str__(self):
        # Readable representation used in the admin, shell and logs.
        return f"{self.name} <{self.email}>"

    # --- Password helpers ---------------------------------------------------
    # Django's PBKDF2 hashing is reused so we never store plain-text passwords,
    # even though this is a standalone model (not django.contrib.auth.User).
    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password

        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password

        return check_password(raw_password, self.password)

    # --- DRF integration ----------------------------------------------------
    # `request.user` is expected to answer these; the standalone model is not a
    # `django.contrib.auth` user, so they are declared explicitly. Permission
    # classes rely on `is_authenticated` to tell a real user from AnonymousUser.
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


# How long a token stays valid. Refreshed only by re-login, not by use.
TOKEN_TTL = timedelta(days=14)


def hash_token(raw: str) -> str:
    """SHA-256 of a raw token. The digest is all that is ever stored."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuthToken(models.Model):
    """One live session for a user.

    `key_hash` is the lookup column — the raw token never touches the database,
    so a leaked dump cannot be replayed as a set of live sessions.
    """

    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="auth_tokens",
    )

    key_hash = models.CharField(max_length=64, unique=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_tokens"
        ordering = ("-created_at",)

    def __str__(self):
        return f"Token for user {self.user_id}"

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    @classmethod
    def issue(cls, user) -> tuple["AuthToken", str]:
        """Create a token for `user`. Returns (row, raw token — shown once)."""
        raw = secrets.token_urlsafe(32)
        token = cls.objects.create(
            user=user,
            key_hash=hash_token(raw),
            expires_at=timezone.now() + TOKEN_TTL,
        )
        return token, raw

    @classmethod
    def purge_expired(cls) -> int:
        deleted, _ = cls.objects.filter(expires_at__lte=timezone.now()).delete()
        return deleted

