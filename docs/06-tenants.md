# 6. Managing tenants

## 6.1 The public tenant

django-tenants needs a `Tenant` row for the `public` schema so that requests to the main
site resolve. `bootstrap_public` creates it (idempotent; the Docker entrypoint runs it):

```bash
python manage.py bootstrap_public                     # uses PUBLIC_DOMAIN
python manage.py bootstrap_public --domain example.com
```

Platform staff are users in the **public** schema:

```bash
python manage.py create_tenant_superuser --schema=public
```

## 6.2 Create a tenant

```bash
python manage.py provision_tenant --name "Acme Corp" \
    --admin-email admin@acme.test --admin-password 'change-me'
# schema: acme_corp     domain: acme-corp.<PUBLIC_DOMAIN>     admin user: admin

python manage.py provision_tenant --name "Acme Corp" --schema acme --domain app.acme.com
```

What happens (see `apps/tenants/services.py::provision_tenant`):

1. The schema name is normalised (`"Acme Corp!"` becomes `acme_corp`) and validated:
   lower-case letters, digits and `_`, not reserved, not `pg_*`.
2. The domain and schema are checked for uniqueness.
3. `Tenant.save()` runs `CREATE SCHEMA` and **all `TENANT_APPS` migrations** in it.
4. The primary `Domain` is created. If that fails, the new schema is dropped again.
5. Optionally, a superuser is created **inside the tenant's schema**.

Call the same function from your own sign-up view or API. Because migrations make it take a
few seconds, real sign-up flows usually queue it as a Celery task.

You can also create tenants in the platform admin (http://localhost:8000/admin/).

## 6.3 Domains

* A tenant can have many domains; one is `is_primary`.
* **Subdomains:** point a wildcard DNS record `*.example.com` at your load balancer and use
  `DJANGO_ALLOWED_HOSTS=.example.com`.
* **Custom domains** (`app.customer.com`): the customer adds a CNAME to your host, you add a
  `Domain` row, add the host to `DJANGO_ALLOWED_HOSTS` (or validate hosts at the proxy), and
  issue a certificate (Caddy on-demand TLS or cert-manager make this automatic).

```bash
python manage.py create_domain      # interactive, from django-tenants
python manage.py delete_domain
```

## 6.4 Suspend a tenant

Set `is_active=False` (admin or shell). `TenantMiddleware` answers every request on that
tenant's domains with **403**, while the data stays intact. `for_each_tenant()` and the
Celery fan-out skip inactive tenants.

## 6.5 Delete a tenant

`Tenant.auto_drop_schema = False`, so deleting the row **keeps the schema** (a safety net).
To really remove the data:

```bash
python manage.py delete_tenant            # asks for confirmation, drops the schema
```

For GDPR exports, back up first: `pg_dump -n acme_corp app > acme_corp.sql`.

## 6.6 Other built-in commands (from django-tenants)

| Command | Purpose |
|---|---|
| `migrate_schemas` | Migrate `public` then every tenant. `--shared` / `--tenant` / `--schema=acme`. |
| `tenant_command <cmd> --schema=acme` | Run any management command inside one tenant. |
| `all_tenants_command <cmd>` | Run a command in every tenant. |
| `create_missing_schemas` | Create schemas for tenant rows that have none. |
| `rename_schema` | Rename a tenant's schema. |
| `clone_tenant` | Clone a template tenant (fast onboarding with sample data). |
| `collectstatic_schemas` | Per-tenant static files, if you use them. |

## 6.7 Users across tenants

By default users are **per tenant**: `alice@acme.test` in `acme` and in `globex` are two
different accounts, and a session or token from one tenant is invalid on another. This is
the simplest and most isolated model.

If one person must log in once and switch between workspaces (Slack-style), add
[`django-tenant-users`](https://github.com/Corvia/django-tenant-users): users move to the
public schema and per-tenant permissions stay in each schema.

## 6.8 Scaling the number of tenants

* Use `TENANT_MIGRATION_EXECUTOR=multiprocessing` once you have more than a few dozen tenants.
* Keep tenant migrations backwards compatible (expand, deploy, contract), because tenants are
  migrated one after another while the old code is still serving traffic.
* Watch PostgreSQL catalog size: tens of thousands of schemas × many tables is where you plan
  sharding (move big tenants to another database, see 7.6).

Next: [7. Multiple databases](07-multiple-databases.md)
