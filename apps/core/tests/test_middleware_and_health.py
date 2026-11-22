from django.core.cache import cache
from django.db import connection
from django.test import Client
from django_tenants.utils import schema_context

from apps.core.testing import TenantAPITestCase


class TenantRoutingTests(TenantAPITestCase):
    def test_readiness_probe(self):
        response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 200)
        # Probes are answered before tenant resolution, on the public schema.
        self.assertEqual(response.json()["schema"], None)

    def test_unknown_host_is_404(self):
        self.assertEqual(Client().get("/", HTTP_HOST="tenant.test.com").status_code, 200)
        self.assertEqual(Client().get("/", HTTP_HOST="nope.test.com").status_code, 404)

    def test_health_probe_works_on_bare_ip(self):
        response = Client().get("/health/live/", HTTP_HOST="10.1.2.3")
        self.assertEqual(response.status_code, 200)

    def test_inactive_tenant_is_blocked(self):
        self.tenant.is_active = False
        self.tenant.save()
        try:
            self.assertEqual(self.client.get("/").status_code, 403)
        finally:
            self.tenant.is_active = True
            self.tenant.save()

    def test_cache_keys_are_namespaced_by_schema(self):
        cache.set("greeting", "hello from test")
        with schema_context("public"):
            self.assertIsNone(cache.get("greeting"))
            cache.set("greeting", "hello from public")
        self.assertEqual(cache.get("greeting"), "hello from test")
        self.assertEqual(connection.schema_name, "test")
