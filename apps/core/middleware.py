from __future__ import annotations

from django.http import HttpResponseForbidden
from django_tenants.middleware.main import TenantMainMiddleware

from apps.core.db import use_primary


class TenantMiddleware(TenantMainMiddleware):
    """Resolve the tenant from the request host and block inactive tenants.

    Extends django-tenants' middleware, which must stay at the very top of
    ``MIDDLEWARE``. After the parent class has switched the database
    connection to the tenant's schema, an inactive (suspended) tenant gets a
    403 instead of reaching any view.
    """

    def process_request(self, request):
        response = super().process_request(request)
        if response is not None:
            return response
        tenant = getattr(request, "tenant", None)
        if tenant is not None and not getattr(tenant, "is_active", True):
            return HttpResponseForbidden("This workspace is suspended.")
        return None


class PrimaryPinningMiddleware:
    """Send every query of an unsafe request (POST/PUT/PATCH/DELETE) to the primary."""

    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in self.SAFE_METHODS:
            return self.get_response(request)
        with use_primary():
            return self.get_response(request)


class HealthCheckMiddleware:
    """Answer health probes before tenant resolution.

    Load balancers and container orchestrators call ``/health/...`` on an IP
    address (``http://10.0.0.5:8000/health/live/``), which matches no tenant
    domain. Placed *above* ``TenantMiddleware``, this serves the probes for any
    host, using the public schema.
    """

    def __init__(self, get_response):
        from apps.core import views

        self.get_response = get_response
        self.routes = {"/health/live/": views.liveness, "/health/ready/": views.readiness}

    def __call__(self, request):
        view = self.routes.get(request.path_info)
        if view is not None:
            return view(request)
        return self.get_response(request)
