"""WebSocket transport for the chatbot (`ws/chat/`).

This file is transport only (WORKFLOW.md Phase 1.6): parse the frame, resolve
the session, hand the message to `orchestration.run_turn`, stream its frames
back. Routing, retrieval, relevance gates and model calls all live in the
orchestrator — if you are about to add an `if` about *what to answer* here,
it belongs there instead.

Outbound frames keep the shape `TEMPFRONTEND` already reads (`answer`,
`delivered`, `error`, `agent_message`, `chat_closed`), plus `tool_started` for
the "checking…" indicator (B9).
"""

import json
import logging

from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from chat.services import session_group
from orchestration.orchestrator import resolve_session, run_turn

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Set once the first message reveals which session this socket belongs
        # to; used to receive live replies from the assigned human agent.
        self.session_group_name = None
        await self.accept()

    async def disconnect(self, code):
        if self.session_group_name:
            await self.channel_layer.group_discard(
                self.session_group_name, self.channel_name
            )
            self.session_group_name = None

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self._send_error("Invalid message format.")
            return

        message = (payload.get("message") or "").strip()
        company_id = payload.get("company_id")
        if not message:
            await self._send_error("Message cannot be empty.")
            return
        if company_id is None:
            await self._send_error("company_id is required.")
            return

        customer = {
            "customer_user_id": payload.get("customer_user_id"),
            "customer_user_name": (payload.get("customer_user_name") or "").strip(),
            "customer_user_email": (payload.get("customer_user_email") or "").strip(),
        }

        session = await database_sync_to_async(resolve_session)(
            company_id,
            payload.get("session_id"),
            visitor_id=str(customer["customer_user_id"] or ""),
        )
        await self._join_session_group(session.id)
        # The widget stores this and presents it to /api/chat/history/; it is
        # the only proof an anonymous browser owns this conversation.
        session_ref = {"session_id": session.id, "session_token": session.public_token}

        def emit(frame):
            # Called from the orchestrator's worker thread mid-turn.
            async_to_sync(self.send)(json.dumps({**frame, **session_ref}))

        result = await sync_to_async(run_turn)(
            session, message, customer=customer, emit=emit
        )
        for frame in result.frames:
            await self.send(json.dumps({**frame, **session_ref}))

    async def _send_error(self, error):
        await self.send(json.dumps({"type": "error", "error": error}))

    async def _join_session_group(self, session_id):
        """Subscribe this socket to the session so agent replies reach it."""
        group = session_group(session_id)
        if self.session_group_name == group:
            return
        if self.session_group_name:
            await self.channel_layer.group_discard(
                self.session_group_name, self.channel_name
            )
        await self.channel_layer.group_add(group, self.channel_name)
        self.session_group_name = group

    # --- Group events pushed in by the agent console ------------------------
    async def chat_message(self, event):
        """An agent replied — forward it to the customer as a chat bubble."""
        payload = event["message"]
        if payload.get("sender") != "agent":
            return
        await self.send(
            json.dumps(
                {
                    "type": "agent_message",
                    "answer": payload["message"],
                    "session_id": payload["session_id"],
                    "is_answer_found": True,
                    "agent_needed": True,
                    "agent_handling": True,
                    "sources": [],
                }
            )
        )

    async def chat_closed(self, event):
        await self.send(
            json.dumps({"type": "chat_closed", "session_id": event["session_id"]})
        )
