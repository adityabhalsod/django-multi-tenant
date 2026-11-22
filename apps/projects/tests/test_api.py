from django.contrib.auth import get_user_model
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context
from rest_framework.authtoken.models import Token

from apps.core.testing import TenantAPITestCase
from apps.projects.models import Project
from apps.tenants.services import provision_tenant


class ProjectAPITests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user("alice", "alice@test.com", "pw-12345")
        token = Token.objects.create(user=self.user)
        self.auth = {"HTTP_AUTHORIZATION": f"Token {token.key}"}

    def test_requires_authentication(self):
        self.assertIn(self.client.get("/api/projects/").status_code, (401, 403))

    def test_create_and_list(self):
        response = self.client.post("/api/projects/", {"name": "Rocket"}, **self.auth)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["owner"], "alice")
        listing = self.client.get("/api/projects/", **self.auth).json()
        self.assertEqual([p["name"] for p in listing["results"]], ["Rocket"])

    def test_report_task_runs_in_tenant_schema(self):
        Project.objects.create(name="One", owner=self.user)
        response = self.client.post("/api/projects/report/", **self.auth)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["schema"], "test")


class TenantIsolationTests(TenantAPITestCase):
    """The core promise: one tenant can never see another tenant's data."""

    def test_data_and_users_are_isolated(self):
        user = get_user_model().objects.create_user("alice", "alice@test.com", "pw-12345")
        Project.objects.create(name="Secret plan", owner=user)

        other = provision_tenant(name="Globex", domain="globex.test.com")
        with schema_context(other.schema_name):
            self.assertEqual(Project.objects.count(), 0)
            self.assertFalse(get_user_model().objects.filter(username="alice").exists())
            bob = get_user_model().objects.create_user("bob", "bob@test.com", "pw-12345")
            token = Token.objects.create(user=bob)

        # Bob's token is unknown on the first tenant...
        response = self.client.get("/api/projects/", HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(response.status_code, 401)
        # ...and on his own tenant he sees an empty list.
        response = TenantClient(other).get(
            "/api/projects/", HTTP_AUTHORIZATION=f"Token {token.key}"
        )
        self.assertEqual(response.json()["count"], 0)
