from django.contrib.admin.sites import site
from django.test import RequestFactory
from django_tenants.utils import schema_context

from apps.core.testing import TenantAPITestCase
from apps.tenants.models import Tenant
from apps.users.models import User


class PublicOnlyAdminTests(TenantAPITestCase):
    def test_tenant_admin_hidden_inside_tenants(self):
        request = RequestFactory().get("/admin/")
        request.user = User(is_superuser=True, is_staff=True, is_active=True)
        model_admin = site._registry[Tenant]
        self.assertFalse(model_admin.has_module_permission(request))
        self.assertFalse(model_admin.has_view_permission(request))
        with schema_context("public"):
            self.assertTrue(model_admin.has_module_permission(request))
