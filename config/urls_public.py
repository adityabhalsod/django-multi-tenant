"""URLs served on the PUBLIC hostname (PUBLIC_DOMAIN), e.g. http://localhost:8000/.

This is the platform site: marketing/landing page, sign-up flows and the
platform admin where staff manage tenants and domains.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path("", core_views.public_home, name="public-home"),
    path("admin/", admin.site.urls),
    path("health/live/", core_views.liveness, name="health-live"),
    path("health/ready/", core_views.readiness, name="health-ready"),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
