"""Tenant-aware Celery application.

``tenant_schemas_celery.app.CeleryApp`` stores the current schema name in the
headers of every task sent, and the worker switches to that schema before the
task runs (and back afterwards).
"""

import os

from tenant_schemas_celery.app import CeleryApp

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = CeleryApp("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
