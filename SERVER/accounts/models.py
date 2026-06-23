"""Custom user model.

Email-based authentication. A user carries a platform `role` and is bound to a
single *active* company (the tenant boundary used everywhere for isolation).
Cross-company membership is expressed through `companies.UserCompany`.
"""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from core.enums import UserRole
from core.models import TimeStampedModel, UUIDModel

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, UUIDModel, TimeStampedModel):
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)

    role = models.CharField(
        max_length=32,
        choices=UserRole.choices,
        default=UserRole.AGENT,
        db_index=True,
    )

    # The tenant this user is currently operating within. SUPER_ADMIN users keep
    # this null because they are not bound to any single company.
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "accounts_user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "role"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.role})"

    # --- Role helpers ------------------------------------------------------
    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_company_admin(self) -> bool:
        return self.role == UserRole.COMPANY_ADMIN

    @property
    def is_manager(self) -> bool:
        return self.role == UserRole.MANAGER

    @property
    def is_agent(self) -> bool:
        return self.role == UserRole.AGENT

    def can_manage_company(self) -> bool:
        """Admins and managers can administer their company."""
        return self.role in {UserRole.COMPANY_ADMIN, UserRole.MANAGER}
