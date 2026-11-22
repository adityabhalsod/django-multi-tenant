"""URLs served on TENANT hostnames, e.g. http://acme.localhost:8000/."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

from apps.core import views as core_views

urlpatterns = [
    path("", core_views.tenant_home, name="tenant-home"),
    path("admin/", admin.site.urls),
    path("health/live/", core_views.liveness, name="health-live"),
    path("health/ready/", core_views.readiness, name="health-ready"),
    path("api/auth/token/", obtain_auth_token, name="api-token"),
    path("api/", include("apps.projects.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
