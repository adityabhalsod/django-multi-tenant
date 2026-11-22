from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django_tenants.utils import get_public_schema_name

from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


@never_cache
@require_GET
def liveness(request):
    """The process is up. Cheap; used by Docker/Kubernetes liveness probes."""
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def readiness(request):
    """Every configured database and the cache are reachable."""
    checks: dict[str, str] = {}
    healthy = True
    for alias in connections:
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute("SELECT 1")
            checks[f"db:{alias}"] = "ok"
        except Exception:
            logger.exception("Database %s is not reachable", alias)
            checks[f"db:{alias}"] = "error"
            healthy = False
    try:
        cache.set("health:ping", "pong", 5)
        checks["cache"] = "ok" if cache.get("health:ping") == "pong" else "error"
    except Exception:
        logger.exception("Cache is not reachable")
        checks["cache"] = "error"
    healthy = healthy and checks["cache"] == "ok"
    tenant = getattr(request, "tenant", None)
    return JsonResponse(
        {
            "status": "ok" if healthy else "error",
            "schema": getattr(tenant, "schema_name", None),
            "checks": checks,
        },
        status=200 if healthy else 503,
    )


def public_home(request):
    """Landing page of the platform. Lists tenants only in DEBUG (handy locally)."""
    domains = []
    if settings.DEBUG:
        tenants = (
            Tenant.objects.exclude(schema_name=get_public_schema_name())
            .filter(is_active=True)
            .prefetch_related("domains")
        )
        domains = [d for d in (t.get_primary_domain() for t in tenants) if d]
    return render(request, "public_home.html", {"domains": domains, "port": request.get_port()})


def tenant_home(request):
    return render(request, "tenant_home.html", {"tenant": request.tenant})
