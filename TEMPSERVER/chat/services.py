"""Agent assignment + realtime fan-out helpers shared by views and consumers.

Two things live here because both the HTTP layer (``chat.views``) and the
WebSocket layer (``chat.consumers`` / ``questions.consumers``) need them:

  * picking a free human agent for a session that the bot could not answer;
  * pushing events onto the channel layer so the agent inbox and the customer
    widget update without polling.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Count, OuterRef, Subquery

from users.models import User

from .models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)

# A session in one of these states is still live, so the agent sitting on it is
# considered busy. Only closing a chat hands the agent back to the pool.
ACTIVE_SESSION_STATUSES = (
    ChatSession.Status.OPEN,
    ChatSession.Status.IN_PROGRESS,
)


# --- Channel layer group names ---------------------------------------------
def agent_group(agent_id):
    """Group that carries everything one agent should see (their inbox)."""
    return f"agent_{agent_id}"


def session_group(session_id):
    """Group that carries everything happening inside one chat session."""
    return f"chat_session_{session_id}"


# --- Assignment -------------------------------------------------------------
def pick_free_agent(company_id, exclude_session_id=None):
    """Return an Agent-type user of this company who is not on a live chat.

    "Free" means their id does not appear in the ``agent`` column of any chat
    session that is still open/in progress.
    """
    busy = ChatSession.objects.filter(
        status__in=ACTIVE_SESSION_STATUSES,
        agent_id__isnull=False,
    )
    if exclude_session_id is not None:
        busy = busy.exclude(id=exclude_session_id)

    busy_agent_ids = busy.values_list("agent_id", flat=True).distinct()

    return (
        User.objects.filter(
            company_id=company_id,
            type=User.Type.AGENT,
            active=True,
            is_archived=False,
        )
        .exclude(id__in=busy_agent_ids)
        .order_by("id")
        .first()
    )


def flag_agent_needed(session):
    """Mark ``session`` as needing a human and attach a free agent to it.

    Returns the assigned agent, or ``None`` when every agent of the company is
    already busy (the session stays flagged so it can be picked up later).
    Calling this again on an already-assigned session is a no-op.
    """
    update_fields = []

    if not session.agent_needed:
        session.agent_needed = True
        update_fields.append("agent_needed")

    agent = session.agent
    if agent is None:
        agent = pick_free_agent(session.company_id, exclude_session_id=session.id)
        if agent is not None:
            session.agent = agent
            update_fields.append("agent")

    if update_fields:
        session.save(update_fields=update_fields + ["updated_at"])
        logger.info(
            "Session #%s flagged for an agent (assigned=%s)",
            session.id,
            getattr(agent, "id", None),
        )

    return agent


# --- Session listing --------------------------------------------------------
def with_last_message(queryset):
    """Attach `last_message_obj` + `message_count` to each session in a list.

    Shared by the customer inbox, the agent inbox and the agent socket so all
    three render the same session summary.
    """
    latest_message = ChatMessage.objects.filter(session_id=OuterRef("pk")).order_by(
        "-created_at"
    )
    sessions = (
        queryset.select_related("company", "agent")
        .annotate(
            last_message_id=Subquery(latest_message.values("id")[:1]),
            message_count=Subquery(
                ChatMessage.objects.filter(session_id=OuterRef("pk"))
                .order_by()
                .values("session_id")
                .annotate(count=Count("id"))
                .values("count")[:1]
            ),
        )
        .order_by("-updated_at")
        .distinct()
    )

    sessions = list(sessions)
    message_map = {
        message.id: message
        for message in ChatMessage.objects.filter(
            id__in=[s.last_message_id for s in sessions if s.last_message_id]
        )
    }
    for session in sessions:
        session.last_message_obj = message_map.get(session.last_message_id)

    return sessions


# --- Broadcasting -----------------------------------------------------------
async def send_to_group(group, payload):
    layer = get_channel_layer()
    if layer is None:  # No channel layer configured (e.g. plain WSGI tests).
        return
    await layer.group_send(group, payload)


def send_to_group_sync(group, payload):
    async_to_sync(send_to_group)(group, payload)


def session_event(session, agent_id=None):
    """Compact session summary used by the `chat.assigned` inbox event."""
    return {
        "id": session.id,
        "company": session.company_id,
        "agent": agent_id if agent_id is not None else session.agent_id,
        "agent_needed": session.agent_needed,
        "status": session.status,
    }


def message_event(chat_message):
    """Compact message payload shared by both sockets."""
    if chat_message.is_ai:
        sender = "ai"
    elif chat_message.sent_by_us:
        sender = "agent"
    else:
        sender = "customer"

    return {
        "id": chat_message.id,
        "session_id": chat_message.session_id,
        "message": chat_message.message,
        "sender": sender,
        "is_ai": chat_message.is_ai,
        "sent_by_us": chat_message.sent_by_us,
        "customer_user_name": chat_message.customer_user_name,
        "created_at": chat_message.created_at.isoformat(),
    }
