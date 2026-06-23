"""Knowledge-base service layer.

Encapsulates all business logic so views/tasks/consumers stay thin:
  * EmbeddingService   - generate & persist embeddings for QA pairs
  * SearchService      - semantic (pgvector) + keyword retrieval, tenant-scoped
  * BulkUploadService  - parse CSV/Excel into QA rows
"""

from __future__ import annotations

import io
import logging

from django.db import transaction
from pgvector.django import CosineDistance

from core.ai import get_embedding_provider

from .models import KnowledgeBase, QuestionAnswer, QuestionEmbedding

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates and stores embeddings for QuestionAnswer rows."""

    def __init__(self, provider=None):
        self.provider = provider or get_embedding_provider()

    @transaction.atomic
    def embed_qa(self, qa: QuestionAnswer) -> QuestionEmbedding:
        """Generate the embedding for one QA and upsert it. Idempotent."""
        vector = self.provider.embed_query(qa.question)
        embedding, _ = QuestionEmbedding.objects.update_or_create(
            qa=qa,
            defaults={
                "company_id": qa.knowledge_base.company_id,
                "embedding": vector,
                "model_name": getattr(self.provider, "model", ""),
            },
        )
        QuestionAnswer.objects.filter(pk=qa.pk).update(
            embedding_status=QuestionAnswer.EMBEDDING_READY
        )
        return embedding

    def mark_failed(self, qa: QuestionAnswer):
        QuestionAnswer.objects.filter(pk=qa.pk).update(
            embedding_status=QuestionAnswer.EMBEDDING_FAILED
        )


class SearchService:
    """Tenant-scoped retrieval over a company's knowledge base."""

    def __init__(self, company_id: int, provider=None):
        self.company_id = company_id
        self.provider = provider or get_embedding_provider()

    def semantic_search(self, query: str, top_k: int = 3) -> list[dict]:
        """Return the top_k most similar QA pairs with a similarity score.

        Score = 1 - cosine_distance, i.e. 1.0 is identical, 0.0 is orthogonal.
        Only ACTIVE, non-deleted QA pairs in this company are considered.
        """
        query_vec = self.provider.embed_query(query)

        rows = (
            QuestionEmbedding.objects.filter(
                company_id=self.company_id,
                qa__is_deleted=False,
                qa__knowledge_base__is_active=True,
                qa__knowledge_base__is_deleted=False,
            )
            .annotate(distance=CosineDistance("embedding", query_vec))
            .select_related("qa", "qa__knowledge_base")
            .order_by("distance")[:top_k]
        )

        results = []
        for row in rows:
            results.append(
                {
                    "qa_id": row.qa_id,
                    "qa_uuid": str(row.qa.uuid),
                    "question": row.qa.question,
                    "answer": row.qa.answer,
                    "knowledge_base_id": row.qa.knowledge_base_id,
                    "distance": float(row.distance),
                    "score": round(1.0 - float(row.distance), 4),
                }
            )
        return results

    def keyword_search(self, query: str, top_k: int = 10) -> list[QuestionAnswer]:
        return list(
            QuestionAnswer.objects.filter(
                knowledge_base__company_id=self.company_id
            ).filter(question__icontains=query)[:top_k]
        )


class BulkUploadService:
    """Parses uploaded CSV / Excel files into QuestionAnswer rows.

    Expected columns (case-insensitive): "question", "answer".
    """

    REQUIRED_COLUMNS = {"question", "answer"}

    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base

    def _read_dataframe(self, file_obj, filename: str):
        import pandas as pd

        name = filename.lower()
        data = file_obj.read()
        if name.endswith(".csv"):
            return pd.read_csv(io.BytesIO(data))
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(data))
        raise ValueError("Unsupported file type. Upload a .csv, .xlsx or .xls file.")

    @transaction.atomic
    def ingest(self, file_obj, filename: str) -> list[QuestionAnswer]:
        df = self._read_dataframe(file_obj, filename)
        df.columns = [str(c).strip().lower() for c in df.columns]

        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Missing required column(s): {', '.join(sorted(missing))}")

        created: list[QuestionAnswer] = []
        for _, raw in df.iterrows():
            question = str(raw["question"]).strip()
            answer = str(raw["answer"]).strip()
            if not question or question.lower() == "nan":
                continue
            created.append(
                QuestionAnswer(
                    knowledge_base=self.knowledge_base,
                    question=question,
                    answer=answer,
                )
            )
        QuestionAnswer.objects.bulk_create(created)
        return created
