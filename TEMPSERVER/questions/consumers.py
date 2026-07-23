"""WebSocket consumer that powers the chatbot.

For each user message we:
  1. Create or reuse a chat session.
  2. Store the user's message.
  3. Generate the FAQ-based answer.
  4. Store the AI response.
"""

import json
import math

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from chat.models import ChatMessage, ChatSession
from vector_question.services import LLMError, generate_answer, generate_embedding

from .models import Question

TOP_K = 3


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
        await self.accept()

    async def disconnect(self, code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
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
        await self._store_message(
            session=session,
            company_id=company_id,
            message=message,
            sent_by_us=False,
            is_ai=False,
            customer_user_id=customer_user_id,
            customer_user_name=customer_user_name,
            customer_user_email=customer_user_email,
        )

        matches = await self._top_matches(message, company_id)

        if not matches:
            answer = "No matching question found."
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
                        "sources": [],
                        "session_id": session.id,
                    }
                )
            )
            return

        best_score = matches[0][0]

        if best_score < settings.CHAT_CONFIDENCE_THRESHOLD:
            answer = "Sorry, I couldn't find a reliable answer in the FAQ database."
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
                        "sources": [],
                        "session_id": session.id,
                    }
                )
            )
            return

        faq_pairs = [(question, answer) for _, question, answer in matches]
        try:
            answer = await sync_to_async(generate_answer)(message, faq_pairs)
        except LLMError as exc:
            await self._send_error(str(exc))
            return

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
