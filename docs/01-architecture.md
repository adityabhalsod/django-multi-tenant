# 1. Architecture and the research behind it

This page explains **which multi-tenancy model this boilerplate uses and why**, so you can
decide with confidence whether it fits your product.

## 1.1 The three ways to do multi-tenancy in Django

| | Shared schema (row-level) | **Schema per tenant** (this repo) | Database per tenant |
|---|---|---|---|
| How it isolates | A `tenant_id` column on every table, filtered in every query | One PostgreSQL schema per tenant; the connection's `search_path` selects it | A separate database (or server) per tenant |
| Isolation strength | Weakest: one missing `.filter()` leaks data | Strong: queries physically cannot see other schemas' tables | Strongest |
| Code changes | Every model, query, admin, serializer | None in business apps | Router + connection management everywhere |
| Tenants per cluster | Millions | Thousands to low tens of thousands | Tens to hundreds |
| Per-tenant backup / restore / export | Hard | Easy (`pg_dump -n <schema>`) | Easiest |
| Migrations | Once | Once per schema (parallelisable) | Once per database |
| Cross-tenant reporting | Trivial | Possible (shared apps, analytics DB, or `UNION` across schemas) | Hard |
| Typical libraries | `django-multitenant` (Citus), `django-scopes`, custom managers | **`django-tenants`**, `django-pgschemas` | Custom routers |

### Libraries reviewed (November 2026)

| Library | Model | Status | Verdict |
|---|---|---|---|
| [`django-tenants`](https://github.com/django-tenants/django-tenants) 4.0.x | Schema per tenant | Active, supports Django 5.2 / 6.0 / 6.1 | **Chosen.** Most widely used, mature, good docs, Celery integration. |
| [`django-pgschemas`](https://github.com/lorinkoz/django-pgschemas) 1.3 | Schema per tenant | Active | Good alternative with static + dynamic tenants; smaller ecosystem. |
| [`django-tenant-users`](https://github.com/Corvia/django-tenant-users) 3.x | Add-on for django-tenants | Active | Use it if one login must span several tenants (see 6.7). |
| [`django-multitenant`](https://github.com/citusdata/django-multitenant) 4.1 | Shared schema (Citus) | Last release 2023 | Only if you are on Citus and need millions of tenants. |
| [`django-scopes`](https://github.com/raphaelm/django-scopes) 2.2 | Shared schema guard rails | Active | Good safety net for row-level designs. |
| `django-tenant-schemas` | Schema per tenant | Legacy predecessor of django-tenants | Do not start new projects on it. |

### Why schema-per-tenant is the default here

1. **Isolation without discipline.** Business code (`apps/projects`) contains zero tenant
   logic, yet cannot read another tenant's rows. Row-level designs depend on every
   developer remembering a filter forever.
2. **It scales far enough.** PostgreSQL handles thousands of schemas comfortably. Migrations
   run in parallel (`TENANT_MIGRATION_EXECUTOR=multiprocessing`).
3. **Operational wins.** Per-tenant backup, restore, export, deletion (GDPR) and moving a big
   tenant to its own database later are each one `pg_dump -n` away.
4. **Escape hatches.** Global data goes in the `public` schema or a separate database, which
   this boilerplate already wires up (see [7. Multiple databases](07-multiple-databases.md)).

**When not to use it:** a consumer app with millions of tiny "tenants" (use row-level),
or regulated customers that contractually require their own database server (use database
per tenant for those customers).

## 1.2 How a request flows

```mermaid
sequenceDiagram
    participant B as Browser (acme.example.com)
    participant H as HealthCheckMiddleware
    participant T as TenantMiddleware
    participant DB as PostgreSQL
    participant V as View / ORM
    B->>H: GET /api/projects/
    H->>T: not a /health/ path, continue
    T->>DB: SELECT tenant FROM public.tenants_domain WHERE domain='acme.example.com'
    T->>T: connection.set_tenant(acme), 403 if tenant inactive
    T->>V: request.tenant = acme, urlconf = config.urls
    V->>DB: SET search_path = "acme", "public"; SELECT ... FROM projects_project
    DB-->>V: only acme's rows
```

* The **hostname** decides the tenant. `localhost` is the public site; `acme.localhost` is a tenant.
* The **public hostname** uses `config/urls_public.py` (landing page, platform admin).
  Tenant hostnames use `config/urls.py` (tenant admin, API).
* Unknown hostnames get **404** (`SHOW_PUBLIC_IF_NO_TENANT_FOUND=True` serves the public site instead).

## 1.3 Shared apps vs tenant apps

Defined in `config/settings/base.py`:

* `SHARED_APPS`: tables created **only in `public`**: tenants, domains, analytics, platform users.
* `TENANT_APPS`: tables created **in every tenant schema**: users, auth tokens, sessions, projects.
* An app in **both** lists (here: `auth`, `contenttypes`, `sessions`, `admin`, `users`) gets a
  table in `public` *and* in every tenant. That is how platform staff and tenant users stay
  separate while sharing one `User` model.

## 1.4 Repository layout

```
config/
  settings/{base,local,production,test}.py   environment-specific settings
  databases.py        builds DATABASES from DATABASE_URL / replicas / extra DBs
  db_routers.py       replica + dedicated-database router (runs before TenantSyncRouter)
  urls.py             tenant URLs           urls_public.py  public-site URLs
  celery.py           tenant-aware Celery app
apps/
  core/               middleware, health checks, tenancy helpers, db pinning, admin mixin
  tenants/            Tenant + Domain models, provisioning service, management commands
  users/              custom User model (public + every tenant)
  projects/           example tenant app with a DRF API and a Celery task
  analytics/          example global app that can live in its own database
docker/               entrypoint, gunicorn, nginx, postgres init + replica scripts
docs/                 you are here
```

Next: [2. Quick start](02-quickstart.md)
