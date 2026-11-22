# 14. Troubleshooting and FAQ

**`404 No tenant for hostname "..."`**
The host has no `Domain` row. Check with `make tenants`. For the public site run
`python manage.py bootstrap_public --domain <host>`. Remember that `127.0.0.1` and
`localhost` are different hosts.

**`DisallowedHost` / 400 Bad Request**
Add the domain to `DJANGO_ALLOWED_HOSTS` (use `.example.com` for all subdomains).

**`relation "xyz" does not exist`**
The table is missing in the current schema. Did you add the app to `TENANT_APPS` (or
`SHARED_APPS`) and run `migrate_schemas`? For a routed app, run `migrate_extra`.

**I ran `python manage.py migrate` and it did something odd**
django-tenants replaces `migrate` with `migrate_schemas`. Use `migrate_schemas` for the
tenant database and `migrate_extra` for extra databases.

**`acme.localhost` does not resolve**
Add `127.0.0.1 acme.localhost` to `/etc/hosts` (Windows:
`C:\Windows\System32\drivers\etc\hosts`).

**The db init script did not create the `analytics` database / replication role**
Init scripts only run on an empty volume: `docker compose down -v` and start again.

**Permission denied writing migrations from the container (Linux)**
Set `APP_UID=$(id -u)` and `APP_GID=$(id -g)` in `.env`, then `docker compose build`.

**Every request redirects to https in the prod stack**
Set `DJANGO_SECURE_SSL_REDIRECT=False` when running without TLS.

**A tenant sees stale data right after saving**
Replication lag. Unsafe requests are pinned automatically; wrap other code in
`apps.core.db.use_primary()`.

**Logged in on one tenant, logged out on another**
Expected: users and sessions are per tenant. See 6.7 for shared users.

**Can I use SQLite or MySQL?**
No. Schema-per-tenant needs PostgreSQL schemas.

**Can I use Django 5.2 LTS instead of 6.1?**
Yes: `uv add "django>=5.2,<5.3"`. Replace the `MAILERS` block with the classic `EMAIL_*`
settings, since `MAILERS` is new in 6.1.

Back to the [docs index](README.md).
