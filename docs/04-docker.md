# 4. Docker and Docker Compose

## 4.1 The Dockerfile, stage by stage

| Stage | What it does |
|---|---|
| `uv` | Pulls the pinned uv binary from `ghcr.io/astral-sh/uv`. |
| `base` | `python:3.13-slim-bookworm` + uv environment variables. |
| `deps` | Installs **runtime** dependencies into `/opt/venv` (cached on `uv.lock`). |
| `deps-dev` | Adds the `dev` group (pytest, ruff, debug toolbar...). |
| `runtime` | Creates the non-root `app` user (UID/GID configurable) and the entrypoint. |
| `development` | `deps-dev` venv + uv + source. Default command: `runserver`. |
| `production` | `deps` venv + source, runs `collectstatic` at build time, health check, gunicorn. |

```bash
docker build --target development -t django-multi-tenant:dev .
docker build --target production  -t django-multi-tenant:latest .
```

### The entrypoint (`docker/entrypoint.sh`)

1. **Waits for PostgreSQL** (`WAIT_FOR_DB=1`, timeout `DB_WAIT_TIMEOUT=60`).
2. If `RUN_MIGRATIONS=1`: runs `migrate_schemas` (public schema, then every tenant),
   `migrate_extra` (extra databases) and `bootstrap_public` (public tenant + domain).
3. `exec`s the container command, so signals reach gunicorn/celery directly.

Only **one** container should set `RUN_MIGRATIONS=1` so that scaled web replicas never race.

## 4.2 Development stack: `compose.yaml`

| Service | Purpose | Port |
|---|---|---|
| `web` | Django dev server with live reload (source is bind-mounted). Runs migrations. | 8000 |
| `worker` | Celery worker (tenant-aware). Starts after `web` is healthy. | |
| `beat` | Celery beat with `TenantAwarePersistentScheduler`. | |
| `db` | PostgreSQL 18. The init script creates the `analytics` database and a replication role. | 5432 |
| `db-replica` | **Profile `replica`.** Streaming hot-standby replica of `db`. | 5433 |
| `redis` | Cache, Celery broker and result backend. | |
| `mailpit` | Catches all outgoing email. | 8025 |

Common commands (each has a `make` shortcut, run `make help`):

```bash
docker compose up -d --build              # start
docker compose logs -f web worker         # follow logs
docker compose exec web python manage.py shell
docker compose exec web pytest            # run tests in the container
docker compose exec db psql -U app app    # SQL shell; try: \dn  (lists tenant schemas)
docker compose --profile replica up -d    # add the read replica
docker compose down                       # stop, keep data
docker compose down -v                    # stop and delete all data
```

**File permissions on Linux:** files created inside the container (e.g. new migrations) are
owned by UID 1000. If your user has another UID, set `APP_UID`/`APP_GID` in `.env` and rebuild.

**Ports already in use?** Change `APP_PORT`, `POSTGRES_PORT`, `POSTGRES_REPLICA_PORT` or
`MAILPIT_PORT` in `.env`.

## 4.3 How the read replica works

1. On first start, `db` runs `docker/postgres/initdb/10-databases.sh`, which creates the
   `replicator` role and allows it in `pg_hba.conf`.
2. `db-replica` runs `docker/postgres/replica-entrypoint.sh`: it clones the primary with
   `pg_basebackup --write-recovery-conf` using a replication slot, then starts PostgreSQL in
   hot-standby mode. Every change on the primary (including new tenant schemas) streams to it.
3. Setting `DATABASE_REPLICA_URLS` makes Django send reads there (see
   [7. Multiple databases](07-multiple-databases.md)).

The init script only runs on an **empty** volume. If you started `db` before, run
`docker compose down -v` once to re-initialise.

## 4.4 Production-like stack: `compose.prod.yaml`

```bash
cp .env.example .env.prod      # set DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DJANGO_ALLOWED_HOSTS...
docker compose -f compose.prod.yaml --env-file .env.prod up -d --build
```

| Service | Purpose |
|---|---|
| `migrate` | One-off job: migrations + public tenant, then exits. Others wait for it to succeed. |
| `web` | gunicorn (`docker/gunicorn.conf.py`), Docker health check on `/health/live/`. |
| `worker`, `beat` | Celery. |
| `nginx` | Reverse proxy on port 80 for every hostname; serves `/media/`. Static files are served by WhiteNoise. |
| `db`, `redis` | Same as development, not published to the host. |

> Trying it on your laptop without TLS? Set `DJANGO_SECURE_SSL_REDIRECT=False` in `.env.prod`,
> otherwise every request redirects to HTTPS.

Next: [5. Configuration](05-configuration.md)
