from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class CompanyNotFound(Exception):
    pass


class EmbeddingError(Exception):
    pass


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class VectorStore(ABC):
    @abstractmethod
    def save(self, embedding: list[float], metadata: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def delete(self, vector_id: str) -> bool:
        raise NotImplementedError


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Real semantic embeddings via sentence-transformers (all-MiniLM-L6-v2).

    The model is loaded once per process and cached on the class — loading is
    expensive (a few seconds) but encoding after that is fast on CPU.
    """

    MODEL_NAME = "all-MiniLM-L6-v2"
    _model = None

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            from sentence_transformers import SentenceTransformer

            cls._model = SentenceTransformer(cls.MODEL_NAME)
        return cls._model

    def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text.")
        vector = self._get_model().encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vector.tolist()


class MockVectorStore(VectorStore):
    def save(self, embedding: list[float], metadata: dict[str, Any]) -> str:
        qid = metadata.get("question_id", "x")
        company_id = metadata.get("company_id", "x")
        vector_id = f"vec_{company_id}_{qid}"
        logger.debug("MockVectorStore.save -> %s (dims=%d)", vector_id, len(embedding))
        return vector_id

    def delete(self, vector_id: str) -> bool:
        logger.debug("MockVectorStore.delete -> %s", vector_id)
        return True


def get_embedding_provider() -> EmbeddingProvider:
    return SentenceTransformerEmbeddingProvider()


def get_vector_store() -> VectorStore:
    return MockVectorStore()


def generate_embedding(text: str) -> list[float]:
    return get_embedding_provider().embed(text)


def save_to_vector_db(embedding: list[float], metadata: dict[str, Any] | None = None) -> str:
    return get_vector_store().save(embedding, metadata or {})


def delete_vector(vector_id: str) -> bool:
    if not vector_id:
        return False
    try:
        return get_vector_store().delete(vector_id)
    except Exception:
        logger.exception("Failed to delete vector %s", vector_id)
        return False


def _build_text(question: str, answer: str) -> str:
    return f"Question:\n{question}\n\nAnswer:\n{answer}"


def vectorize_company(company_id: int) -> dict[str, Any]:
    from company.models import Company
    from questions.models import Question
    from .models import VectorJob

    if not Company.objects.filter(pk=company_id).exists():
        raise CompanyNotFound(f"Company {company_id} does not exist.")

    pending_qs = Question.objects.filter(
        company_id=company_id,
        is_vectorized=False,
        is_archived=False,
    )
    total = pending_qs.count()

    if total == 0:
        return {
            "all_vectorized": True,
            "message": "All questions are already vectorized.",
            "total_questions": 0,
            "processed_questions": 0,
            "failed_questions": 0,
        }

    job = VectorJob.objects.create(
        company_id=company_id,
        status=VectorJob.Status.PROCESSING,
        total_questions=total,
        started_at=timezone.now(),
    )

    processed = 0
    failed = 0
    errors: list[str] = []

    for question in pending_qs.iterator():
        try:
            text = _build_text(question.question, question.answer)
            embedding = generate_embedding(text)

            with transaction.atomic():
                question.embedding = embedding
                question.is_vectorized = True
                question.save(update_fields=["embedding", "is_vectorized", "updated_at"])

            processed += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Question {question.id}: {exc}")
            logger.exception("Vectorization failed for question %s", question.id)

        VectorJob.objects.filter(pk=job.id).update(
            processed_questions=processed,
            failed_questions=failed,
        )

    job.processed_questions = processed
    job.failed_questions = failed
    job.completed_at = timezone.now()
    job.error_message = "\n".join(errors) if errors else None
    job.status = (
        VectorJob.Status.FAILED
        if processed == 0 and failed > 0
        else VectorJob.Status.COMPLETED
    )
    job.save(
        update_fields=[
            "processed_questions",
            "failed_questions",
            "completed_at",
            "error_message",
            "status",
            "updated_at",
        ]
    )

    return {
        "all_vectorized": False,
        "message": "Vectorization completed successfully.",
        "job_id": job.id,
        "total_questions": total,
        "processed_questions": processed,
        "failed_questions": failed,
    }
