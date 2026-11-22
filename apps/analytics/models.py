"""Example of a *non tenant-aware* app that can live in its own database.

With ``DATABASE_EXTRA_URLS=analytics=postgres://...`` and
``DATABASE_APP_ROUTES=analytics=analytics`` every query of this app goes to
the ``analytics`` database. Without them it falls back to the ``public``
schema of the primary database (it is in ``SHARED_APPS``).

Because this data is global, rows carry the tenant's schema name explicitly.
"""

from django.db import models


class Event(models.Model):
    tenant_schema = models.CharField(max_length=63, db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.tenant_schema}:{self.name}"
