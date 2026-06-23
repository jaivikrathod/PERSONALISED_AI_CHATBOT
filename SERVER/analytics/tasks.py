"""Scheduled analytics tasks.

Register `aggregate_all_companies_metrics` with Celery beat to run nightly.
"""

from celery import shared_task

from .services import compute_daily_metrics


@shared_task
def aggregate_company_metrics(company_id: int):
    compute_daily_metrics(company_id)


@shared_task
def aggregate_all_companies_metrics():
    from companies.models import Company

    for company_id in Company.objects.values_list("id", flat=True):
        aggregate_company_metrics.delay(company_id)
