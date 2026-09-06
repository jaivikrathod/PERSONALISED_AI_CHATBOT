"""WebSocket consumer for the human-agent console.

An agent connects to ``ws/agent/?token=<bearer token>`` and joins their personal
group. The identity comes from the token, never from an id in the query string:
the previous ``?agent_id=`` form let anyone read any agent's inbox.

From then on they receive:

  * ``chat_assigned``  - a session the bot could not answer was handed to them;
  * ``chat_message``   - a new message inside one of their sessions;
  * ``chat_closed``    - a session they were handling was closed.

They can also push into the socket to reply to a customer, which stores the
message and mirrors it into the customer's session group so the widget shows
it instantly.
"""

import json
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from users.models import AuthToken, User, hash_token

from .models import ChatMessage, ChatSession
from .serializers import ChatMessageSerializer, ChatSessionListSerializer
from .services import (
    ACTIVE_SESSION_STATUSES,
    agent_group,
    message_event,
    send_to_group,
    session_group,
    with_last_message,
)

logger = logging.getLogger(__name__)


class AgentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        params = parse_qs(self.scope.get("query_string", b"").decode())
        token = (params.get("token") or [None])[0]

        agent = await self._get_agent(token)
        if agent is None:
            # 4001: bad/expired token, or not an active Agent-type user.
            await self.close(code=4001)
            return

        self.agent_id = agent["id"]
        self.group_name = agent_group(self.agent_id)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self._send_json(
            {
                "type": "connected",
                "agent_id": self.agent_id,
                "agent_name": agent["name"],
                "chats": await self._list_chats(),
            }
        )

    async def disconnect(self, code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not getattr(self, "agent_id", None):
            return

        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self._send_error("Invalid message format.")
            return

        action = payload.get("action") or "message"

        if action == "refresh":
            await self._send_json({"type": "chats", "chats": await self._list_chats()})
            return

        if action == "history":
            await self._handle_history(payload)
            return

        if action == "close":
            await self._handle_close(payload)
            return

        if action == "message":
            await self._handle_message(payload)
            return

        await self._send_error(f"Unknown action: {action}")

    # --- Actions ------------------------------------------------------------
    async def _handle_history(self, payload):
        session_id = payload.get("session_id")
        messages = await self._history(session_id)
        if messages is None:
            await self._send_error("Chat session not found for this agent.")
            return
        await self._send_json(
            {"type": "history", "session_id": session_id, "messages": messages}
        )

    async def _handle_message(self, payload):
        session_id = payload.get("session_id")
        message = (payload.get("message") or "").strip()

        if not session_id:
            await self._send_error("session_id is required.")
            return
        if not message:
            await self._send_error("Message cannot be empty.")
            return

        stored = await self._store_agent_message(session_id, message)
        if stored is None:
            await self._send_error("Chat session not found for this agent.")
            return

        # Customer widget first, then every tab this agent has open.
        await send_to_group(
            session_group(session_id),
            {"type": "chat.message", "message": stored},
        )
        await send_to_group(
            self.group_name,
            {"type": "chat.message", "message": stored},
        )

    async def _handle_close(self, payload):
        session_id = payload.get("session_id")
        if not session_id:
            await self._send_error("session_id is required.")
            return

        closed = await self._close_session(session_id)
        if not closed:
            await self._send_error("Chat session not found for this agent.")
            return

        await send_to_group(
            session_group(session_id),
            {"type": "chat.closed", "session_id": session_id},
        )
        await send_to_group(
            self.group_name,
            {"type": "chat.closed", "session_id": session_id},
        )

    # --- Group event handlers ----------------------------------------------
    async def chat_assigned(self, event):
        await self._send_json(
            {
                "type": "chat_assigned",
                "session": event["session"],
                "chats": await self._list_chats(),
            }
        )

    async def chat_message(self, event):
        await self._send_json({"type": "chat_message", "message": event["message"]})

    async def chat_closed(self, event):
        await self._send_json(
            {
                "type": "chat_closed",
                "session_id": event["session_id"],
                "chats": await self._list_chats(),
            }
        )

    # --- Helpers ------------------------------------------------------------
    async def _send_json(self, payload):
        await self.send(json.dumps(payload))

    async def _send_error(self, error):
        await self._send_json({"type": "error", "error": error})

    @database_sync_to_async
    def _get_agent(self, raw_token):
        """Resolve a bearer token to an active Agent, or None."""
        if not raw_token:
            return None

        auth = (
            AuthToken.objects.select_related("user")
            .filter(key_hash=hash_token(raw_token))
            .first()
        )
        if auth is None or auth.is_expired:
            return None

        agent = auth.user
        if (
            agent.type != User.Type.AGENT
            or not agent.active
            or agent.is_archived
        ):
            return None

        return {"id": agent.id, "name": agent.name, "company_id": agent.company_id}

    @database_sync_to_async
    def _list_chats(self):
        sessions = with_last_message(ChatSession.objects.filter(agent_id=self.agent_id))
        return ChatSessionListSerializer(sessions, many=True).data

    @database_sync_to_async
    def _history(self, session_id):
        session = (
            ChatSession.objects.prefetch_related("messages")
            .filter(id=session_id, agent_id=self.agent_id)
            .first()
        )
        if session is None:
            return None
        return ChatMessageSerializer(session.messages.all(), many=True).data

    @database_sync_to_async
    def _store_agent_message(self, session_id, message):
        session = ChatSession.objects.filter(
            id=session_id,
            agent_id=self.agent_id,
        ).first()
        if session is None:
            return None

        chat_message = ChatMessage.objects.create(
            company_id=session.company_id,
            session=session,
            message=message,
            sent_by_us=True,
            is_ai=False,
            this_user_id=self.agent_id,
            message_type=ChatMessage.MessageType.TEXT,
        )

        # An agent replying means the handover actually happened.
        if session.status in ACTIVE_SESSION_STATUSES:
            session.status = ChatSession.Status.IN_PROGRESS
        session.save(update_fields=["status", "updated_at"])

        return message_event(chat_message)

    @database_sync_to_async
    def _close_session(self, session_id):
        session = ChatSession.objects.filter(
            id=session_id,
            agent_id=self.agent_id,
        ).first()
        if session is None:
            return False

        session.status = ChatSession.Status.CLOSED
        session.closed_at = timezone.now()
        session.agent_needed = False
        session.save(
            update_fields=["status", "closed_at", "agent_needed", "updated_at"]
        )
        return True
