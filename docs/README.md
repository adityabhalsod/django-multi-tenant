# Documentation

A step-by-step guide to every part of the boilerplate. Read it in order the first time.

| # | Guide | You will learn |
|---|---|---|
| 1 | [Architecture and research](01-architecture.md) | The three multi-tenancy models, libraries compared, why schema-per-tenant, request flow |
| 2 | [Quick start](02-quickstart.md) | Run it with Docker or uv in five minutes, create tenants, see isolation |
| 3 | [uv](03-uv.md) | Installing Python and dependencies, the lockfile, everyday commands |
| 4 | [Docker](04-docker.md) | Dockerfile stages, dev and prod Compose stacks, the read replica |
| 5 | [Configuration](05-configuration.md) | Every environment variable and settings module |
| 6 | [Managing tenants](06-tenants.md) | Create, domains, suspend, delete, users across tenants |
| 7 | [Multiple databases](07-multiple-databases.md) | Primary, read replicas, per-app databases, pooling |
| 8 | [Building features](08-building-features.md) | Adding tenant and shared apps, working across tenants |
| 9 | [Background tasks](09-background-tasks.md) | Tenant-aware Celery, periodic tasks |
| 10 | [Cache, files and email](10-cache-files-email.md) | Tenant-safe caching, media storage, S3, email |
| 11 | [Deployment](11-deployment.md) | DNS, TLS, migrations, processes, production checklist |
| 12 | [Testing](12-testing.md) | Tenant-aware tests and what the suite guarantees |
| 13 | [Security](13-security.md) | The isolation model and its pitfalls |
| 14 | [Troubleshooting](14-troubleshooting.md) | Common errors and FAQ |
