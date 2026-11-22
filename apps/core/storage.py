"""Tenant-aware S3 storage: every tenant writes under ``<schema_name>/``."""

from django.db import connection

try:
    from storages.backends.s3 import S3Storage
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError("Install the s3 extra: `uv sync --extra s3`") from exc


class TenantS3Storage(S3Storage):
    @property
    def location(self):  # type: ignore[override]
        return connection.schema_name

    @location.setter
    def location(self, value):
        # django-storages sets this from settings; the tenant always wins.
        pass
