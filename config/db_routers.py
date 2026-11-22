"""Database routing for a schema-per-tenant project with optional extra DBs.

``MultiDatabaseRouter`` runs *before* ``django_tenants.routers.TenantSyncRouter``
and handles three concerns:

1. **Dedicated databases.** Apps listed in ``DATABASE_APP_ROUTES`` read, write
   and migrate only on their own alias (e.g. ``analytics`` -> ``analytics``).
2. **Read replicas.** Reads of tenant-aware models go to a replica, unless the
   current request/task is pinned to the primary (see ``apps.core.db``).
   The replica connection is switched to the *same tenant schema* as the
   primary connection just before it is used, so tenant isolation holds on
   replicas too.
3. **Migrations.** Replicas never migrate, extra databases only migrate their
   own apps, and everything else is left to ``TenantSyncRouter`` which decides
   between ``SHARED_APPS`` (public schema) and ``TENANT_APPS`` (tenant schemas).
"""

from __future__ import annotations

import random

from django.conf import settings
from django.db import connections

from apps.core.db import is_primary_pinned

PRIMARY = "default"


class MultiDatabaseRouter:
    # Tenant metadata must always come from the primary: a lagging replica
    # could otherwise resolve a domain to a tenant that was just deleted.
    PRIMARY_ONLY_APPS = frozenset({"tenants", "sessions", "authtoken", "contenttypes", "auth"})

    @property
    def app_routes(self) -> dict[str, str]:
        return getattr(settings, "DATABASE_APP_ROUTES", {})

    @property
    def replicas(self) -> list[str]:
        return getattr(settings, "DATABASE_REPLICAS", [])

    # -- reads / writes -------------------------------------------------
    def db_for_read(self, model, **hints):
        label = model._meta.app_label
        if label in self.app_routes:
            return self.app_routes[label]
        if not self.replicas or is_primary_pinned() or label in self.PRIMARY_ONLY_APPS:
            return PRIMARY
        alias = random.choice(self.replicas)  # noqa: S311 - not security sensitive
        self._sync_tenant(alias)
        return alias

    def db_for_write(self, model, **hints):
        return self.app_routes.get(model._meta.app_label, PRIMARY)

    # -- relations ------------------------------------------------------
    def allow_relation(self, obj1, obj2, **hints):
        group = {PRIMARY, *self.replicas}
        db1, db2 = obj1._state.db, obj2._state.db
        if db1 in group and db2 in group:
            return True
        return db1 == db2

    # -- migrations -----------------------------------------------------
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db in self.replicas:
            return False
        if app_label in self.app_routes:
            return db == self.app_routes[app_label]
        if db != PRIMARY:
            # An extra database only ever receives the apps routed to it.
            return False
        return None  # let TenantSyncRouter decide shared vs tenant apps

    # -- helpers --------------------------------------------------------
    @staticmethod
    def _sync_tenant(alias: str) -> None:
        """Point the replica connection at the primary's current tenant/schema."""
        primary, replica = connections[PRIMARY], connections[alias]
        if replica.tenant is primary.tenant and replica.schema_name == primary.schema_name:
            return
        replica.set_tenant(primary.tenant, include_public=primary.include_public_schema)
