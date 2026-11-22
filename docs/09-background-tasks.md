# 9. Background tasks with Celery

## 9.1 How tenant context reaches the worker

`config/celery.py` uses `tenant_schemas_celery.app.CeleryApp`:

1. When a task is **sent**, the current schema name is added to its headers.
2. Before the worker **runs** it, the worker switches the connection (and replicas) to that
   schema; afterwards it switches back.

So this "just works":

```python
# apps/projects/views.py, inside a request to acme.localhost
project_report.delay()  # runs in the "acme" schema on the worker
```

Tasks queued outside any tenant run in `public`.

## 9.2 Write a task

```python
from celery import shared_task


@shared_task
def send_invoice(invoice_id: int) -> None:
    invoice = Invoice.objects.get(pk=invoice_id)  # the right tenant's table
    ...
```

Pass IDs, not model instances. Make tasks idempotent (`CELERY_TASK_ACKS_LATE=True` means a
task may run again after a worker crash).

## 9.3 Queue from outside a request

```python
from django_tenants.utils import tenant_context

with tenant_context(tenant):
    send_invoice.delay(invoice.pk)
```

## 9.4 Periodic tasks (beat)

`beat` runs with `TenantAwarePersistentScheduler`. In `CELERY_BEAT_SCHEDULE`:

```python
CELERY_BEAT_SCHEDULE = {
    # No "tenant_schemas": runs once for EVERY tenant
    "nightly-project-report": {"task": "apps.projects.tasks.project_report", "schedule": 86400},
    # Only in the public schema (platform-wide jobs)
    "cleanup": {"task": "apps.core.tasks.cleanup", "schedule": 3600, "tenant_schemas": ["public"]},
}
```

Alternatively, schedule one public task that fans out with `for_each_tenant()`
(see `apps.projects.tasks.project_report_all_tenants`).

## 9.5 Run workers

```bash
docker compose up -d worker beat                       # Docker
uv run celery -A config worker -l info                 # local
uv run celery -A config beat -l info \
  --scheduler tenant_schemas_celery.scheduler.TenantAwarePersistentScheduler
```

Run exactly **one** beat process per environment.

In tests, `CELERY_TASK_ALWAYS_EAGER=True` runs tasks inline.

Next: [10. Cache, files and email](10-cache-files-email.md)
