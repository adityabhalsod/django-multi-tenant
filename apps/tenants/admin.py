from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from django_tenants.utils import get_public_schema_name

from apps.core.admin import PublicSchemaOnlyAdminMixin

from .models import Domain, Tenant


class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1


@admin.register(Tenant)
class TenantAdmin(PublicSchemaOnlyAdminMixin, TenantAdminMixin, admin.ModelAdmin):
    list_display = ("name", "schema_name", "is_active", "primary_domain", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "schema_name", "domains__domain")
    inlines = (DomainInline,)

    @admin.display(description="Primary domain")
    def primary_domain(self, obj):
        domain = obj.get_primary_domain()
        return domain.domain if domain else "-"

    def has_delete_permission(self, request, obj=None):
        # The public tenant must never be deleted from the admin.
        if obj is not None and obj.schema_name == get_public_schema_name():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Domain)
class DomainAdmin(PublicSchemaOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    search_fields = ("domain", "tenant__name")
