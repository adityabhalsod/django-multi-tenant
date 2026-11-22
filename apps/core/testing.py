"""Shared test helpers."""

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient


class TenantAPITestCase(TenantTestCase):
    """A test case running inside a throw-away tenant schema ("test").

    ``self.tenant`` is the tenant, ``self.client`` sends requests to its domain.
    """

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.name = "Test tenant"

    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
