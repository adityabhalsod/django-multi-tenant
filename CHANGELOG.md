# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-22

### Added
- Schema-per-tenant multi-tenancy with django-tenants 4 on Django 6.1 and PostgreSQL 18.
- Tenant and Domain models, `provision_tenant` and `bootstrap_public` commands, tenant suspension.
- Multiple databases: read replicas with tenant-schema sync and primary pinning, per-app databases, `migrate_extra`.
- Tenant-aware Celery and beat, Redis cache, media storage (filesystem and S3), email via `MAILERS`.
- Example tenant app (projects) with a DRF API and OpenAPI docs; example global app (analytics).
- uv project, multi-stage Dockerfile, development and production Compose stacks, streaming replica profile.
- Test suite proving tenant isolation, GitHub Actions CI, Ruff, pre-commit, Makefile.
- Fourteen step-by-step guides in `docs/`.
