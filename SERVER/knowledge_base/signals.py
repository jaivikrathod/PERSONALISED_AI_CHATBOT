"""Trigger embedding generation whenever a QA pair is created or its question
text changes. Runs the work on Celery so the request returns immediately.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import QuestionAnswer
from .tasks import generate_qa_embedding


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


@receiver(post_save, sender=QuestionAnswer)
def enqueue_embedding(sender, instance, created, **kwargs):
    if instance.is_deleted:
        return
    if instance.embedding_status == QuestionAnswer.EMBEDDING_PENDING:
        # transaction.on_commit ensures the row is visible to the worker.
        from django.db import transaction

        transaction.on_commit(lambda: generate_qa_embedding.delay(instance.pk))
