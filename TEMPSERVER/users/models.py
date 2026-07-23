from django.db import models

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
