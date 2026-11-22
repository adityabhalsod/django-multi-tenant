"""Tenant provisioning. Keep business logic here, not in views or commands."""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from django_tenants.utils import get_public_schema_name, schema_context

from .models import Domain, Tenant

# Lower-case letters, digits and underscores; must not start with a digit.
# Stricter than PostgreSQL itself so names never need quoting.
SCHEMA_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
RESERVED_SCHEMAS = frozenset({"public", "information_schema", "pg_catalog", "pg_toast"})


class ProvisioningError(ValueError):
    pass


@dataclass(frozen=True)
class TenantAdmin:
    username: str
    email: str
    password: str


def normalise_schema_name(value: str) -> str:
    """``"Acme Corp!"`` -> ``"acme_corp"``. Schema names are PostgreSQL identifiers."""
    schema = re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")
    if schema and schema[0].isdigit():
        schema = f"t_{schema}"
    return schema[:63]


def validate_schema_name(schema_name: str) -> None:
    if schema_name in RESERVED_SCHEMAS or schema_name.startswith("pg_"):
        raise ProvisioningError(f"{schema_name!r} is a reserved schema name")
    if not SCHEMA_NAME_RE.match(schema_name):
        raise ProvisioningError(f"{schema_name!r} is not a valid PostgreSQL schema name")


def ensure_public_tenant(domain: str, name: str = "Public") -> Tenant:
    """Create (idempotently) the ``public`` tenant and its domain.

    django-tenants needs a Tenant row for the public schema so that requests to
    the main site (landing page, platform admin) resolve to it.
    """
    with schema_context(get_public_schema_name()):
        tenant, _ = Tenant.objects.get_or_create(
            schema_name=get_public_schema_name(), defaults={"name": name}
        )
        Domain.objects.get_or_create(
            domain=domain.lower(), defaults={"tenant": tenant, "is_primary": True}
        )
    return tenant


def provision_tenant(
    *,
    name: str,
    domain: str,
    schema_name: str | None = None,
    admin: TenantAdmin | None = None,
) -> Tenant:
    """Create a tenant, its schema, its primary domain and (optionally) an admin user.

    Saving the tenant creates the schema and runs every ``TENANT_APPS``
    migration inside it, which can take a few seconds on large projects.
    """
    schema_name = schema_name or normalise_schema_name(name)
    validate_schema_name(schema_name)
    domain = domain.lower().strip()

    with schema_context(get_public_schema_name()):
        if Tenant.objects.filter(schema_name=schema_name).exists():
            raise ProvisioningError(f"Schema {schema_name!r} is already taken")
        if Domain.objects.filter(domain=domain).exists():
            raise ProvisioningError(f"Domain {domain!r} is already taken")

        # Schema creation is DDL: it is not wrapped in the same transaction as the
        # domain on purpose, because a migration failure must not leave a domain
        # pointing at a half-built schema. If the domain insert fails we drop the
        # brand-new schema again.
        tenant = Tenant(schema_name=schema_name, name=name)
        tenant.save()
        try:
            with transaction.atomic():
                Domain.objects.create(domain=domain, tenant=tenant, is_primary=True)
        except Exception:
            tenant.delete(force_drop=True)
            raise

    if admin is not None:
        with schema_context(tenant.schema_name):
            get_user_model().objects.create_superuser(
                username=admin.username, email=admin.email, password=admin.password
            )
    return tenant
