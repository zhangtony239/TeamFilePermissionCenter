from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    AuditLogViewSet,
    AuthViewSet,
    BackupViewSet,
    FileEntryViewSet,
    ProjectAwardViewSet,
    ProjectEventViewSet,
    ProjectMembershipViewSet,
    ProjectTaskViewSet,
    ProjectViewSet,
    RecycleBinViewSet,
    UserAdminViewSet,
)

router = DefaultRouter()
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r"projects", ProjectViewSet, basename="projects")
router.register(r"memberships", ProjectMembershipViewSet, basename="memberships")
router.register(r"awards", ProjectAwardViewSet, basename="awards")
router.register(r"events", ProjectEventViewSet, basename="events")
router.register(r"tasks", ProjectTaskViewSet, basename="tasks")
router.register(r"users", UserAdminViewSet, basename="users")
router.register(r"audit", AuditLogViewSet, basename="audit")
router.register(r"recycle", RecycleBinViewSet, basename="recycle")
router.register(r"files", FileEntryViewSet, basename="files")
router.register(r"backups", BackupViewSet, basename="backups")

urlpatterns = [
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("", include(router.urls)),
]
