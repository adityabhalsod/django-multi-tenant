"""One admin site, branded per schema.

The same ``admin.site`` serves the platform admin (public schema) and every
tenant's admin, so its titles are computed per request instead of being set
once at import time.
"""

from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.db import connection
from django_tenants.utils import get_public_schema_name


class TenantAwareAdminSite(admin.AdminSite):
    @staticmethod
    def _title() -> str:
        tenant = getattr(connection, "tenant", None)
        if connection.schema_name == get_public_schema_name():
            return "Platform administration"
        return f"{getattr(tenant, 'name', '') or connection.schema_name} administration"

    @property
    def site_header(self):  # type: ignore[override]
        return self._title()

    @property
    def site_title(self):  # type: ignore[override]
        return self._title()

    @property
    def index_title(self):  # type: ignore[override]
        if connection.schema_name == get_public_schema_name():
            return "Tenants, domains and platform staff"
        return "Workspace administration"


class TenantAdminConfig(AdminConfig):
    """Drop-in for ``django.contrib.admin`` that installs ``TenantAwareAdminSite``."""

    default_site = "apps.core.admin_site.TenantAwareAdminSite"
