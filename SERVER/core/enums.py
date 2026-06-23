"""Central enumerations shared across apps."""

from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    COMPANY_ADMIN = "COMPANY_ADMIN", "Company Admin"
    MANAGER = "MANAGER", "Manager"
    AGENT = "AGENT", "Agent"


class CompanyStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    TRIAL = "TRIAL", "Trial"


class ConversationStatus(models.TextChoices):
    BOT = "BOT", "Handled by bot"
    WAITING_AGENT = "WAITING_AGENT", "Waiting for agent"
    ACTIVE_AGENT = "ACTIVE_AGENT", "Active with agent"
    RESOLVED = "RESOLVED", "Resolved"


class SenderType(models.TextChoices):
    VISITOR = "VISITOR", "Visitor"
    BOT = "BOT", "Bot"
    AGENT = "AGENT", "Agent"
