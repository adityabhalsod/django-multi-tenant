# 13. Security model

## 13.1 What isolates tenants

| Layer | Mechanism |
|---|---|
| Database | Each tenant's tables live in its own schema; the connection's `search_path` is `"<tenant>", "public"`. |
| Authentication | Users, sessions and API tokens are tenant tables. Credentials from one tenant are invalid on another. |
| Cookies | Host-only session cookies (do not set `SESSION_COOKIE_DOMAIN`). |
| Cache | Keys are prefixed with the schema name. |
| Files | Media stored under `<schema>/`. |
| Background jobs | The schema travels with every Celery task. |
| Replicas | The router syncs the replica connection to the same schema before each read. |
| Admin | `PublicSchemaOnlyAdminMixin` hides platform models from tenant admins. |

## 13.2 Pitfalls to avoid

1. **Public tables are visible from tenants.** `public` is on every tenant's search path, so
   tenant code can query shared models. Never put tenant-private data in a shared app, and
   always use `PublicSchemaOnlyAdminMixin` for shared models' admins.
2. **Raw SQL with schema names:** never interpolate user input into `SET search_path` or
   schema-qualified SQL. Schema names are validated at creation (`SCHEMA_NAME_RE`).
3. **Threads and async tasks you start yourself** do not inherit the tenant. Wrap them in
   `tenant_context(tenant)`.
4. **Caching outside the Django cache** (module globals, `lru_cache`) is shared by all
   tenants in the process. Key it by `connection.schema_name`.
5. **Host header trust:** keep `ALLOWED_HOSTS` restricted; the host selects the tenant.
6. **Global data in another database** (`analytics`) must carry and filter by
   `tenant_schema` explicitly; the schema boundary does not apply there.
7. **Deleting tenants:** `auto_drop_schema=False` keeps data after a row is deleted. Use
   `delete_tenant` deliberately and keep backups.

## 13.3 Reporting vulnerabilities

See [SECURITY.md](../SECURITY.md).

Next: [14. Troubleshooting](14-troubleshooting.md)
