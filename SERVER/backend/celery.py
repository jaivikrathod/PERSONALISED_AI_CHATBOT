"""Celery application bootstrap.

Usage:
    celery -A backend worker -l info
    celery -A backend beat -l info
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

app = Celery("backend")

# All CELERY_* keys in Django settings configure the worker.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py modules across installed apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
