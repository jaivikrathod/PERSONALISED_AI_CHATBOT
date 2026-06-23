"""Account signals.

Keeps `companies.UserCompany` membership in sync with the user's primary
company so the two representations never drift apart.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def sync_user_company_membership(sender, instance, created, **kwargs):
    """When a user is assigned to a company, ensure a UserCompany row exists."""
    if not instance.company_id:
        return

    # Imported lazily to avoid an app-loading cycle (companies imports accounts).
    from companies.models import UserCompany

    UserCompany.objects.update_or_create(
        user=instance,
        company_id=instance.company_id,
        defaults={"role": instance.role},
    )
