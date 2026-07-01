"""Vectorization business logic and provider abstraction.

This module is the ONLY place that knows how embeddings are generated and where
vectors are stored. The API layer (views) never talks to a provider directly --
it only calls `vectorize_company()`. That keeps the API contract stable while
the underlying provider changes.

To swap in a real provider later (OpenAI, Gemini, Ollama for embeddings;
ChromaDB, Pinecone, Qdrant, pgvector, Weaviate for storage) you only:
  1. Implement the `EmbeddingProvider` / `VectorStore` interfaces below.
  2. Point `get_embedding_provider()` / `get_vector_store()` at your class
     (e.g. via Django settings). Nothing in views/urls/serializers changes.

The same `vectorize_company()` entry point can also be wrapped by a Celery task
later (RabbitMQ/Redis broker) for async processing -- again, no API change.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class CompanyNotFound(Exception):
    """Raised when vectorization is requested for a non-existent company."""


class EmbeddingError(Exception):
    """Raised when an embedding cannot be generated for a piece of text."""


# ---------------------------------------------------------------------------
# Provider interfaces (the abstraction seam)
# ---------------------------------------------------------------------------
class EmbeddingProvider(ABC):
    """Turns text into a vector embedding.

    Implement this for OpenAI / Gemini / Ollama / sentence-transformers, etc.
    """

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return the embedding vector for `text`."""
        raise NotImplementedError


class VectorStore(ABC):
    """Persists / deletes embeddings in a vector database.

    Implement this for ChromaDB / Pinecone / Qdrant / pgvector / Weaviate.
    """

    @abstractmethod
    def save(self, embedding: list[float], metadata: dict[str, Any]) -> str:
        """Store `embedding` with `metadata`; return the vector's unique id."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, vector_id: str) -> bool:
        """Delete the vector identified by `vector_id`. Return success flag."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Mock implementations (default, used until a real provider is configured)
# ---------------------------------------------------------------------------
class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic fake embedding so the pipeline is testable end-to-end."""

    DIMENSIONS = 8

    def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text.")
        # A cheap deterministic vector derived from the text length/bytes.
        # Replace with a real model call, e.g.:
        #   return openai.embeddings.create(model=..., input=text).data[0].embedding
        seed = sum(bytes(text, "utf-8"))
        return [round(((seed + i) % 100) / 100, 4) for i in range(self.DIMENSIONS)]


class MockVectorStore(VectorStore):
    """In-memory fake vector store that hands out predictable ids."""

    def save(self, embedding: list[float], metadata: dict[str, Any]) -> str:
        # Real impl would upsert into Pinecone/Qdrant/pgvector and return its id.
        qid = metadata.get("question_id", "x")
        company_id = metadata.get("company_id", "x")
        vector_id = f"vec_{company_id}_{qid}"
        logger.debug("MockVectorStore.save -> %s (dims=%d)", vector_id, len(embedding))
        return vector_id

    def delete(self, vector_id: str) -> bool:
        # Real impl would delete by id from the vector DB.
        logger.debug("MockVectorStore.delete -> %s", vector_id)
        return True


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------
# Swap these factories (or read from django.conf.settings) to change providers
# without touching the API layer. Kept as functions so they can be overridden
# in tests and later wired to settings, e.g.:
#     provider_path = getattr(settings, "EMBEDDING_PROVIDER", None)
#     return import_string(provider_path)() if provider_path else MockEmbeddingProvider()
def get_embedding_provider() -> EmbeddingProvider:
    return MockEmbeddingProvider()


def get_vector_store() -> VectorStore:
    return MockVectorStore()


# ---------------------------------------------------------------------------
# Placeholder functional API (stable names the rest of the code depends on)
# ---------------------------------------------------------------------------
def generate_embedding(text: str) -> list[float]:
    """Generate an embedding for `text` using the configured provider."""
    return get_embedding_provider().embed(text)


def save_to_vector_db(embedding: list[float], metadata: dict[str, Any] | None = None) -> str:
    """Persist `embedding` (+ optional metadata) and return its vector id."""
    return get_vector_store().save(embedding, metadata or {})


def delete_vector(vector_id: str) -> bool:
    """Delete a vector by id. Never raises -- deletion is best-effort cleanup."""
    if not vector_id:
        return False
    try:
        return get_vector_store().delete(vector_id)
    except Exception:  # noqa: BLE001 - cleanup must not break the caller
        logger.exception("Failed to delete vector %s", vector_id)
        return False


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _build_text(question: str, answer: str) -> str:
    """Format a Q/A pair into the text that gets embedded."""
    return f"Question:\n{question}\n\nAnswer:\n{answer}"


def vectorize_company(company_id: int) -> dict[str, Any]:
    """Vectorize all un-vectorized questions for a company.

    Workflow (Parts 4 & 5):
      1. Verify the company exists (raise CompanyNotFound otherwise).
      2. Create a VectorJob record (status=pending).
      3. Fetch questions with company_id=<id>, is_vectorized=False, not archived.
      4. If none -> return early ("all already vectorized").
      5. Otherwise loop, embedding + storing each question, updating progress.
         A failure on one question is recorded and processing continues.
      6. Finalize the job (completed/failed) and return a summary dict.

    Returns a dict consumed by the view; it does NOT build HTTP responses so it
    stays framework-agnostic and reusable from a Celery task or CLI command.
    """
    # Imported here to avoid circular imports at module load time.
    from company.models import Company
    from questions.models import Question
    from .models import VectorJob

    # --- 1. Verify company exists --------------------------------------------
    if not Company.objects.filter(pk=company_id).exists():
        raise CompanyNotFound(f"Company {company_id} does not exist.")

    # --- 3. Find work (before creating a job for the "nothing to do" case) ---
    pending_qs = Question.objects.filter(
        company_id=company_id,
        is_vectorized=False,
        is_archived=False,
    )
    total = pending_qs.count()

    # --- 4. Nothing to vectorize ---------------------------------------------
    if total == 0:
        return {
            "all_vectorized": True,
            "message": "All questions are already vectorized.",
            "total_questions": 0,
            "processed_questions": 0,
            "failed_questions": 0,
        }

    # --- 2. Create the job ----------------------------------------------------
    job = VectorJob.objects.create(
        company_id=company_id,
        status=VectorJob.Status.PROCESSING,
        total_questions=total,
        started_at=timezone.now(),
    )

    processed = 0
    failed = 0
    errors: list[str] = []

    # --- 5. Process each question --------------------------------------------
    # Iterate over ids so a long run doesn't hold a single big transaction; each
    # question is saved in its own atomic block so partial progress is durable.
    for question in pending_qs.iterator():
        try:
            text = _build_text(question.question, question.answer)
            embedding = generate_embedding(text)
            vector_id = save_to_vector_db(
                embedding,
                metadata={
                    "question_id": question.id,
                    "company_id": company_id,
                },
            )

            with transaction.atomic():
                question.vector_id = vector_id
                question.is_vectorized = True
                # update_fields keeps the save narrow and avoids the content-change
                # reset logic in Question.save() from firing.
                question.save(update_fields=["vector_id", "is_vectorized", "updated_at"])

            processed += 1
        except Exception as exc:  # noqa: BLE001 - one failure must not stop the job
            failed += 1
            errors.append(f"Question {question.id}: {exc}")
            logger.exception("Vectorization failed for question %s", question.id)

        # Persist incremental progress so external observers see live counts.
        VectorJob.objects.filter(pk=job.id).update(
            processed_questions=processed,
            failed_questions=failed,
        )

    # --- 6. Finalize ----------------------------------------------------------
    job.processed_questions = processed
    job.failed_questions = failed
    job.completed_at = timezone.now()
    job.error_message = "\n".join(errors) if errors else None
    # "completed" even with some failures (job ran to the end); use "failed"
    # only if every single question errored out.
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
