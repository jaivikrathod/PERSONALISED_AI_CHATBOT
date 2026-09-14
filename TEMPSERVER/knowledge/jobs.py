"""A database-backed job queue for ingestion — no new infrastructure.

`INGESTION_MODE` (settings):
- `thread` (default): a daemon thread per job, started after the request's
  transaction commits. Good for development and a single server.
- `worker`: jobs wait for `manage.py run_ingestion_worker`, which claims them
  with `SELECT … FOR UPDATE SKIP LOCKED`, so several workers can run safely.
- `inline`: run immediately in the caller. Tests use this.

Progress is written to the job row as it runs, so the API can poll it.
"""

from __future__ import annotations

import logging
import threading

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from .models import IngestionJob

logger = logging.getLogger(__name__)


def enqueue(job: IngestionJob) -> None:
    mode = getattr(settings, "INGESTION_MODE", "thread")
    if mode == "inline":
        run_job(job.id)
    elif mode == "thread":
        transaction.on_commit(
            lambda: threading.Thread(target=_run_in_thread, args=(job.id,), daemon=True).start()
        )
    # "worker": nothing to do — the worker polls the table.


def _run_in_thread(job_id: int) -> None:
    try:
        run_job(job_id)
    finally:
        connection.close()


def claim_next() -> int | None:
    with transaction.atomic():
        job = (
            IngestionJob.objects.select_for_update(skip_locked=True)
            .filter(status=IngestionJob.Status.QUEUED)
            .order_by("created_at", "id")
            .first()
        )
        if job is None:
            return None
        _mark_running(job)
        return job.id


def run_job(job_id: int) -> None:
    with transaction.atomic():
        job = (
            IngestionJob.objects.select_for_update(skip_locked=True)
            .filter(id=job_id)
            .first()
        )
        if job is None or job.status not in (IngestionJob.Status.QUEUED, IngestionJob.Status.RUNNING):
            return
        if job.status == IngestionJob.Status.QUEUED:
            _mark_running(job)

    from .ingest import HANDLERS

    job = IngestionJob.objects.select_related("source", "document").get(id=job_id)
    try:
        HANDLERS[job.kind](job)
    except Exception as exc:  # a failed job is a status, never a crashed worker
        logger.exception("Ingestion job #%s failed", job_id)
        IngestionJob.objects.filter(id=job_id).update(
            status=IngestionJob.Status.FAILED,
            error=str(exc)[:2000],
            payload=b"",
            finished_at=timezone.now(),
        )
        from .ingest import mark_failed

        mark_failed(job, str(exc))
        return

    IngestionJob.objects.filter(id=job_id).update(
        status=IngestionJob.Status.DONE,
        done_steps=job.total_steps,
        payload=b"",
        finished_at=timezone.now(),
    )


def report(job: IngestionJob, *, done: int | None = None, total: int | None = None, message: str | None = None):
    fields = {}
    if done is not None:
        job.done_steps = fields["done_steps"] = done
    if total is not None:
        job.total_steps = fields["total_steps"] = total
    if message is not None:
        job.message = fields["message"] = message[:255]
    if fields:
        IngestionJob.objects.filter(id=job.id).update(**fields)


def _mark_running(job: IngestionJob) -> None:
    job.status = IngestionJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])
