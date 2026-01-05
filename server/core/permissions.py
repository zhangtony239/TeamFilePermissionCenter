from __future__ import annotations

from rest_framework.permissions import BasePermission

from .models import ProjectMembership


class IsSystemAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsProjectAdminOrSystemAdmin(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        project_id = getattr(obj, "id", None)
        if project_id is None and hasattr(obj, "project_id"):
            project_id = obj.project_id
        if project_id is None:
            return False
        return ProjectMembership.objects.filter(
            project_id=project_id,
            user_id=request.user.id,
            role=ProjectMembership.Role.PROJECT_ADMIN,
            is_active=True,
        ).exists()


class IsProjectMemberOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        project_id = getattr(obj, "id", None)
        if project_id is None and hasattr(obj, "project_id"):
            project_id = obj.project_id
        if project_id is None:
            return False
        return ProjectMembership.objects.filter(project_id=project_id, user_id=request.user.id, is_active=True).exists()
