"""Tenant (Company) models.

A Company is the top-level tenant boundary. UserCompany expresses membership +
role for users who belong to multiple companies (the user's *active* company is
denormalised onto accounts.User.company for fast isolation checks).
"""

from django.conf import settings
from django.db import models

from core.enums import CompanyStatus, UserRole
from core.models import BaseModel, SoftDeleteModel


class Company(BaseModel, SoftDeleteModel):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=CompanyStatus.choices,
        default=CompanyStatus.TRIAL,
        db_index=True,
    )

    class Meta:
        db_table = "companies_company"
        ordering = ["-created_at"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name

    def get_object_company_id(self):
        return self.id


class UserCompany(BaseModel):
    """Membership of a user in a company, with the role held *in that company*."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_memberships",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="user_memberships",
    )
    role = models.CharField(
        max_length=32,
        choices=UserRole.choices,
        default=UserRole.AGENT,
    )

    class Meta:
        db_table = "companies_user_company"
        constraints = [
            models.UniqueConstraint(fields=["user", "company"], name="uniq_user_company"),
        ]
        indexes = [models.Index(fields=["company", "role"])]

    def __str__(self):
        return f"{self.user_id} @ {self.company_id} ({self.role})"
