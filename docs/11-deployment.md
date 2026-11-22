# 11. Deployment

The production image (`--target production`) is the same everywhere: Docker Compose on a VM,
Kubernetes, ECS, Fly.io, Render, Railway. This page is the checklist.

## 11.1 Step by step

1. **DNS:** an `A`/`CNAME` for `example.com` **and** a wildcard `*.example.com` pointing at
   your load balancer.
2. **TLS:** a wildcard certificate for `*.example.com` (DNS-01 challenge), plus on-demand
   certificates if tenants bring custom domains.
3. **Managed services:** PostgreSQL 14+ (18 recommended), Redis 7+. Optionally read replicas.
4. **Environment** (secrets in your platform's secret store, never in the image):
   ```env
   DJANGO_SETTINGS_MODULE=config.settings.production
   DJANGO_SECRET_KEY=<50+ random chars>
   DJANGO_ALLOWED_HOSTS=.example.com
   DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://*.example.com
   PUBLIC_DOMAIN=example.com
   DATABASE_URL=postgres://...
   DATABASE_REPLICA_URLS=postgres://...        # optional
   REDIS_URL=rediss://...
   SENTRY_DSN=...                              # optional
   ```
5. **Build and push** the image: `docker build --target production -t registry/app:<sha> .`
6. **Migrate** as a one-off job before rolling out new code:
   ```bash
   docker run --rm --env-file .env.prod -e RUN_MIGRATIONS=1 registry/app:<sha> true
   ```
   (The `migrate` service in `compose.prod.yaml` does exactly this.)
7. **Run processes** from the same image:
   * web: default command (gunicorn), health checks `GET /health/live/` (liveness) and
     `GET /health/ready/` (readiness: every database and the cache)
   * worker: `celery -A config worker -l info`
   * beat (exactly one): `celery -A config beat -l info --scheduler tenant_schemas_celery.scheduler.TenantAwarePersistentScheduler`
8. **Proxy:** forward the original `Host` header (tenant selection depends on it) and
   `X-Forwarded-Proto`. See `docker/nginx/default.conf`.
9. **Platform admin:** `python manage.py create_tenant_superuser --schema=public`.

## 11.2 Production checklist

- [ ] `DEBUG=False`, strong `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS` restricted to your domains
- [ ] HTTPS everywhere, HSTS enabled (`DJANGO_SECURE_HSTS_SECONDS`)
- [ ] `python manage.py check --deploy` passes (W021 about HSTS preload is expected until you opt in)
- [ ] Database backups + tested restores (per-tenant restores: `pg_restore -n <schema>`)
- [ ] `TENANT_MIGRATION_EXECUTOR=multiprocessing` once you have many tenants
- [ ] Migrations are backwards compatible (expand, deploy, contract)
- [ ] Media on S3 (`USE_S3_MEDIA=True`), not on the container filesystem
- [ ] Error tracking (Sentry) and log aggregation (every line contains `[schema]`)
- [ ] Rate limiting at the proxy, per tenant if needed
- [ ] Connection pooling chosen deliberately (see 7.5)

## 11.3 Scaling notes

* Web and workers are stateless: scale horizontally.
* Tenant resolution costs one indexed query per request; cache it if it ever shows up in
  profiles (override `TenantMiddleware.get_tenant`).
* Route heavy reads to replicas (already wired), and heavy global data to its own database.

Next: [12. Testing](12-testing.md)
