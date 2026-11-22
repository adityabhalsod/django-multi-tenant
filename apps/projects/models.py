"""Example tenant-scoped app. Copy this pattern for your own domain models.

Nothing here mentions tenants: because ``projects`` is in ``TENANT_APPS`` its
table exists in every tenant schema, and the request's ``search_path`` makes
the ORM read and write only the current tenant's rows. No ``tenant_id``
column, no filtering to forget.
"""

from django.conf import settings
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="projects"
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.name
