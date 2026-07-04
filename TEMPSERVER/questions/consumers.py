"""WebSocket consumer that powers the chatbot.

Flow for every message a client sends:
  1. Embed the incoming question with the same provider used for the stored Q&A.
  2. Cosine-compare it against the company's vectorized questions.
  3. Take the top-K matches. If the best one clears the confidence threshold,
     hand those FAQ pairs to Gemini and return its grounded answer.

Nothing is stored — this is a read-only retrieval + LLM lookup for now.
"""

import json
import math

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from vector_question.services import LLMError, generate_answer, generate_embedding
from .models import Question

# How many nearest questions to rank and feed to the LLM as context.
TOP_K = 3


def _cosine_similarity(a, b):
    """Cosine similarity of two equal-length vectors; 0.0 when undefined."""
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
        # No group membership or state to clean up yet.
        pass

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

        matches = await self._top_matches(message, company_id)

        if not matches:
            await self.send(
                json.dumps(
                    {
                        "type": "answer",
                        "answer": "No matching question found.",
                        "sources": [],
                    }
                )
            )
            return

        best_score = matches[0][0]

        # Low confidence: don't call the LLM, just say we couldn't find it.
        if best_score < settings.CHAT_CONFIDENCE_THRESHOLD:
            await self.send(
                json.dumps(
                    {
                        "type": "answer",
                        "answer": "Sorry, I couldn't find a reliable answer in the FAQ database.",
                        "score": round(best_score, 4),
                        "sources": [],
                    }
                )
            )
            return

        # Feed the top-K (question, answer) pairs to Gemini as grounding context.
        faq_pairs = [(question, answer) for _, question, answer in matches]
        try:
            answer = await sync_to_async(generate_answer)(message, faq_pairs)
        except LLMError as exc:
            await self._send_error(str(exc))
            return

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
                }
            )
        )

    async def _send_error(self, error):
        await self.send(json.dumps({"type": "error", "error": error}))

    @database_sync_to_async
    def _top_matches(self, message, company_id):
        """Embed `message` and return the TOP_K (score, question, answer) tuples, best first."""
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
