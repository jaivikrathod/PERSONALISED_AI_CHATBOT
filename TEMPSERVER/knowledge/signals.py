from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from questions.models import Question
from registry.models import Chatbot

from .faq import backfill_chatbot, remove_question, sync_question


@receiver(post_save, sender=Question)
def question_saved(sender, instance, raw=False, **kwargs):
    if not raw:
        sync_question(instance)


@receiver(post_delete, sender=Question)
def question_deleted(sender, instance, **kwargs):
    remove_question(instance)


@receiver(post_save, sender=Chatbot)
def chatbot_created(sender, instance, created=False, raw=False, **kwargs):
    if created and not raw:
        backfill_chatbot(instance)
