# 5. Configuration

All machine-specific configuration comes from **environment variables** (or a `.env` file,
which never overrides real environment variables). Settings modules:

| Module | Used by | Notes |
|---|---|---|
| `config.settings.base` | everything | All shared settings. |
| `config.settings.local` | `manage.py`, Celery, dev containers | `DEBUG=True`, Mailpit, optional debug toolbar. |
| `config.settings.production` | `wsgi.py`, `asgi.py`, prod image | HTTPS, HSTS, secure cookies, optional S3 + Sentry. |
| `config.settings.test` | pytest | Fast hashing, in-memory cache and email, eager Celery. |

Select one with `DJANGO_SETTINGS_MODULE`.

## 5.1 Environment variables

### Django

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | **required** | Long random string. |
| `DJANGO_DEBUG` | `False` (`True` in local) | Never enable in production. |
| `DJANGO_ALLOWED_HOSTS` | `.localhost,127.0.0.1` | Comma separated. A leading dot allows all subdomains, which you need for tenants. Custom tenant domains must be added too (or use a wildcard proxy check). |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | e.g. `https://*.example.com`. |
| `PUBLIC_DOMAIN` | `localhost` | Hostname of the public site; default parent domain for new tenants. |
| `SHOW_PUBLIC_IF_NO_TENANT_FOUND` | `False` | Serve the public site for unknown hosts instead of 404. |
| `TIME_ZONE` | `UTC` | |
| `LOG_LEVEL` / `DB_LOG_LEVEL` | `INFO` / `WARNING` | Set `DB_LOG_LEVEL=DEBUG` to log every SQL query with its database alias. |

### Databases (details in [7. Multiple databases](07-multiple-databases.md))

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | **required** | Primary PostgreSQL: `postgres://user:pass@host:5432/db`. |
| `DATABASE_REPLICA_URLS` | empty | Comma-separated read replica URLs. |
| `DATABASE_EXTRA_URLS` | empty | `alias=url` pairs of extra, non tenant-aware databases. |
| `DATABASE_APP_ROUTES` | empty | `app_label=alias` pairs: which app lives in which extra database. |
| `DB_CONN_MAX_AGE` | `60` | Persistent connection lifetime (seconds). |
| `DB_POOL` | `False` | Use Django's native psycopg connection pool instead (`DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_POOL_TIMEOUT`). |
| `TENANT_LIMIT_SET_CALLS` | `True` | Set `False` behind PgBouncer in transaction mode (see 7.5). |
| `DB_CONNECT_TIMEOUT` | `5` | Seconds. |
| `TENANT_MIGRATION_EXECUTOR` | `standard` | `multiprocessing` migrates tenant schemas in parallel. |
| `TENANT_MULTIPROCESSING_MAX_PROCESSES` | `2` | Parallelism for the above. |

### Cache, Celery, email

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Default for cache, broker and results. |
| `CACHE_URL` | `REDIS_URL` | Separate Redis for the cache. |
| `CACHE_KEY_PREFIX` / `CACHE_DEFAULT_TIMEOUT` | `dmt` / `300` | |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | `REDIS_URL` | |
| `EMAIL_BACKEND` | SMTP | Any Django email backend path. |
| `EMAIL_HOST` / `EMAIL_PORT` | `localhost` / `25` (`mailpit` / `1025` in local) | |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` / `EMAIL_TIMEOUT` | | SMTP options. |
| `DEFAULT_FROM_EMAIL` | `noreply@localhost` | |

Email is configured with Django 6.1's new `MAILERS` setting (the old `EMAIL_*` settings are
deprecated); the environment variable names stay the familiar ones.

### Production only

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECURE_SSL_REDIRECT` | `True` | Redirect HTTP to HTTPS (health checks are exempt). |
| `DJANGO_SECURE_HSTS_SECONDS` | 30 days | |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` / `..._PRELOAD` | `True` / `False` | |
| `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE` | | Needs `uv sync --extra sentry`. |
| `USE_S3_MEDIA`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL` | | Tenant-aware S3 media; needs `--extra s3`. |
| `GUNICORN_WORKERS`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`, ... | | See `docker/gunicorn.conf.py`. |

### Docker Compose only

`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_REPLICATION_PASSWORD`,
`APP_PORT`, `POSTGRES_PORT`, `POSTGRES_REPLICA_PORT`, `MAILPIT_PORT`, `APP_UID`, `APP_GID`.

## 5.2 Key django-tenants settings (in `base.py`)

| Setting | Value | Why |
|---|---|---|
| `TENANT_MODEL` / `TENANT_DOMAIN_MODEL` | `tenants.Tenant` / `tenants.Domain` | |
| `PUBLIC_SCHEMA_URLCONF` | `config.urls_public` | Different URLs for the public site. |
| `DATABASE_ROUTERS` | `MultiDatabaseRouter`, `TenantSyncRouter` | Order matters: ours first. |
| `TENANT_LIMIT_SET_CALLS` | `True` | Avoid repeating `SET search_path` within a request. |
| `CACHES[...]["KEY_FUNCTION"]` | `django_tenants.cache.make_key` | Prefix every cache key with the schema. |
| `STORAGES["default"]` | `TenantFileSystemStorage` | Media under `MEDIA_ROOT/<schema>/`. |
| `LOGGING` filter | `TenantContextFilter` | Every log line shows `[schema]`. |

Next: [6. Managing tenants](06-tenants.md)
