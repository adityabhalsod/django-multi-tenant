"""Base settings shared by every environment.

All configuration that differs between machines comes from environment
variables (12-factor). See ``.env.example`` for the full list and
``docs/05-configuration.md`` for an explanation of each one.
"""

from pathlib import Path

import environ

from config.databases import build_databases

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# A local .env file is optional; real environment variables always win.
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env.str("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
# Tenants are added at runtime, so allow the whole parent domain: a leading
# dot matches the domain and every subdomain (".example.com").
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[".localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Hostname of the main (public) site. Tenants get <schema>.<PUBLIC_DOMAIN>
# by default, e.g. acme.localhost during development.
PUBLIC_DOMAIN = env.str("PUBLIC_DOMAIN", default="localhost")

# ---------------------------------------------------------------------------
# Multi-tenancy (django-tenants, schema per tenant)
# ---------------------------------------------------------------------------
# Apps whose tables live ONLY in the "public" schema.
SHARED_APPS = [
    "django_tenants",  # must be first
    "apps.tenants",  # Tenant + Domain models
    "apps.core",
    "apps.analytics",  # global data; may be routed to its own database
    # Contrib apps also needed by the public (platform) site:
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "django.contrib.staticfiles",
    "apps.users",  # platform staff accounts (public.users_user)
    # Third-party apps without models can be listed in either list:
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
]

# Apps whose tables are created in EVERY tenant schema.
TENANT_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "apps.users",  # tenant's own users (<schema>.users_user)
    "rest_framework.authtoken",
    "apps.projects",  # example business app, copy this pattern
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"
PUBLIC_SCHEMA_URLCONF = "config.urls_public"
ROOT_URLCONF = "config.urls"  # tenant URLconf
# Unknown hostnames: show the public site instead of a 404 (set False to 404).
SHOW_PUBLIC_IF_NO_TENANT_FOUND = env.bool("SHOW_PUBLIC_IF_NO_TENANT_FOUND", default=False)
# Run tenant migrations in parallel processes for large tenant counts.
TENANT_MIGRATION_EXECUTOR = env.str("TENANT_MIGRATION_EXECUTOR", default="standard")
TENANT_MULTIPROCESSING_MAX_PROCESSES = env.int("TENANT_MULTIPROCESSING_MAX_PROCESSES", default=2)
# Skip redundant "SET search_path" calls on a connection. Must be False behind
# PgBouncer in transaction mode (see docs/07-multiple-databases.md#75).
TENANT_LIMIT_SET_CALLS = env.bool("TENANT_LIMIT_SET_CALLS", default=True)

# ---------------------------------------------------------------------------
# Databases (primary + optional replicas + optional extra databases)
# ---------------------------------------------------------------------------
DATABASES, DATABASE_REPLICAS, DATABASE_APP_ROUTES = build_databases(env)
DATABASE_ROUTERS = [
    "config.db_routers.MultiDatabaseRouter",  # replicas + dedicated databases
    "django_tenants.routers.TenantSyncRouter",  # shared vs tenant apps
]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "apps.core.middleware.HealthCheckMiddleware",  # probes work on any host/IP
    "apps.core.middleware.TenantMiddleware",  # selects the schema; keep it at the top
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.core.middleware.PrimaryPinningMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Sessions live in each tenant's schema, so a login on acme.example.com is not
# valid on globex.example.com. Keep cookies host-only (no SESSION_COOKIE_DOMAIN).
SESSION_COOKIE_NAME = "sessionid"

# ---------------------------------------------------------------------------
# Cache (Redis). Keys are prefixed with the schema name -> no cross-tenant hits.
# ---------------------------------------------------------------------------
REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env.str("CACHE_URL", default=REDIS_URL),
        "KEY_FUNCTION": "django_tenants.cache.make_key",
        "KEY_PREFIX": env.str("CACHE_KEY_PREFIX", default="dmt"),
        "TIMEOUT": env.int("CACHE_DEFAULT_TIMEOUT", default=300),
    }
}

# ---------------------------------------------------------------------------
# I18N
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = env.str("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media. Media files are stored per tenant: MEDIA_ROOT/<schema>/...
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = Path(env.str("MEDIA_ROOT", default=str(BASE_DIR / "media")))
MULTITENANT_RELATIVE_MEDIA_ROOT = "%s"  # %s is replaced by the schema name
STORAGES = {
    "default": {"BACKEND": "django_tenants.files.storage.TenantFileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# ---------------------------------------------------------------------------
# Django REST framework + OpenAPI
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Token first so a bad/foreign token yields 401 + WWW-Authenticate.
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Django Multi-Tenant API",
    "DESCRIPTION": "Tenant-scoped API. The tenant is selected by the request hostname.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# ---------------------------------------------------------------------------
# Celery (tenant-aware via tenant-schemas-celery)
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
# Switch the schema on every tenant-aware connection, replicas included.
CELERY_TASK_TENANT_DATABASES = ("default", *DATABASE_REPLICAS)
# Periodic tasks. Without "tenant_schemas" an entry runs once per tenant;
# with "tenant_schemas": ["public"] it runs once, in the public schema.
CELERY_BEAT_SCHEDULE = {
    "nightly-project-report": {
        "task": "apps.projects.tasks.project_report",
        "schedule": 60 * 60 * 24,
    },
}

# ---------------------------------------------------------------------------
# Email (Django 6.1 MAILERS; the old EMAIL_* settings are deprecated)
# ---------------------------------------------------------------------------
MAILERS = {
    "default": {
        "BACKEND": env.str("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"),
        "OPTIONS": {
            "host": env.str("EMAIL_HOST", default="localhost"),
            "port": env.int("EMAIL_PORT", default=25),
            "username": env.str("EMAIL_HOST_USER", default=""),
            "password": env.str("EMAIL_HOST_PASSWORD", default=""),
            "use_tls": env.bool("EMAIL_USE_TLS", default=False),
            "timeout": env.int("EMAIL_TIMEOUT", default=10),
        },
    }
}
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="noreply@localhost")

# ---------------------------------------------------------------------------
# Logging (structured enough for Docker; one line per record)
# ---------------------------------------------------------------------------
LOG_LEVEL = env.str("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        # Adds %(schema_name)s and %(domain_url)s to every record.
        "tenant_context": {"()": "django_tenants.log.TenantContextFilter"},
    },
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s [%(schema_name)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["tenant_context"],
            "formatter": "default",
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.db.backends": {"level": env.str("DB_LOG_LEVEL", default="WARNING")},
    },
}
