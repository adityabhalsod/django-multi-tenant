"""Celery tasks are tenant-aware thanks to tenant-schemas-celery.

When a task is queued from inside a tenant (a request, or ``tenant_context``)
the schema name travels in the message headers and the worker switches to
that schema before running the task. Tasks queued from the public schema run
in the public schema.
"""

import logging

from celery import shared_task
from django.db import connection

from apps.core.tenancy import for_each_tenant

from .models import Project

logger = logging.getLogger(__name__)


@shared_task
def project_report() -> dict:
    data = {
        "schema": connection.schema_name,
        "total": Project.objects.count(),
        "archived": Project.objects.filter(is_archived=True).count(),
    }
    logger.info("Project report: %s", data)
    return data


@shared_task
def project_report_all_tenants() -> dict:
    """Fan-out example: run the same logic inside every active tenant."""
    return for_each_tenant(lambda: Project.objects.count())
