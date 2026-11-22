# 12. Testing

```bash
uv run pytest                     # all tests (needs PostgreSQL: DATABASE_URL)
uv run pytest -k isolation -x     # filter, stop at first failure
uv run pytest --cov               # coverage report
docker compose exec web pytest    # inside Docker
```

Settings: `config.settings.test` (MD5 hasher, local-memory cache, in-memory email, eager
Celery). Tests need a real PostgreSQL because schemas are a PostgreSQL feature.

## 12.1 Tenant-aware test cases

`apps.core.testing.TenantAPITestCase` (built on django-tenants' `TenantTestCase`):

* creates a tenant with schema `test` and domain `tenant.test.com` once per class,
* runs every test inside that schema,
* gives you `self.client`, a `TenantClient` that sends requests to the tenant's domain.

```python
from apps.core.testing import TenantAPITestCase


class InvoiceTests(TenantAPITestCase):
    def test_list(self):
        user = User.objects.create_user("bob", "bob@test.com", "pw")
        self.client.force_login(user)
        assert self.client.get("/api/invoices/").status_code == 200
```

Tenants created *inside* a test (e.g. with `provision_tenant`) disappear when the test's
transaction rolls back, since PostgreSQL DDL is transactional.

Plain unit tests that do not touch tenant tables can use `SimpleTestCase` or plain pytest
functions (see `apps/core/tests/test_routers.py`).

## 12.2 What the included suite proves

| Test | Guarantee |
|---|---|
| `TenantIsolationTests` | A tenant cannot see another tenant's rows, users or tokens. |
| `TenantRoutingTests` | Host-based routing, 404 for unknown hosts, 403 for suspended tenants, schema-prefixed cache keys, health probes on bare IPs. |
| `RouterTests` | Replica reads, primary pinning, routed apps, migration rules. |
| `test_databases.py` | Environment parsing for replicas and extra databases. |
| `ProvisionTenantTests` | Schema, domain and admin creation; duplicate protection. |
| `PublicOnlyAdminTests` | Platform models are hidden from tenant admins. |

CI (`.github/workflows/ci.yml`) runs lint, `makemigrations --check`, the tests against
PostgreSQL 18, and a production image build on every push and pull request.

Next: [13. Security](13-security.md)
