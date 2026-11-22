from django.contrib import admin

from apps.core.admin import PublicSchemaOnlyAdminMixin

from .models import Event


@admin.register(Event)
class EventAdmin(PublicSchemaOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "tenant_schema", "created_at")
    list_filter = ("name", "tenant_schema")
    readonly_fields = ("tenant_schema", "name", "payload", "created_at")
