import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import schema_context

from apps.core.testing import TenantAPITestCase
from apps.tenants.models import Domain, Tenant
from apps.tenants.services import (
    ProvisioningError,
    TenantAdmin,
    normalise_schema_name,
    provision_tenant,
    validate_schema_name,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Acme Corp!", "acme_corp"), ("  Globex  ", "globex"), ("42 Inc", "t_42_inc")],
)
def test_normalise_schema_name(raw, expected):
    assert normalise_schema_name(raw) == expected


@pytest.mark.parametrize("name", ["public", "pg_catalog", "pg_anything", "Bad-Name", ""])
def test_validate_rejects(name):
    with pytest.raises(ProvisioningError):
        validate_schema_name(name)


class ProvisionTenantTests(TenantAPITestCase):
    # Schemas created here vanish when the test transaction rolls back:
    # PostgreSQL DDL is transactional.

    def test_provision_creates_schema_domain_and_admin(self):
        tenant = provision_tenant(
            name="Initech",
            domain="Initech.Test.com",
            admin=TenantAdmin("boss", "boss@initech.test", "s3cret-pass"),
        )
        self.assertTrue(Tenant.objects.filter(schema_name="initech").exists())
        self.assertEqual(Domain.objects.get(tenant=tenant).domain, "initech.test.com")
        with schema_context("initech"):
            self.assertTrue(get_user_model().objects.filter(username="boss").exists())
        # The admin exists only inside that tenant.
        self.assertFalse(get_user_model().objects.filter(username="boss").exists())
        self.assertEqual(connection.schema_name, "test")

    def test_duplicate_domain_rejected(self):
        with pytest.raises(ProvisioningError, match="Domain"):
            provision_tenant(name="Other", domain="tenant.test.com")
        self.assertFalse(Tenant.objects.filter(schema_name="other").exists())
