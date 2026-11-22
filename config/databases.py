"""Build Django's ``DATABASES`` setting from environment variables.

Three kinds of database are supported, all configured with URLs:

``DATABASE_URL`` (required)
    The primary PostgreSQL database. It holds the ``public`` schema (shared
    data such as tenants and domains) plus one schema per tenant. It always
    uses the ``django_tenants`` backend.

``DATABASE_REPLICA_URLS`` (optional, comma separated)
    Read replicas of the primary. They also use the ``django_tenants``
    backend so that the tenant's ``search_path`` can be applied to them.
    They are registered as ``replica_1``, ``replica_2``, ...

``DATABASE_EXTRA_URLS`` (optional, comma separated ``alias=url`` pairs)
    Completely separate databases that are *not* tenant-aware, e.g. an
    analytics warehouse or a legacy system. Apps are sent to them with
    ``DATABASE_APP_ROUTES`` (``app_label=alias`` pairs). See
    ``config/db_routers.py`` and ``docs/07-multiple-databases.md``.
"""

from __future__ import annotations

import environ

TENANT_ENGINE = "django_tenants.postgresql_backend"


def _parse_pairs(raw: str) -> dict[str, str]:
    """Parse ``"a=1,b=2"`` into ``{"a": "1", "b": "2"}`` (whitespace tolerant)."""
    pairs: dict[str, str] = {}
    for item in filter(None, (chunk.strip() for chunk in raw.split(","))):
        key, sep, value = item.partition("=")
        if not sep or not key.strip() or not value.strip():
            raise ValueError(f"Expected 'name=value', got {item!r}")
        pairs[key.strip()] = value.strip()
    return pairs


def _db(env: environ.Env, url: str, *, tenant_aware: bool) -> dict:
    config = env.db_url_config(url)
    if tenant_aware:
        config["ENGINE"] = TENANT_ENGINE
    config.setdefault("OPTIONS", {})
    config["OPTIONS"].setdefault("connect_timeout", env.int("DB_CONNECT_TIMEOUT", default=5))
    if env.bool("DB_POOL", default=False):
        # Django's native psycopg 3 connection pool. Requires CONN_MAX_AGE=0.
        config["CONN_MAX_AGE"] = 0
        config["OPTIONS"]["pool"] = {
            "min_size": env.int("DB_POOL_MIN_SIZE", default=2),
            "max_size": env.int("DB_POOL_MAX_SIZE", default=10),
            "timeout": env.int("DB_POOL_TIMEOUT", default=10),
        }
    else:
        config["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
        config["CONN_HEALTH_CHECKS"] = True
    return config


def build_databases(env: environ.Env) -> tuple[dict, list[str], dict[str, str]]:
    """Return ``(DATABASES, replica_aliases, app_routes)``."""
    databases = {"default": _db(env, env.str("DATABASE_URL"), tenant_aware=True)}

    replicas: list[str] = []
    for index, url in enumerate(env.list("DATABASE_REPLICA_URLS", default=[]), start=1):
        alias = f"replica_{index}"
        databases[alias] = _db(env, url, tenant_aware=True)
        # Tests must not try to create a separate test database for a replica:
        # it mirrors the primary.
        databases[alias]["TEST"] = {"MIRROR": "default"}
        replicas.append(alias)

    for alias, url in _parse_pairs(env.str("DATABASE_EXTRA_URLS", default="")).items():
        if alias in databases:
            raise ValueError(f"Database alias {alias!r} is reserved or duplicated")
        databases[alias] = _db(env, url, tenant_aware=False)

    app_routes = _parse_pairs(env.str("DATABASE_APP_ROUTES", default=""))
    # Only route to aliases that actually exist. If the extra database is not
    # configured the app silently falls back to the primary database, which
    # keeps local development simple.
    app_routes = {app: alias for app, alias in app_routes.items() if alias in databases}

    return databases, replicas, app_routes
