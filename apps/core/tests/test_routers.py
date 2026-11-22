from unittest import mock

from django.test import SimpleTestCase, override_settings

from apps.analytics.models import Event
from apps.core.db import is_primary_pinned, use_primary
from apps.projects.models import Project
from apps.tenants.models import Tenant
from config.db_routers import MultiDatabaseRouter

ROUTES = {"analytics": "analytics"}


@override_settings(DATABASE_REPLICAS=["replica_1"], DATABASE_APP_ROUTES=ROUTES)
class RouterTests(SimpleTestCase):
    def setUp(self):
        self.router = MultiDatabaseRouter()
        patcher = mock.patch.object(MultiDatabaseRouter, "_sync_tenant")
        self.sync = patcher.start()
        self.addCleanup(patcher.stop)

    def test_tenant_reads_go_to_replica_and_sync_schema(self):
        self.assertEqual(self.router.db_for_read(Project), "replica_1")
        self.sync.assert_called_once_with("replica_1")

    def test_pinned_reads_go_to_primary(self):
        with use_primary():
            self.assertTrue(is_primary_pinned())
            self.assertEqual(self.router.db_for_read(Project), "default")
        self.assertFalse(is_primary_pinned())

    def test_tenant_metadata_always_from_primary(self):
        self.assertEqual(self.router.db_for_read(Tenant), "default")

    def test_writes_go_to_primary(self):
        self.assertEqual(self.router.db_for_write(Project), "default")

    def test_routed_app(self):
        self.assertEqual(self.router.db_for_read(Event), "analytics")
        self.assertEqual(self.router.db_for_write(Event), "analytics")

    def test_migrations(self):
        allow = self.router.allow_migrate
        self.assertFalse(allow("replica_1", "projects"))
        self.assertTrue(allow("analytics", "analytics"))
        self.assertFalse(allow("default", "analytics"))
        self.assertFalse(allow("analytics", "projects"))
        self.assertIsNone(allow("default", "projects"))  # TenantSyncRouter decides


@override_settings(DATABASE_REPLICAS=[], DATABASE_APP_ROUTES={})
class NoReplicaRouterTests(SimpleTestCase):
    def test_everything_on_primary(self):
        router = MultiDatabaseRouter()
        self.assertEqual(router.db_for_read(Project), "default")
        self.assertEqual(router.db_for_read(Event), "default")
        self.assertIsNone(router.allow_migrate("default", "analytics"))
