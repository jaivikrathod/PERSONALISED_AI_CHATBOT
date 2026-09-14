import time

from django.core.management.base import BaseCommand

from knowledge.jobs import claim_next, run_job


class Command(BaseCommand):
    help = "Process queued knowledge ingestion jobs (use with INGESTION_MODE=worker)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Drain the queue, then exit.")
        parser.add_argument("--poll", type=float, default=2.0, help="Seconds between polls.")

    def handle(self, *args, once=False, poll=2.0, **options):
        while True:
            job_id = claim_next()
            if job_id is not None:
                self.stdout.write(f"Running ingestion job #{job_id}")
                run_job(job_id)
                continue
            if once:
                return
            time.sleep(poll)
