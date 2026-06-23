"""WebSocket consumers for realtime chat.

Two socket types share the same conversation room (`conversation_<uuid>`):

* VisitorConsumer  - authenticated by the chatbot widget_token + session. Public.
* AgentConsumer    - authenticated by JWT (see core.ws_auth). Dashboard side.

Both support: incoming messages, typing indicators and read receipts. Messages
are processed through the SAME ChatService used by the REST API, so behaviour is
identical across transports.
"""

import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from core.enums import SenderType


class _BaseChatConsumer(AsyncWebsocketConsumer):
    """Shared room plumbing + event fan-out."""

    async def connect(self):
        self.conversation_uuid = self.scope["url_route"]["kwargs"]["conversation_uuid"]
        self.group_name = f"conversation_{self.conversation_uuid}"

        self.conversation = await self._load_conversation(self.conversation_uuid)
        if self.conversation is None or not await self.authorize():
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            return

        action = data.get("action", "message")

        if action == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "chat.typing", "sender": self.sender_label(), "is_typing": data.get("is_typing", True)},
            )
        elif action == "read":
            await self._mark_read(data.get("message_id"))
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "chat.read", "sender": self.sender_label(), "message_id": data.get("message_id")},
            )
        elif action == "message":
            await self.handle_message(data.get("message", ""))

    # -- group event handlers (called via group_send `type`) ---------------
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"event": "message", **event["message"]}))

    async def chat_typing(self, event):
        await self.send(text_data=json.dumps({"event": "typing", **{k: event[k] for k in ("sender", "is_typing")}}))

    async def chat_read(self, event):
        await self.send(text_data=json.dumps({"event": "read", "sender": event["sender"], "message_id": event["message_id"]}))

    async def chat_event(self, event):
        await self.send(text_data=json.dumps({"event": event["event"], "payload": event["payload"]}))

    # -- hooks overridden by subclasses ------------------------------------
    async def authorize(self) -> bool:
        raise NotImplementedError

    def sender_label(self) -> str:
        raise NotImplementedError

    async def handle_message(self, text: str):
        raise NotImplementedError

    # -- db helpers ---------------------------------------------------------
    @sync_to_async
    def _load_conversation(self, uuid):
        from .models import Conversation

        return (
            Conversation.objects.select_related("chatbot", "visitor", "company")
            .filter(uuid=uuid)
            .first()
        )

    @sync_to_async
    def _mark_read(self, message_id):
        from django.utils import timezone

        from .models import Message

        if not message_id:
            return
        Message.objects.filter(id=message_id, conversation=self.conversation, read_at__isnull=True).update(
            read_at=timezone.now()
        )

    @sync_to_async
    def _run_chat(self, text):
        from .services import ChatService

        return ChatService(self.conversation).handle_user_message(text)

    @sync_to_async
    def _save_agent_message(self, text, user):
        from .services import ChatService

        return ChatService(self.conversation)._save_message(
            SenderType.AGENT, text, sender_agent=user
        )


class VisitorConsumer(_BaseChatConsumer):
    """Public widget socket. Authorised by matching the chatbot's widget_token."""

    async def authorize(self) -> bool:
        from urllib.parse import parse_qs

        query = parse_qs(self.scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        return bool(token) and token == self.conversation.chatbot.widget_token

    def sender_label(self) -> str:
        return "visitor"

    async def handle_message(self, text: str):
        if text.strip():
            # ChatService persists + broadcasts both the visitor msg and bot reply.
            await self._run_chat(text)


class AgentConsumer(_BaseChatConsumer):
    """Dashboard socket. Authorised by JWT (scope['user']) + company match."""

    async def authorize(self) -> bool:
        user = self.scope.get("user")
        if not (user and user.is_authenticated):
            return False
        from core.enums import UserRole

        if user.role == UserRole.SUPER_ADMIN:
            return True
        return user.company_id == self.conversation.company_id

    def sender_label(self) -> str:
        return "agent"

    async def handle_message(self, text: str):
        if text.strip():
            await self._save_agent_message(text, self.scope["user"])
