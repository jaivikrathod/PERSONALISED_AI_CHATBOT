"""Agent assignment service layer.

Handles the assign / transfer / close lifecycle and agent notifications. All
operations are tenant-safe: an agent can only be assigned to a conversation in
their own company.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.enums import ConversationStatus, UserRole
from core.exceptions import ServiceError, TenantIsolationError

from .models import AgentAvailability, ConversationAssignment

logger = logging.getLogger(__name__)


def _assert_same_company(conversation, agent):
    if agent.role == UserRole.SUPER_ADMIN:
        return
    if conversation.company_id != agent.company_id:
        raise TenantIsolationError("Agent and conversation belong to different companies.")


@transaction.atomic
def assign_conversation(conversation, agent) -> ConversationAssignment:
    """Assign a conversation to an agent and mark it ACTIVE_AGENT."""
    _assert_same_company(conversation, agent)

    if conversation.status == ConversationStatus.RESOLVED:
        raise ServiceError("Cannot assign a resolved conversation.")

    # Release any existing active assignment (idempotent re-assign / takeover).
    ConversationAssignment.objects.filter(
        conversation=conversation, is_active=True
    ).exclude(agent=agent).update(is_active=False, released_at=timezone.now())

    assignment, _ = ConversationAssignment.objects.update_or_create(
        conversation=conversation,
        agent=agent,
        is_active=True,
        defaults={"assigned_at": timezone.now(), "released_at": None},
    )

    conversation.status = ConversationStatus.ACTIVE_AGENT
    conversation.save(update_fields=["status", "updated_at"])

    _notify_conversation(conversation, "agent_joined", {"agent_id": agent.id})
    return assignment


@transaction.atomic
def transfer_conversation(conversation, to_agent) -> ConversationAssignment:
    """Hand an active conversation from its current agent to another."""
    _assert_same_company(conversation, to_agent)

    ConversationAssignment.objects.filter(
        conversation=conversation, is_active=True
    ).update(is_active=False, released_at=timezone.now())

    assignment = ConversationAssignment.objects.create(
        conversation=conversation, agent=to_agent, is_active=True
    )
    conversation.status = ConversationStatus.ACTIVE_AGENT
    conversation.save(update_fields=["status", "updated_at"])

    _notify_conversation(conversation, "agent_transferred", {"agent_id": to_agent.id})
    return assignment


@transaction.atomic
def close_conversation(conversation) -> None:
    """Release the active assignment and mark the conversation resolved."""
    ConversationAssignment.objects.filter(
        conversation=conversation, is_active=True
    ).update(is_active=False, released_at=timezone.now())

    conversation.status = ConversationStatus.RESOLVED
    conversation.resolved_at = timezone.now()
    conversation.save(update_fields=["status", "resolved_at", "updated_at"])

    _notify_conversation(conversation, "conversation_closed", {})


def available_agents_for_company(company_id):
    """Online agents in a company with free capacity, least-loaded first."""
    from django.db.models import Count, F, Q

    return (
        AgentAvailability.objects.filter(online=True, user__company_id=company_id)
        .select_related("user")
        .annotate(
            active_chats=Count(
                "user__assignments",
                filter=Q(user__assignments__is_active=True),
            )
        )
        .filter(active_chats__lt=F("max_active_chats"))
        .order_by("active_chats")
    )


def notify_available_agents(conversation, reason: str):
    """Broadcast a 'chat needs an agent' event to a company's agent channel."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f"agents_company_{conversation.company_id}",
            {
                "type": "agent.notify",
                "event": "escalation",
                "reason": reason,
                "conversation": str(conversation.uuid),
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to broadcast agent notification")


def _notify_conversation(conversation, event: str, payload: dict):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f"conversation_{conversation.uuid}",
            {"type": "chat.event", "event": event, "payload": payload},
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to broadcast conversation event")
