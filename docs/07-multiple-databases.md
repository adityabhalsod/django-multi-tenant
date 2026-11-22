# 7. Multiple databases

The boilerplate supports three kinds of database at once, all switched on with environment
variables and **no code changes**:

```
                    ┌───────────────────────────── default (primary) ─────┐
 writes, tenant     │  public schema: tenants, domains, platform users    │
 metadata, pinned ─▶│  acme schema / globex schema / ... one per tenant   │──streaming──▶ replica_1, replica_2 ...
 reads              └─────────────────────────────────────────────────────┘                (reads, same schemas)

 apps routed with DATABASE_APP_ROUTES ─────────────▶ analytics (separate, not tenant-aware)
```

## 7.1 Step 1: the primary database (required)

```env
DATABASE_URL=postgres://app:app@localhost:5432/app
```

`config/databases.py` turns it into the `default` alias with the
`django_tenants.postgresql_backend` engine, persistent connections (`DB_CONN_MAX_AGE`) and
connection health checks.

## 7.2 Step 2: read replicas (optional)

```env
DATABASE_REPLICA_URLS=postgres://app:app@replica-1:5432/app,postgres://app:app@replica-2:5432/app
```

They become `replica_1`, `replica_2`, ... Then `config/db_routers.py::MultiDatabaseRouter`:

* sends **reads** of tenant data to a random replica,
* **switches the replica connection to the same tenant schema** as the primary connection
  right before the query (so isolation holds on replicas too),
* keeps tenant metadata (`tenants`, `auth`, `sessions`, `authtoken`, `contenttypes`) on the
  primary, so a lagging replica can never resolve a deleted domain or a revoked token,
* sends all **writes** to the primary,
* never migrates replicas (`TEST.MIRROR = default` in tests).

**Read-your-writes.** Replication lag means a row you just wrote might not be on the replica
yet. Two tools handle that:

```python
# 1. Automatic: PrimaryPinningMiddleware pins POST/PUT/PATCH/DELETE requests to the primary.

# 2. Manual, anywhere (views, tasks, services):
from apps.core.db import use_primary

with use_primary():
    invoice = Invoice.objects.get(pk=pk)  # guaranteed fresh
```

Celery workers switch the schema on the primary **and** every replica
(`CELERY_TASK_TENANT_DATABASES`).

**Try it locally:** `docker compose --profile replica up -d` with
`DATABASE_REPLICA_URLS=postgres://app:app@db-replica:5432/app`, then set `DB_LOG_LEVEL=DEBUG`
and watch `alias=replica_1` appear in the SQL log for GET requests.

## 7.3 Step 3: extra databases for specific apps (optional)

Some data is not per tenant: analytics events, audit logs, a reporting warehouse, a legacy
system. Put it in its own database:

```env
DATABASE_EXTRA_URLS=analytics=postgres://app:app@warehouse:5432/analytics
DATABASE_APP_ROUTES=analytics=analytics
```

* `DATABASE_EXTRA_URLS`: `alias=url` pairs. These use the plain PostgreSQL backend.
* `DATABASE_APP_ROUTES`: `app_label=alias` pairs. Every read, write and migration of that
  app goes to that alias.
* If a route points to an alias that is not configured, it is ignored and the app falls back
  to the primary database (the app must then be in `SHARED_APPS`, like `analytics` is).
  That keeps "one database" setups working with the same code.

Migrate extra databases with:

```bash
python manage.py migrate_extra              # all extra databases
python manage.py migrate_extra analytics    # one
```

(`migrate_schemas` only handles the tenant database; Django's stock `migrate` is wrapped by
`migrate_extra` because django-tenants replaces `migrate`.)

The example `apps/analytics` app stores the tenant's schema name on each row, because this
data is global. `apps.analytics.services.track()` is best-effort: it logs instead of raising,
since it cannot share a transaction with the primary database.

### Add your own routed app, step by step

1. `python manage.py startapp audit apps/audit` and add `"apps.audit"` to `SHARED_APPS`.
2. Write models; include a `tenant_schema` field if rows belong to tenants.
3. Add `PublicSchemaOnlyAdminMixin` to its admin classes.
4. `python manage.py makemigrations audit`
5. `DATABASE_EXTRA_URLS=...,audit=postgres://.../audit` and `DATABASE_APP_ROUTES=...,audit=audit`
6. `python manage.py migrate_extra audit`

Remember: Django cannot join or put foreign keys across databases. Store IDs, not FKs.

## 7.4 Rules the router enforces

| Situation | Database |
|---|---|
| Read, routed app | its alias |
| Read, tenant metadata / auth / sessions | `default` |
| Read, anything else, replicas configured, not pinned | random replica (schema synced) |
| Read, otherwise | `default` |
| Write | routed alias, else `default` |
| Migrate on a replica | never |
| Migrate routed app | only on its alias |
| Migrate other apps on an extra DB | never |
| Migrate on `default` | decided by `TenantSyncRouter` (`SHARED_APPS` vs `TENANT_APPS`) |

## 7.5 Connection pooling

django-tenants selects the tenant with a session-level `SET search_path`, so the pooling
mode matters:

| Option | Safe? | How |
|---|---|---|
| Persistent connections (default) | Yes | `DB_CONN_MAX_AGE=60` |
| Django's native psycopg pool | Yes | `DB_POOL=True` (+ `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_POOL_TIMEOUT`). The search path is re-issued whenever a connection is taken from the pool. |
| PgBouncer **session** mode | Yes | Point `DATABASE_URL` at PgBouncer. |
| PgBouncer **transaction** mode | Only with care | `DB_CONN_MAX_AGE=0`, `TENANT_LIMIT_SET_CALLS=False` and `ATOMIC_REQUESTS=True`, so the `SET` and your queries share one transaction. Otherwise a query can run on a server connection whose search path belongs to another tenant. |

Start with the native pool; add PgBouncer (session mode) when the number of app processes
outgrows PostgreSQL's connection limit.

## 7.6 Moving a big tenant to its own database later

Schema-per-tenant makes this a data move, not a rewrite: `pg_dump -n bigcorp` into a new
server, then route that tenant's connections there. A common next step is a second
tenant-aware alias plus `TENANT_DB_ALIAS`-aware routing for that tenant; start there only when
one tenant actually needs it.

Next: [8. Building features](08-building-features.md)
