"""WebSocket consumer that powers the chatbot.

Flow for every message a client sends:
  1. Embed the incoming question with the same provider used for the stored Q&A.
  2. Cosine-compare it against the company's vectorized questions.
  3. Return the single best-matching *question* (the top of the top-3).

Nothing is stored — this is a read-only similarity lookup for now. RAG,
fine-tuned answers and live-agent hand-off come later.
"""

import json
import math

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from vector_question.services import generate_embedding
from .models import Question

# How many nearest questions to rank before picking the top one.
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
                        "question": None,
                        "message": "No matching question found.",
                    }
                )
            )
            return

        # Show only the top-most question/answer, per the current requirement.
        score, question, answer = matches[0]
        await self.send(
            json.dumps(
                {
                    "type": "answer",
                    "question": question,
                    "answer": answer,
                    "score": round(score, 4),
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
