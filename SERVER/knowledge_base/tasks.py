"""Celery tasks for asynchronous embedding generation."""

import logging

from celery import shared_task

from .models import QuestionAnswer
from .services import EmbeddingService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_qa_embedding(self, qa_id: int):
    """Generate + store the embedding for a single QA pair."""
    try:
        qa = QuestionAnswer.objects.select_related("knowledge_base").get(pk=qa_id)
    except QuestionAnswer.DoesNotExist:
        logger.warning("QA %s no longer exists; skipping embedding.", qa_id)
        return

    service = EmbeddingService()
    try:
        service.embed_qa(qa)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Embedding failed for QA %s", qa_id)
        service.mark_failed(qa)
        raise self.retry(exc=exc)


@shared_task
def generate_embeddings_for_kb(knowledge_base_id: int):
    """Backfill embeddings for every pending QA in a knowledge base."""
    pending = QuestionAnswer.objects.filter(
        knowledge_base_id=knowledge_base_id,
        embedding_status=QuestionAnswer.EMBEDDING_PENDING,
    ).values_list("id", flat=True)
    for qa_id in pending:
        generate_qa_embedding.delay(qa_id)
