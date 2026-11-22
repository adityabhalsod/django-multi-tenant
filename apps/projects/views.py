from django.db import connection
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.analytics.services import track

from .models import Project
from .serializers import ProjectSerializer
from .tasks import project_report


class ProjectViewSet(viewsets.ModelViewSet):
    """CRUD for the current tenant's projects (the tenant comes from the hostname)."""

    serializer_class = ProjectSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Project.objects.select_related("owner")

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        track("project.created", project_id=project.pk)

    @action(detail=False, methods=["post"])
    def report(self, request):
        """Queue a background job. The task runs in this tenant's schema."""
        result = project_report.delay()
        return Response({"task_id": result.id, "schema": connection.schema_name}, status=202)
