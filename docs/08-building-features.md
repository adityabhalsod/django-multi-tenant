# 8. Building features

## 8.1 Add a tenant app, step by step

The `apps/projects` app is the template. To add `invoices`:

1. **Create the app**
   ```bash
   mkdir apps/invoices && uv run python manage.py startapp invoices apps/invoices
   ```
   In `apps/invoices/apps.py` set `name = "apps.invoices"` and `label = "invoices"`.
2. **Register it as a tenant app** in `config/settings/base.py`:
   ```python
   TENANT_APPS = [..., "apps.invoices"]
   ```
3. **Write models normally.** No `tenant` foreign key, no custom manager.
   ```python
   class Invoice(models.Model):
       number = models.CharField(max_length=30, unique=True)  # unique per tenant
       total = models.DecimalField(max_digits=12, decimal_places=2)
   ```
4. **Create and apply migrations**
   ```bash
   uv run python manage.py makemigrations invoices
   uv run python manage.py migrate_schemas      # applies to every tenant
   ```
   New tenants get the table automatically when they are provisioned.
5. **API**: copy `serializers.py`, `views.py`, `urls.py` from `apps/projects`, then add
   `path("api/", include("apps.invoices.urls"))` to `config/urls.py` (the tenant URLconf).
6. **Admin**: a normal `@admin.register(Invoice)` shows up in each tenant's admin.
7. **Tests**: subclass `apps.core.testing.TenantAPITestCase` (see [12. Testing](12-testing.md)).

`unique=True` is per tenant, because each tenant has its own table.

## 8.2 Add a shared (public) app

For data that belongs to the platform (plans, billing, feature flags):

1. Add it to `SHARED_APPS` only.
2. Use `PublicSchemaOnlyAdminMixin` on every `ModelAdmin`:
   ```python
   from apps.core.admin import PublicSchemaOnlyAdminMixin


   @admin.register(Plan)
   class PlanAdmin(PublicSchemaOnlyAdminMixin, admin.ModelAdmin): ...
   ```
   **Why:** the tenant's `search_path` is `"acme", "public"`, so tenant code *can* read
   public tables. Admin registrations are global, so without the mixin a tenant superuser
   would see the platform's models in their own admin.
3. Tenant models may have a `ForeignKey` to a shared model (tenant table → public table);
   never the other way round.

## 8.3 Know which tenant you are in

```python
request.tenant  # in views (set by TenantMiddleware)

from django.db import connection

connection.tenant, connection.schema_name  # anywhere
```

## 8.4 Run code in another tenant

```python
from django_tenants.utils import schema_context, tenant_context

with schema_context("acme"):
    Project.objects.count()

with tenant_context(tenant):
    ...

from apps.core.tenancy import for_each_tenant

counts = for_each_tenant(lambda: Project.objects.count())  # {"acme": 3, "globex": 1}
```

Management commands run in the public schema by default; use
`python manage.py tenant_command <command> --schema=acme`.

## 8.5 Cross-tenant reporting

Options, simplest first:

1. Loop with `for_each_tenant()` (fine for hundreds of tenants, in a Celery task).
2. Write events to a shared/global app (like `apps/analytics`) as they happen.
3. Raw SQL `UNION ALL` across schemas, or replicate into a warehouse.

## 8.6 URLs

* `config/urls.py` serves every tenant hostname.
* `config/urls_public.py` serves `PUBLIC_DOMAIN`.
* To build an absolute URL for a tenant (emails, webhooks):
  `f"https://{tenant.get_primary_domain().domain}{path}"`.

Next: [9. Background tasks](09-background-tasks.md)
