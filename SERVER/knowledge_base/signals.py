"""Trigger embedding generation whenever a QA pair is created or its question
text changes. Runs the work on Celery so the request returns immediately.

Enqueueing is best-effort: if the broker (Redis) is unavailable, the FAQ is
simply left PENDING and the dashboard's "Convert to Vector DB" button embeds it
synchronously instead. A missing worker must never break FAQ creation.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import QuestionAnswer
from .tasks import generate_qa_embedding

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=QuestionAnswer)
def flag_question_change(sender, instance, **kwargs):
    """Mark the embedding stale if the question text was edited."""
    if not instance.pk:
        return
    try:
        previous = QuestionAnswer.objects.get(pk=instance.pk)
    except QuestionAnswer.DoesNotExist:
        return
    if previous.question != instance.question:
        instance.embedding_status = QuestionAnswer.EMBEDDING_PENDING


def _safe_enqueue(qa_pk):
    """Fire the Celery task, swallowing broker-connection errors."""
    try:
        generate_qa_embedding.delay(qa_pk)
    except Exception:  # noqa: BLE001 - broker down: leave PENDING for the button
        logger.warning(
            "Could not enqueue embedding for QA %s (broker unavailable); "
            "it will stay PENDING until 'Convert to Vector DB' is run.",
            qa_pk,
        )


@receiver(post_save, sender=QuestionAnswer)
def enqueue_embedding(sender, instance, created, **kwargs):
    # Button-driven by default: skip auto-enqueue unless a Celery worker is in
    # use (EMBED_QA_ON_SAVE=True). The FAQ stays PENDING for "Convert to Vector
    # DB". This keeps FAQ creation instant and independent of Redis/Celery.
    from django.conf import settings

    if not settings.EMBED_QA_ON_SAVE:
        return
    if instance.is_deleted:
        return
    if instance.embedding_status == QuestionAnswer.EMBEDDING_PENDING:
        # transaction.on_commit ensures the row is visible to the worker.
        from django.db import transaction

        transaction.on_commit(lambda: _safe_enqueue(instance.pk))
