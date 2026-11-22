# 10. Cache, files and email

## 10.1 Cache

Django's built-in Redis cache with django-tenants' key function:

```python
"KEY_FUNCTION": "django_tenants.cache.make_key"   # -> "<schema>:<prefix>:<version>:<key>"
```

`cache.get("dashboard")` in Acme and in Globex are different keys, so there is no
cross-tenant cache bleed. For truly global keys, read them inside
`schema_context("public")`.

Sessions are stored in each tenant's database schema (`django.contrib.sessions` is a tenant
app), and cookies are host-only, so a login never leaks between tenant domains.

## 10.2 Media files

`STORAGES["default"]` is `TenantFileSystemStorage` with
`MULTITENANT_RELATIVE_MEDIA_ROOT = "%s"`: uploads go to `MEDIA_ROOT/<schema>/...`.

For production, use S3 or any S3-compatible store (R2, MinIO, Spaces):

```bash
uv sync --extra s3     # or build the image with --build-arg UV_EXTRAS="--extra s3"
```

```env
USE_S3_MEDIA=True
AWS_STORAGE_BUCKET_NAME=my-bucket
AWS_S3_REGION_NAME=eu-central-1
# AWS_S3_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com
```

`apps.core.storage.TenantS3Storage` prefixes every key with the schema name and uses signed
URLs by default.

## 10.3 Static files

Static files are shared by all tenants, served by WhiteNoise with compressed, hashed file
names, and collected at image build time. (Per-tenant themes are possible with
`django_tenants.staticfiles`, but are rarely worth it.)

## 10.4 Email

Configured with Django 6.1 `MAILERS`. In development every email lands in Mailpit at
http://localhost:8025. In production set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, or point `EMAIL_BACKEND` at a provider backend.

To brand emails per tenant, render templates with `connection.tenant` in the context.

Next: [11. Deployment](11-deployment.md)
