"""Helpers for running code across tenants (management commands, Celery, scripts)."""

from __future__ import annotations

from collections.abc import Callable, Iterator

from django_tenants.utils import get_public_schema_name, get_tenant_model, tenant_context


def iter_tenants(*, include_inactive: bool = False) -> Iterator:
    """Yield every real tenant (never the ``public`` pseudo-tenant)."""
    qs = get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
    if not include_inactive:
        qs = qs.filter(is_active=True)
    yield from qs.order_by("pk").iterator()


def for_each_tenant[T](func: Callable[..., T], *args, **kwargs) -> dict[str, T]:
    """Call ``func`` once inside every active tenant's schema.

    Returns ``{schema_name: result}``. Each call runs with the database
    connection switched to that tenant, so ordinary ORM code "just works".
    """
    results: dict[str, T] = {}
    for tenant in iter_tenants():
        with tenant_context(tenant):
            results[tenant.schema_name] = func(*args, **kwargs)
    return results
