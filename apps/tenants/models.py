"""Tenant and Domain models. These live in the shared ``public`` schema."""

from __future__ import annotations

from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class Tenant(TenantMixin):
    """One customer/workspace. Owns a PostgreSQL schema named ``schema_name``."""

    name = models.CharField(max_length=100)
    is_active = models.BooleanField(
        default=True, help_text="Inactive tenants receive HTTP 403 on every request."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Create the schema (and run tenant migrations) when the tenant is saved.
    auto_create_schema = True
    # Never drop a schema implicitly: deleting the row keeps the data.
    # Use `manage.py delete_tenant` when you really mean it.
    auto_drop_schema = False

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name} ({self.schema_name})"


class Domain(DomainMixin):
    """A hostname (e.g. ``acme.example.com``) that routes to a tenant."""

    class Meta:
        ordering = ("domain",)

    def __str__(self) -> str:
        return self.domain
