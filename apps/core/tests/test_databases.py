import environ
import pytest

from config.databases import TENANT_ENGINE, _parse_pairs, build_databases

PRIMARY = "postgres://u:p@primary:5432/app"


def make_env(monkeypatch, **values):
    for key in ("DATABASE_REPLICA_URLS", "DATABASE_EXTRA_URLS", "DATABASE_APP_ROUTES"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DATABASE_URL", PRIMARY)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return environ.Env()


def test_primary_only(monkeypatch):
    databases, replicas, routes = build_databases(make_env(monkeypatch))
    assert list(databases) == ["default"]
    assert databases["default"]["ENGINE"] == TENANT_ENGINE
    assert databases["default"]["HOST"] == "primary"
    assert replicas == [] and routes == {}


def test_replicas_and_extras(monkeypatch):
    env = make_env(
        monkeypatch,
        DATABASE_REPLICA_URLS="postgres://u:p@r1/app,postgres://u:p@r2/app",
        DATABASE_EXTRA_URLS="analytics=postgres://u:p@wh/analytics",
        DATABASE_APP_ROUTES="analytics=analytics, reports=missing",
    )
    databases, replicas, routes = build_databases(env)
    assert replicas == ["replica_1", "replica_2"]
    assert databases["replica_2"]["HOST"] == "r2"
    assert databases["replica_1"]["ENGINE"] == TENANT_ENGINE
    assert databases["replica_1"]["TEST"] == {"MIRROR": "default"}
    # Extra databases are plain PostgreSQL, not tenant-aware.
    assert databases["analytics"]["ENGINE"] == "django.db.backends.postgresql"
    # Routes to aliases that do not exist are dropped (fallback to primary).
    assert routes == {"analytics": "analytics"}


def test_reserved_alias_rejected(monkeypatch):
    env = make_env(monkeypatch, DATABASE_EXTRA_URLS="default=postgres://u:p@x/y")
    with pytest.raises(ValueError, match="reserved"):
        build_databases(env)


@pytest.mark.parametrize("raw", ["novalue", "=x", "a="])
def test_parse_pairs_errors(raw):
    with pytest.raises(ValueError):
        _parse_pairs(raw)
