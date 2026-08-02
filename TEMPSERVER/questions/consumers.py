"""WebSocket consumer that powers the chatbot.

For each user message we:
  1. Create or reuse a chat session.
  2. Store the user's message.
  3. Generate the FAQ-based answer.
  4. Store the AI response.
"""

import json
import logging
import math

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from chat.models import ChatMessage, ChatSession
from chat.services import (
    ACTIVE_SESSION_STATUSES,
    agent_group,
    flag_agent_needed,
    message_event,
    send_to_group,
    session_event,
    session_group,
)
from vector_question.services import LLMError, generate_answer, generate_embedding

from .models import Question, UnansweredMessage

logger = logging.getLogger(__name__)

TOP_K = 3

# Shown to the customer whenever we can't answer from the FAQ and are handing
# the conversation off to a human agent (session.agent_needed is set too).
AGENT_HANDOFF_MESSAGE = (
    "I'm not able to answer that from our FAQ right now. "
    "Let me connect you with one of our support agents who'll help you shortly."
)


def _cosine_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


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
        logger.info("Received message: %s", text_data)
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self._send_error("Invalid message format.")
            return

        message = (payload.get("message") or "").strip()
        company_id = payload.get("company_id")
        session_id = payload.get("session_id")
        customer_user_id = payload.get("customer_user_id")
        customer_user_name = (payload.get("customer_user_name") or "").strip()
        customer_user_email = (payload.get("customer_user_email") or "").strip()

        if not message:
            await self._send_error("Message cannot be empty.")
            return
        if company_id is None:
            await self._send_error("company_id is required.")
            return

        session = await self._get_or_create_session(session_id, company_id)
        await self._join_session_group(session.id)
        stored = await self._store_message(
            session=session,
            company_id=company_id,
            message=message,
            sent_by_us=False,
            is_ai=False,
            customer_user_id=customer_user_id,
            customer_user_name=customer_user_name,
            customer_user_email=customer_user_email,
        )

        # A human already owns this conversation: hand the message straight to
        # them and keep the AI out of it.
        live_agent_id = await self._live_agent_id(session)
        if live_agent_id:
            await send_to_group(
                agent_group(live_agent_id),
                {"type": "chat.message", "message": message_event(stored)},
            )
            await self.send(
                json.dumps(
                    {
                        "type": "delivered",
                        "session_id": session.id,
                        "agent_needed": True,
                        "agent_handling": True,
                    }
                )
            )
            return

        matches = await self._top_matches(message, company_id)

        for score, question, answer in matches:
            logger.info(
                "Vector match | score=%.4f | question=%r | answer=%r",
                score,
                question,
                answer,
            )

        if not matches:
            answer = AGENT_HANDOFF_MESSAGE
            await self._store_unanswered(message, company_id)
            await self._handoff_to_agent(session)
            await self._store_message(
                session=session,
                company_id=company_id,
                message=answer,
                sent_by_us=True,
                is_ai=True,
                customer_user_id=customer_user_id,
                customer_user_name=customer_user_name,
                customer_user_email=customer_user_email,
            )
            await self.send(
                json.dumps(
                    {
                        "type": "answer",
                        "answer": answer,
                        "is_answer_found": False,
                        "agent_needed": True,
                        "sources": [],
                        "session_id": session.id,
                    }
                )
            )
            return

        best_score = matches[0][0]
        logger.info("Best match score: %.4f", best_score)
        logger.info(
            "Confidence threshold: %.4f", settings.CHAT_CONFIDENCE_THRESHOLD
        )
        if best_score < settings.CHAT_CONFIDENCE_THRESHOLD:
            answer = AGENT_HANDOFF_MESSAGE
            # The question isn't reliably covered by our FAQ database — park it
            # so a human can supply an answer later, and flag for a human agent.
            await self._store_unanswered(message, company_id)
            await self._handoff_to_agent(session)
            await self._store_message(
                session=session,
                company_id=company_id,
                message=answer,
                sent_by_us=True,
                is_ai=True,
                customer_user_id=customer_user_id,
                customer_user_name=customer_user_name,
                customer_user_email=customer_user_email,
            )
            await self.send(
                json.dumps(
                    {
                        "type": "answer",
                        "answer": answer,
                        "score": round(best_score, 4),
                        "is_answer_found": False,
                        "agent_needed": True,
                        "sources": [],
                        "session_id": session.id,
                    }
                )
            )
            return

        # return
               
        faq_pairs = [(question, answer) for _, question, answer in matches]
        try:
            answer, is_answer_found = await sync_to_async(generate_answer)(
                message, faq_pairs
            )
        except LLMError as exc:
            await self._send_error(str(exc))
            return

        # Even though a vector match cleared the threshold, the LLM may still
        # decide the FAQ context can't actually answer the question. Treat that
        # as unanswered: park it for review, flag the session for a human, and
        # hand off to an agent instead of showing the model's apology.
        if not is_answer_found:
            answer = AGENT_HANDOFF_MESSAGE
            await self._store_unanswered(message, company_id)
            await self._handoff_to_agent(session)


        await self._store_message(
            session=session,
            company_id=company_id,
            message=answer,
            sent_by_us=True,
            is_ai=True,
            customer_user_id=customer_user_id,
            customer_user_name=customer_user_name,
            customer_user_email=customer_user_email,
        )

        await self.send(
            json.dumps(
                {
                    "type": "answer",
                    "answer": answer,
                    "score": round(best_score, 4),
                    "is_answer_found": is_answer_found,
                    "agent_needed": not is_answer_found,
                    "sources": [
                        {"question": question, "score": round(score, 4)}
                        for score, question, _ in matches
                    ],
                    "session_id": session.id,
                }
            )
        )

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

    async def _handoff_to_agent(self, session):
        """Flag the session, assign a free agent and ping their console."""
        assignment = await self._flag_and_assign(session)
        if assignment is None:
            logger.info("Session #%s needs an agent but none are free", session.id)
            return

        await send_to_group(
            agent_group(assignment["agent_id"]),
            {"type": "chat.assigned", "session": assignment["session"]},
        )

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

    @database_sync_to_async
    def _get_or_create_session(self, session_id, company_id):
        if session_id:
            session = ChatSession.objects.filter(
                id=session_id,
                company_id=company_id,
            ).first()
            if session:
                return session

        return ChatSession.objects.create(company_id=company_id)

    @database_sync_to_async
    def _store_message(
        self,
        session,
        company_id,
        message,
        sent_by_us,
        is_ai,
        customer_user_id=None,
        customer_user_name="",
        customer_user_email="",
    ):
        return ChatMessage.objects.create(
            company_id=company_id,
            session=session,
            customer_user_id=customer_user_id if customer_user_id else None,
            customer_user_name=customer_user_name,
            customer_user_email=customer_user_email,
            message=message,
            sent_by_us=sent_by_us,
            is_ai=is_ai,
            message_type=ChatMessage.MessageType.TEXT,
        )

    @database_sync_to_async
    def _store_unanswered(self, message, company_id):
        return UnansweredMessage.objects.create(
            company_id=company_id,
            message=message,
        )

    @database_sync_to_async
    def _live_agent_id(self, session):
        """Agent id currently handling this session, if the chat is still live."""
        # Re-read: the agent may have been attached after this socket connected.
        row = (
            ChatSession.objects.filter(id=session.id)
            .values("agent_id", "status")
            .first()
        )
        if row and row["agent_id"] and row["status"] in ACTIVE_SESSION_STATUSES:
            return row["agent_id"]
        return None

    @database_sync_to_async
    def _flag_and_assign(self, session):
        agent = flag_agent_needed(session)
        if agent is None:
            return None
        return {
            "agent_id": agent.id,
            "session": session_event(session, agent_id=agent.id),
        }

    @database_sync_to_async
    def _top_matches(self, message, company_id):
        query_embedding = generate_embedding(message)

        queryset = Question.objects.filter(is_archived=False, is_vectorized=True)
        if company_id is not None:
            queryset = queryset.filter(company_id=company_id)

        scored = []
        for row in queryset.only("id", "question", "answer", "embedding").iterator():
            if not row.embedding:
                continue
            scored.append(
                (
                    _cosine_similarity(query_embedding, row.embedding),
                    row.question,
                    row.answer,
                )
            )

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:TOP_K]
