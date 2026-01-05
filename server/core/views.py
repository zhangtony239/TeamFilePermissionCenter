from __future__ import annotations

from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.db.models import Count
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AuditLog, FileACL, FileEntry, Project, ProjectAward, ProjectEvent, ProjectMembership, ProjectTask, RecycleBinItem
from .permissions import IsProjectAdminOrSystemAdmin, IsProjectMemberOrAdmin, IsSystemAdmin
from .storage import presigned_download_url, presigned_preview_url, put_object
from .serializers import (
    AuditLogSerializer,
    ProjectAwardSerializer,
    ProjectEventSerializer,
    ProjectMembershipSerializer,
    ProjectSerializer,
    ProjectTaskSerializer,
    RecycleBinItemSerializer,
    FileDirNodeSerializer,
    FileEntrySerializer,
    FileACLSerializer,
    UserAdminSerializer,
    UserBriefSerializer,
)

User = get_user_model()


def _require_project_member(request, *, project_id: int) -> None:
    if request.user.is_staff:
        return
    if not ProjectMembership.objects.filter(
        project_id=project_id,
        user_id=request.user.id,
        is_active=True,
    ).exists():
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("无权限访问该项目")


def _require_project_admin(request, *, project_id: int) -> None:
    if request.user.is_staff:
        return
    if not ProjectMembership.objects.filter(
        project_id=project_id,
        user_id=request.user.id,
        role=ProjectMembership.Role.PROJECT_ADMIN,
        is_active=True,
    ).exists():
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("需要项目管理员或系统管理员权限")


def _client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def write_audit(
    *,
    request,
    action: str,
    project: Project | None = None,
    path: str = "",
    result: str = "OK",
    reason: str = "",
):
    AuditLog.objects.create(
        project=project,
        actor=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
        action=action,
        path=path,
        result=result,
        reason=reason,
        ip=_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "") or "")[:256],
    )


def _jsonify_value(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _snapshot_project(project: Project) -> dict:
    memberships = (
        ProjectMembership.objects.filter(project=project)
        .select_related("user")
        .order_by("id")
    )
    awards = ProjectAward.objects.filter(project=project).order_by("id")
    events = ProjectEvent.objects.filter(project=project).order_by("id")
    tasks = ProjectTask.objects.filter(project=project).order_by("id")

    return {
        "project": {
            "id": project.id,
            "code": project.code,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "start_date": _jsonify_value(project.start_date),
            "end_date": _jsonify_value(project.end_date),
            "competition_stage": project.competition_stage,
            "progress_percent": project.progress_percent,
            "created_at": _jsonify_value(project.created_at),
        },
        "memberships": [
            {
                "user_id": m.user_id,
                "role": m.role,
                "is_active": m.is_active,
                "joined_at": _jsonify_value(m.joined_at),
            }
            for m in memberships
        ],
        "awards": [
            {
                "stage": a.stage,
                "title": a.title,
                "level": a.level,
                "description": a.description,
                "awarded_at": _jsonify_value(a.awarded_at),
                "created_at": _jsonify_value(a.created_at),
            }
            for a in awards
        ],
        "events": [
            {
                "title": e.title,
                "start_at": _jsonify_value(e.start_at),
                "end_at": _jsonify_value(e.end_at),
                "stage": e.stage,
                "description": e.description,
                "created_at": _jsonify_value(e.created_at),
            }
            for e in events
        ],
        "tasks": [
            {
                "title": t.title,
                "status": t.status,
                "start_date": _jsonify_value(t.start_date),
                "end_date": _jsonify_value(t.end_date),
                "progress_percent": t.progress_percent,
                "description": t.description,
                "sort_order": t.sort_order,
                "created_at": _jsonify_value(t.created_at),
            }
            for t in tasks
        ],
    }


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        return Response({"ok": True, "data": UserBriefSerializer(request.user).data})


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Project.objects.all().annotate(members_count=Count("memberships", distinct=True)).order_by("-created_at")
        if self.request.user.is_staff:
            return qs
        return qs.filter(memberships__user_id=self.request.user.id, memberships__is_active=True).distinct()

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update"}:
            return [IsAuthenticated(), IsProjectAdminOrSystemAdmin()]
        if self.action in {"destroy"}:
            return [IsAuthenticated(), IsSystemAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        project = serializer.save()
        # 初始化默认目录，便于文件中心直接可用
        FileEntry.objects.get_or_create(project=project, parent=None, name="文档", is_dir=True)
        FileEntry.objects.get_or_create(project=project, parent=None, name="素材", is_dir=True)

        # 默认 ACL：root（target_entry=None）
        # ProjectAdmin：全权限；Member：默认只读
        FileACL.objects.get_or_create(
            project=project,
            target_entry=None,
            subject_kind=FileACL.SubjectKind.ROLE,
            subject_role=ProjectMembership.Role.PROJECT_ADMIN,
            defaults={
                "effect": FileACL.Effect.ALLOW,
                "actions": [
                    "LIST",
                    "PREVIEW",
                    "DOWNLOAD",
                    "UPLOAD",
                    "UPDATE",
                    "MOVE",
                    "DELETE",
                    "RESTORE",
                    "ACL_ADMIN",
                ],
                "inherit": True,
                "created_by": self.request.user,
            },
        )
        FileACL.objects.get_or_create(
            project=project,
            target_entry=None,
            subject_kind=FileACL.SubjectKind.ROLE,
            subject_role=ProjectMembership.Role.MEMBER,
            defaults={
                "effect": FileACL.Effect.ALLOW,
                "actions": ["LIST", "PREVIEW", "DOWNLOAD"],
                "inherit": True,
                "created_by": self.request.user,
            },
        )
        write_audit(request=self.request, action="PROJECT_CREATE", project=project)

    def perform_update(self, serializer):
        project = serializer.save()
        write_audit(request=self.request, action="PROJECT_UPDATE", project=project)

    def perform_destroy(self, instance):
        snapshot = _snapshot_project(instance)
        RecycleBinItem.objects.create(
            object_type=RecycleBinItem.ObjectType.PROJECT,
            object_id=instance.id,
            object_code=instance.code,
            object_name=instance.name,
            payload=snapshot,
            deleted_by=self.request.user,
        )
        write_audit(request=self.request, action="PROJECT_DELETE_TO_RECYCLE", project=instance, path=str(instance.id))
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, pk=None):
        project = self.get_object()
        self.check_object_permissions(request, project)
        memberships = (
            ProjectMembership.objects.filter(project=project)
            .select_related("user")
            .order_by("-is_active", "user__username")
        )
        return Response({"ok": True, "data": ProjectMembershipSerializer(memberships, many=True).data})

    @members.mapping.post
    def members_add(self, request, pk=None):
        project = self.get_object()
        IsProjectAdminOrSystemAdmin().has_object_permission(request, self, project) or self.permission_denied(request)

        serializer = ProjectMembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data["user_id"]
        role = serializer.validated_data.get("role", ProjectMembership.Role.MEMBER)
        user = User.objects.get(id=user_id)

        membership, _created = ProjectMembership.objects.update_or_create(
            project=project,
            user=user,
            defaults={"role": role, "is_active": True},
        )
        write_audit(request=request, action="MEMBER_ADD", project=project, path=str(user_id))
        return Response({"ok": True, "data": ProjectMembershipSerializer(membership).data}, status=status.HTTP_201_CREATED)


class ProjectMembershipViewSet(
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ProjectMembership.objects.select_related("user", "project")
    serializer_class = ProjectMembershipSerializer
    permission_classes = [IsAuthenticated, IsProjectAdminOrSystemAdmin]

    def perform_update(self, serializer):
        membership = serializer.save()
        write_audit(request=self.request, action="MEMBER_UPDATE", project=membership.project, path=str(membership.id))

    def perform_destroy(self, instance):
        write_audit(request=self.request, action="MEMBER_REMOVE", project=instance.project, path=str(instance.id))
        super().perform_destroy(instance)


class ProjectAwardViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectAwardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ProjectAward.objects.select_related("project").order_by("-awarded_at", "-created_at")
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        if self.request.user.is_staff:
            return qs
        return qs.filter(project__memberships__user_id=self.request.user.id, project__memberships__is_active=True).distinct()

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsProjectAdminOrSystemAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        award = serializer.save()
        write_audit(request=self.request, action="AWARD_CREATE", project=award.project, path=str(award.id))

    def perform_update(self, serializer):
        award = serializer.save()
        write_audit(request=self.request, action="AWARD_UPDATE", project=award.project, path=str(award.id))

    def perform_destroy(self, instance):
        write_audit(request=self.request, action="AWARD_DELETE", project=instance.project, path=str(instance.id))
        super().perform_destroy(instance)


class FileEntryViewSet(viewsets.GenericViewSet):
    queryset = FileEntry.objects.select_related("project", "parent")
    serializer_class = FileEntrySerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = super().get_queryset().order_by("is_dir", "name")
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        if self.request.user.is_staff:
            return qs
        return qs.filter(project__memberships__user_id=self.request.user.id, project__memberships__is_active=True).distinct()

    def _is_project_admin(self, *, request, project_id: int) -> bool:
        if request.user.is_staff:
            return True
        return ProjectMembership.objects.filter(
            project_id=project_id,
            user_id=request.user.id,
            role=ProjectMembership.Role.PROJECT_ADMIN,
            is_active=True,
        ).exists()

    def _get_member_role(self, *, request, project_id: int) -> str:
        if request.user.is_staff:
            return ProjectMembership.Role.ADMIN
        m = ProjectMembership.objects.filter(
            project_id=project_id,
            user_id=request.user.id,
            is_active=True,
        ).first()
        return (m.role if m else ProjectMembership.Role.MEMBER) or ProjectMembership.Role.MEMBER

    def _get_ancestor_ids(self, *, entry: FileEntry) -> list[int]:
        # 只沿 parent 链上溯（不含 entry 自身）
        out: list[int] = []
        cur = entry.parent_id
        while cur is not None:
            out.append(cur)
            cur = FileEntry.objects.filter(id=cur).values_list("parent_id", flat=True).first()
        out.reverse()
        return out

    def _eval_acl(
        self,
        *,
        action: str,
        target_id: int | None,
        chain_ids: list[int | None],
        acls_by_target: dict[int | None, list[FileACL]],
    ) -> bool:
        # 优先级：显式 DENY > 显式 ALLOW > 继承 DENY > 继承 ALLOW > 默认拒绝
        direct = acls_by_target.get(target_id, [])
        for a in direct:
            if action in (a.actions or []) and a.effect == FileACL.Effect.DENY:
                return False
        for a in direct:
            if action in (a.actions or []) and a.effect == FileACL.Effect.ALLOW:
                return True

        ancestors = [i for i in chain_ids if i != target_id]
        for anc in reversed(ancestors):
            for a in acls_by_target.get(anc, []):
                if not a.inherit:
                    continue
                if action in (a.actions or []) and a.effect == FileACL.Effect.DENY:
                    return False
        for anc in reversed(ancestors):
            for a in acls_by_target.get(anc, []):
                if not a.inherit:
                    continue
                if action in (a.actions or []) and a.effect == FileACL.Effect.ALLOW:
                    return True
        return False

    def _load_subject_acls(self, *, project_id: int, role: str, user_id: int, target_ids: list[int | None]):
        if not target_ids:
            target_ids = [None]
        qs = FileACL.objects.filter(project_id=project_id)

        q_targets = Q(target_entry_id__in=[i for i in target_ids if i is not None]) | Q(target_entry__isnull=True)
        qs = qs.filter(q_targets)

        qs = qs.filter(
            Q(subject_kind=FileACL.SubjectKind.USER, subject_user_id=user_id)
            | Q(subject_kind=FileACL.SubjectKind.ROLE, subject_role=role)
        )
        by: dict[int | None, list[FileACL]] = {}
        for a in qs.order_by("id"):
            by.setdefault(a.target_entry_id, []).append(a)
        return by

    def _require_acl(self, *, request, entry: FileEntry, action: str) -> None:
        if request.user.is_staff or self._is_project_admin(request=request, project_id=entry.project_id):
            return
        role = self._get_member_role(request=request, project_id=entry.project_id)
        chain: list[int | None] = [None]
        chain.extend(self._get_ancestor_ids(entry=entry))
        chain.append(entry.id)
        acls_by_target = self._load_subject_acls(
            project_id=entry.project_id,
            role=role,
            user_id=request.user.id,
            target_ids=chain,
        )
        allowed = self._eval_acl(action=action, target_id=entry.id, chain_ids=chain, acls_by_target=acls_by_target)
        if not allowed:
            from rest_framework.exceptions import NotFound

            raise NotFound("资源不存在")

    def _parse_include_personal(self, request) -> bool:
        v = request.query_params.get("include_personal")
        return v in {"1", "true", "True", "yes", "on"}

    def _can_access_personal_entry(self, *, request, entry: FileEntry) -> bool:
        if not entry.is_personal:
            return True
        if request.user.is_staff:
            return True
        if self._is_project_admin(request=request, project_id=entry.project_id):
            return True
        return entry.owner_user_id == request.user.id

    def _apply_personal_filter(self, *, qs, request, project_id: int, include_personal: bool):
        if not include_personal:
            return qs.filter(is_personal=False)
        if request.user.is_staff or self._is_project_admin(request=request, project_id=project_id):
            return qs
        return qs.filter(Q(is_personal=False) | Q(owner_user_id=request.user.id))

    def _get_parent_or_404(self, *, request, project_id: int, parent_id: int, include_personal: bool) -> FileEntry:
        parent = FileEntry.objects.filter(id=parent_id, project_id=project_id).first()
        if not parent or parent.deleted_at is not None or not parent.is_dir:
            from rest_framework.exceptions import NotFound

            raise NotFound("目录不存在")
        if not include_personal and parent.is_personal:
            from rest_framework.exceptions import NotFound

            raise NotFound("目录不存在")
        if parent.is_personal and not self._can_access_personal_entry(request=request, entry=parent):
            from rest_framework.exceptions import NotFound

            raise NotFound("目录不存在")

        # ACL：需要对目录具备 LIST 权限（否则不允许进入该目录）
        self._require_acl(request=request, entry=parent, action=FileACL.Action.LIST)
        return parent

    def _collect_subtree_ids(self, *, root_id: int) -> list[int]:
        # 迭代 BFS：收集 root 及其所有后代
        ids: list[int] = [root_id]
        frontier: list[int] = [root_id]
        while frontier:
            children = list(
                FileEntry.objects.filter(parent_id__in=frontier).values_list("id", flat=True)
            )
            if not children:
                break
            ids.extend(children)
            frontier = children
        # 去重保持稳定
        seen: set[int] = set()
        out: list[int] = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out

    def _validate_entry_name(self, name: str) -> str:
        s = (name or "").strip()
        if not s:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": "名称不能为空"})
        if len(s) > 255:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": "名称过长"})
        if "/" in s or "\\" in s:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": "名称不能包含 / 或 \\"})
        return s

    def _assert_sibling_name_available(
        self,
        *,
        project_id: int,
        parent_id: int | None,
        name: str,
        exclude_ids: list[int] | None = None,
    ) -> None:
        qs = FileEntry.objects.filter(
            project_id=project_id,
            parent_id=parent_id,
            name=name,
            deleted_at__isnull=True,
        )
        if exclude_ids:
            qs = qs.exclude(id__in=exclude_ids)
        if qs.exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": "同一目录下已存在同名条目"})

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        project_id = request.query_params.get("project")
        if not project_id:
            return Response({"detail": "project 参数必填"}, status=status.HTTP_400_BAD_REQUEST)
        _require_project_member(request, project_id=int(project_id))

        include_personal = self._parse_include_personal(request)

        dirs = FileEntry.objects.filter(project_id=project_id, is_dir=True, deleted_at__isnull=True).order_by("name")
        dirs = self._apply_personal_filter(qs=dirs, request=request, project_id=int(project_id), include_personal=include_personal)

        # ACL：过滤掉没有 LIST 权限的目录
        if request.user.is_staff or self._is_project_admin(request=request, project_id=int(project_id)):
            return Response(FileDirNodeSerializer(dirs, many=True).data)

        role = self._get_member_role(request=request, project_id=int(project_id))
        # root(None) + 所有目录 id
        target_ids: list[int | None] = [None]
        dir_list = list(dirs)
        target_ids.extend([d.id for d in dir_list])
        acls_by_target = self._load_subject_acls(
            project_id=int(project_id),
            role=role,
            user_id=request.user.id,
            target_ids=target_ids,
        )

        allowed_dirs: list[FileEntry] = []
        for d in dir_list:
            chain: list[int | None] = [None]
            chain.extend(self._get_ancestor_ids(entry=d))
            chain.append(d.id)
            if self._eval_acl(
                action=FileACL.Action.LIST,
                target_id=d.id,
                chain_ids=chain,
                acls_by_target=acls_by_target,
            ):
                allowed_dirs.append(d)

        return Response(FileDirNodeSerializer(allowed_dirs, many=True).data)

    def list(self, request):
        project_id = request.query_params.get("project")
        folder = request.query_params.get("folder", "root")
        if not project_id:
            return Response({"detail": "project 参数必填"}, status=status.HTTP_400_BAD_REQUEST)
        _require_project_member(request, project_id=int(project_id))

        include_personal = self._parse_include_personal(request)

        if folder == "root" or folder == "":
            parent_id = None
        else:
            try:
                parent_id = int(folder)
            except Exception:
                return Response({"detail": "folder 参数非法"}, status=status.HTTP_400_BAD_REQUEST)
            # 不允许访问已删除/不存在/非目录的 folder
            self._get_parent_or_404(request=request, project_id=int(project_id), parent_id=parent_id, include_personal=include_personal)

        qs = FileEntry.objects.filter(
            project_id=project_id,
            parent_id=parent_id,
            deleted_at__isnull=True,
        ).order_by("-is_dir", "name")
        qs = self._apply_personal_filter(qs=qs, request=request, project_id=int(project_id), include_personal=include_personal)

        if request.user.is_staff or self._is_project_admin(request=request, project_id=int(project_id)):
            return Response(FileEntrySerializer(qs, many=True).data)

        role = self._get_member_role(request=request, project_id=int(project_id))
        items = list(qs)
        target_ids: list[int | None] = [None]
        target_ids.extend([x.id for x in items])
        acls_by_target = self._load_subject_acls(
            project_id=int(project_id),
            role=role,
            user_id=request.user.id,
            target_ids=target_ids,
        )

        # parent_chain：同一目录下的子项共享上级链
        parent_chain: list[int | None] = [None]
        if parent_id is not None:
            parent_entry = FileEntry.objects.filter(id=parent_id, project_id=int(project_id)).first()
            if parent_entry:
                parent_chain.extend(self._get_ancestor_ids(entry=parent_entry))
                parent_chain.append(parent_entry.id)

        allowed: list[FileEntry] = []
        for it in items:
            chain = list(parent_chain)
            chain.append(it.id)
            if self._eval_acl(
                action=FileACL.Action.LIST,
                target_id=it.id,
                chain_ids=chain,
                acls_by_target=acls_by_target,
            ):
                allowed.append(it)

        return Response(FileEntrySerializer(allowed, many=True).data)

    @action(detail=False, methods=["get"], url_path="recycle")
    def recycle(self, request):
        project_id = request.query_params.get("project")
        if not project_id:
            return Response({"detail": "project 参数必填"}, status=status.HTTP_400_BAD_REQUEST)
        _require_project_member(request, project_id=int(project_id))

        include_personal = self._parse_include_personal(request)

        qs = FileEntry.objects.filter(project_id=project_id, deleted_at__isnull=False).order_by("-deleted_at", "name")
        qs = self._apply_personal_filter(qs=qs, request=request, project_id=int(project_id), include_personal=include_personal)

        if request.user.is_staff or self._is_project_admin(request=request, project_id=int(project_id)):
            return Response(FileEntrySerializer(qs, many=True).data)

        role = self._get_member_role(request=request, project_id=int(project_id))
        items = list(qs)
        target_ids: list[int | None] = [None]
        target_ids.extend([x.id for x in items])
        acls_by_target = self._load_subject_acls(
            project_id=int(project_id),
            role=role,
            user_id=request.user.id,
            target_ids=target_ids,
        )

        allowed: list[FileEntry] = []
        for it in items:
            chain: list[int | None] = [None]
            chain.extend(self._get_ancestor_ids(entry=it))
            chain.append(it.id)
            if self._eval_acl(
                action=FileACL.Action.LIST,
                target_id=it.id,
                chain_ids=chain,
                acls_by_target=acls_by_target,
            ):
                allowed.append(it)

        return Response(FileEntrySerializer(allowed, many=True).data)

    @action(detail=False, methods=["post"], url_path="folders")
    def create_folder(self, request):
        project_id = request.data.get("project")
        parent = request.data.get("parent")
        name = (request.data.get("name") or "").strip()

        if not project_id or not name:
            return Response({"detail": "project/name 参数必填"}, status=status.HTTP_400_BAD_REQUEST)
        _require_project_admin(request, project_id=int(project_id))

        if parent in ("", None, "root"):
            parent_id = None
        else:
            try:
                parent_id = int(parent)
            except Exception:
                return Response({"detail": "parent 参数非法"}, status=status.HTTP_400_BAD_REQUEST)
            self._get_parent_or_404(request=request, project_id=int(project_id), parent_id=parent_id, include_personal=True)

        from rest_framework.exceptions import ValidationError

        try:
            self._assert_sibling_name_available(
                project_id=int(project_id),
                parent_id=parent_id,
                name=name,
            )
        except ValidationError as e:
            msg = e.detail.get("detail") if isinstance(e.detail, dict) else str(e.detail)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        entry = FileEntry.objects.create(
            project_id=project_id,
            parent_id=parent_id,
            name=name,
            is_dir=True,
            created_by=request.user,
            updated_by=request.user,
        )
        write_audit(request=request, action="FILE_FOLDER_CREATE", project=entry.project, path=str(entry.id))
        return Response(FileEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        project_id = request.data.get("project")
        parent = request.data.get("parent")
        up = request.FILES.get("file")

        if not project_id or up is None:
            return Response({"detail": "project/file 参数必填"}, status=status.HTTP_400_BAD_REQUEST)

        _require_project_admin(request, project_id=int(project_id))

        if parent in ("", None, "root"):
            parent_id = None
        else:
            try:
                parent_id = int(parent)
            except Exception:
                return Response({"detail": "parent 参数非法"}, status=status.HTTP_400_BAD_REQUEST)
            self._get_parent_or_404(request=request, project_id=int(project_id), parent_id=parent_id, include_personal=True)

        filename = getattr(up, "name", "file")
        # 简单去掉路径前缀，避免注入
        filename = filename.split("/")[-1].split("\\")[-1]
        if not filename:
            filename = "file"

        # 同目录同名校验
        from rest_framework.exceptions import ValidationError

        try:
            self._assert_sibling_name_available(
                project_id=int(project_id),
                parent_id=parent_id,
                name=filename,
            )
        except ValidationError as e:
            msg = e.detail.get("detail") if isinstance(e.detail, dict) else str(e.detail)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        import uuid

        object_name = f"p{project_id}/{uuid.uuid4().hex}/{filename}"
        storage_key = put_object(
            object_name=object_name,
            data=up.file,
            length=int(getattr(up, "size", 0) or 0),
            content_type=getattr(up, "content_type", None),
        )

        entry = FileEntry.objects.create(
            project_id=project_id,
            parent_id=parent_id,
            name=filename,
            is_dir=False,
            size_bytes=int(getattr(up, "size", 0) or 0),
            mime_type=(getattr(up, "content_type", "") or "")[:128],
            storage_key=storage_key,
            created_by=request.user,
            updated_by=request.user,
        )
        write_audit(request=request, action="FILE_UPLOAD", project=entry.project, path=str(entry.id))
        return Response(FileEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        entry = self.get_object()
        _require_project_member(request, project_id=entry.project_id)
        if entry.is_personal and not self._can_access_personal_entry(request=request, entry=entry):
            from rest_framework.exceptions import NotFound

            raise NotFound("文件不存在")
        if entry.is_dir:
            return Response({"detail": "目录不支持下载"}, status=status.HTTP_400_BAD_REQUEST)
        if entry.deleted_at is not None:
            return Response({"detail": "回收站文件不支持下载"}, status=status.HTTP_400_BAD_REQUEST)
        if not entry.storage_key:
            return Response({"detail": "文件缺少存储地址"}, status=status.HTTP_400_BAD_REQUEST)

        self._require_acl(request=request, entry=entry, action=FileACL.Action.DOWNLOAD)

        try:
            url = presigned_download_url(object_name=entry.storage_key, filename=entry.name)
        except Exception as e:
            return Response({"detail": f"生成下载链接失败：{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        write_audit(request=request, action="FILE_DOWNLOAD_URL", project=entry.project, path=str(entry.id))
        return Response({"ok": True, "url": url})

    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request, pk=None):
        entry = self.get_object()
        _require_project_member(request, project_id=entry.project_id)
        if entry.is_personal and not self._can_access_personal_entry(request=request, entry=entry):
            from rest_framework.exceptions import NotFound

            raise NotFound("文件不存在")
        if entry.is_dir:
            return Response({"detail": "目录不支持预览"}, status=status.HTTP_400_BAD_REQUEST)
        if entry.deleted_at is not None:
            return Response({"detail": "回收站文件不支持预览"}, status=status.HTTP_400_BAD_REQUEST)
        if not entry.storage_key:
            return Response({"detail": "文件缺少存储地址"}, status=status.HTTP_400_BAD_REQUEST)

        self._require_acl(request=request, entry=entry, action=FileACL.Action.PREVIEW)

        try:
            url = presigned_preview_url(
                object_name=entry.storage_key,
                filename=entry.name,
                content_type=entry.mime_type or None,
            )
        except Exception as e:
            return Response({"detail": f"生成预览链接失败：{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        write_audit(request=request, action="FILE_PREVIEW_URL", project=entry.project, path=str(entry.id))
        return Response({"ok": True, "url": url})

    @action(detail=True, methods=["post"], url_path="personalize")
    def personalize(self, request, pk=None):
        entry = self.get_object()
        _require_project_member(request, project_id=entry.project_id)
        if entry.deleted_at is not None:
            return Response({"detail": "回收站条目不支持设置个人区"}, status=status.HTTP_400_BAD_REQUEST)

        is_personal = bool(request.data.get("is_personal"))
        owner_user_id = request.data.get("owner_user_id")

        # 权限：系统管理员/项目管理员可设置任意条目；普通成员仅能设置自己创建/拥有的条目
        is_admin = self._is_project_admin(request=request, project_id=entry.project_id)
        if not is_admin:
            allowed = (entry.owner_user_id == request.user.id) or (entry.created_by_id == request.user.id)
            if not allowed:
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("无权限设置该条目的个人区")

        if is_personal:
            if owner_user_id in (None, "", 0, "0"):
                owner_id = request.user.id
            else:
                try:
                    owner_id = int(owner_user_id)
                except Exception:
                    return Response({"detail": "owner_user_id 参数非法"}, status=status.HTTP_400_BAD_REQUEST)
                if not is_admin and owner_id != request.user.id:
                    return Response({"detail": "只能设置为自己的个人区"}, status=status.HTTP_403_FORBIDDEN)

            entry.is_personal = True
            entry.owner_user_id = owner_id
        else:
            # 取消个人区：普通成员只能取消自己的个人区
            if not is_admin and entry.owner_user_id != request.user.id:
                return Response({"detail": "只能取消自己的个人区"}, status=status.HTTP_403_FORBIDDEN)
            entry.is_personal = False
            entry.owner_user = None

        entry.updated_by = request.user
        entry.save(update_fields=["is_personal", "owner_user", "updated_by", "updated_at"])
        write_audit(request=request, action="FILE_PERSONALIZE", project=entry.project, path=str(entry.id))
        return Response({"ok": True, "data": FileEntrySerializer(entry).data})

    @action(detail=False, methods=["get"], url_path="acl")
    def acl_list(self, request):
        project_id = request.query_params.get("project")
        target = request.query_params.get("target", "root")
        if not project_id:
            return Response({"detail": "project 参数必填"}, status=status.HTTP_400_BAD_REQUEST)
        _require_project_admin(request, project_id=int(project_id))

        if target in ("", None, "root"):
            target_id = None
        else:
            try:
                target_id = int(target)
            except Exception:
                return Response({"detail": "target 参数非法"}, status=status.HTTP_400_BAD_REQUEST)

        qs = FileACL.objects.filter(project_id=int(project_id), target_entry_id=target_id).order_by("-id")
        return Response(FileACLSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], url_path="acl/grant")
    def acl_grant(self, request):
        project_id = request.data.get("project")
        target = request.data.get("target", "root")
        subject_kind = (request.data.get("subject_kind") or "").strip()
        subject_value = request.data.get("subject_value")
        effect = (request.data.get("effect") or "").strip()
        actions = request.data.get("actions") or []
        inherit = bool(request.data.get("inherit", True))

        if not project_id:
            return Response({"detail": "project 参数必填"}, status=status.HTTP_400_BAD_REQUEST)
        _require_project_admin(request, project_id=int(project_id))

        if target in ("", None, "root"):
            target_id = None
        else:
            try:
                target_id = int(target)
            except Exception:
                return Response({"detail": "target 参数非法"}, status=status.HTTP_400_BAD_REQUEST)
            # 确保 target 在项目内
            if not FileEntry.objects.filter(id=target_id, project_id=int(project_id)).exists():
                return Response({"detail": "目标不存在"}, status=status.HTTP_404_NOT_FOUND)

        if subject_kind not in {FileACL.SubjectKind.USER, FileACL.SubjectKind.ROLE}:
            return Response({"detail": "subject_kind 参数非法"}, status=status.HTTP_400_BAD_REQUEST)
        if effect not in {FileACL.Effect.ALLOW, FileACL.Effect.DENY}:
            return Response({"detail": "effect 参数非法"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(actions, list) or not actions:
            return Response({"detail": "actions 参数必填"}, status=status.HTTP_400_BAD_REQUEST)

        valid_actions = {a for a, _ in FileACL.Action.choices}
        for a in actions:
            if a not in valid_actions:
                return Response({"detail": f"action 非法：{a}"}, status=status.HTTP_400_BAD_REQUEST)

        payload: dict = {
            "project_id": int(project_id),
            "target_entry_id": target_id,
            "subject_kind": subject_kind,
            "effect": effect,
            "actions": actions,
            "inherit": inherit,
            "created_by": request.user,
        }

        if subject_kind == FileACL.SubjectKind.USER:
            try:
                payload["subject_user_id"] = int(subject_value)
            except Exception:
                return Response({"detail": "subject_value 需要 user_id"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            role = str(subject_value or "").strip()
            if role not in {ProjectMembership.Role.ADMIN, ProjectMembership.Role.PROJECT_ADMIN, ProjectMembership.Role.MEMBER}:
                return Response({"detail": "subject_value 需要 role（Admin/ProjectAdmin/Member）"}, status=status.HTTP_400_BAD_REQUEST)
            payload["subject_role"] = role

        acl = FileACL.objects.create(**payload)
        write_audit(request=request, action="ACL_GRANT", project=Project.objects.filter(id=int(project_id)).first(), path=str(acl.id))
        return Response({"ok": True, "data": FileACLSerializer(acl).data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["delete"], url_path=r"acl/(?P<acl_id>[^/.]+)")
    def acl_delete(self, request, acl_id=None):
        try:
            acl_id_int = int(acl_id)
        except Exception:
            return Response({"detail": "acl_id 非法"}, status=status.HTTP_400_BAD_REQUEST)
        acl = FileACL.objects.filter(id=acl_id_int).select_related("project").first()
        if not acl:
            return Response(status=204)
        _require_project_admin(request, project_id=acl.project_id)
        project = acl.project
        acl.delete()
        write_audit(request=request, action="ACL_DELETE", project=project, path=str(acl_id_int))
        return Response(status=204)

    @action(detail=True, methods=["post"], url_path="rename")
    def rename(self, request, pk=None):
        entry = self.get_object()
        _require_project_admin(request, project_id=entry.project_id)
        if entry.deleted_at is not None:
            return Response({"detail": "回收站条目不支持重命名"}, status=status.HTTP_400_BAD_REQUEST)

        from rest_framework.exceptions import ValidationError

        try:
            new_name = self._validate_entry_name(request.data.get("name") or "")
        except ValidationError as e:
            msg = e.detail.get("detail") if isinstance(e.detail, dict) else str(e.detail)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        # 同目录同名校验（排除自身）
        try:
            self._assert_sibling_name_available(
                project_id=entry.project_id,
                parent_id=entry.parent_id,
                name=new_name,
                exclude_ids=[entry.id],
            )
        except ValidationError as e:
            msg = e.detail.get("detail") if isinstance(e.detail, dict) else str(e.detail)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        if entry.name == new_name:
            return Response({"ok": True})

        entry.name = new_name
        entry.updated_by = request.user
        entry.save(update_fields=["name", "updated_by", "updated_at"])
        write_audit(request=request, action="FILE_RENAME", project=entry.project, path=str(entry.id))
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="move")
    def move(self, request, pk=None):
        entry = self.get_object()
        _require_project_admin(request, project_id=entry.project_id)
        if entry.deleted_at is not None:
            return Response({"detail": "回收站条目不支持移动"}, status=status.HTTP_400_BAD_REQUEST)

        parent = request.data.get("parent")
        if parent in ("", None, "root"):
            target_parent_id = None
        else:
            try:
                target_parent_id = int(parent)
            except Exception:
                return Response({"detail": "parent 参数非法"}, status=status.HTTP_400_BAD_REQUEST)
            self._get_parent_or_404(project_id=entry.project_id, parent_id=target_parent_id)

        # 目录不允许移入自身/子孙目录
        if entry.is_dir and target_parent_id is not None:
            subtree_ids = self._collect_subtree_ids(root_id=entry.id)
            if target_parent_id in subtree_ids:
                return Response({"detail": "不能将目录移动到自身或子目录中"}, status=status.HTTP_400_BAD_REQUEST)

        # 同目录同名校验（排除自身）
        from rest_framework.exceptions import ValidationError

        try:
            self._assert_sibling_name_available(
                project_id=entry.project_id,
                parent_id=target_parent_id,
                name=entry.name,
                exclude_ids=[entry.id],
            )
        except ValidationError as e:
            msg = e.detail.get("detail") if isinstance(e.detail, dict) else str(e.detail)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        if entry.parent_id == target_parent_id:
            return Response({"ok": True})

        entry.parent_id = target_parent_id
        entry.updated_by = request.user
        entry.save(update_fields=["parent", "updated_by", "updated_at"])
        write_audit(request=request, action="FILE_MOVE", project=entry.project, path=str(entry.id))
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="delete")
    def soft_delete(self, request, pk=None):
        entry = self.get_object()
        _require_project_admin(request, project_id=entry.project_id)
        if entry.deleted_at is not None:
            return Response({"detail": "已在回收站"}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        with transaction.atomic():
            if entry.is_dir:
                ids = self._collect_subtree_ids(root_id=entry.id)
                FileEntry.objects.filter(id__in=ids, deleted_at__isnull=True).update(
                    deleted_at=now,
                    deleted_by=request.user,
                    updated_by=request.user,
                )
            else:
                entry.deleted_at = now
                entry.deleted_by = request.user
                entry.updated_by = request.user
                entry.save(update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"])
        write_audit(request=request, action="FILE_DELETE_TO_RECYCLE", project=entry.project, path=str(entry.id))
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        entry = self.get_object()
        _require_project_admin(request, project_id=entry.project_id)
        if entry.deleted_at is None:
            return Response({"detail": "未在回收站"}, status=status.HTTP_400_BAD_REQUEST)

        # 先校验上级目录
        if entry.parent_id is not None:
            parent = FileEntry.objects.filter(id=entry.parent_id, project_id=entry.project_id).first()
            if not parent or parent.deleted_at is not None:
                return Response({"detail": "上级目录不存在或已删除"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if entry.is_dir:
                ids = self._collect_subtree_ids(root_id=entry.id)
                id_set = set(ids)

                # BFS 顺序：先父后子
                queue: list[int] = [entry.id]
                while queue:
                    cur_id = queue.pop(0)
                    cur = FileEntry.objects.select_for_update().filter(id=cur_id).first()
                    if not cur:
                        continue
                    # name 冲突检查：同父目录下已有未删除同名条目（排除本次将恢复的子树）
                    conflict = (
                        FileEntry.objects.filter(
                            project_id=cur.project_id,
                            parent_id=cur.parent_id,
                            name=cur.name,
                            deleted_at__isnull=True,
                        )
                        .exclude(id__in=id_set)
                        .exists()
                    )
                    if conflict:
                        return Response({"detail": f"恢复失败：同目录下存在同名条目（{cur.name}）"}, status=status.HTTP_400_BAD_REQUEST)

                    cur.deleted_at = None
                    cur.deleted_by = None
                    cur.updated_by = request.user
                    cur.save(update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"])

                    children = list(FileEntry.objects.filter(parent_id=cur_id, id__in=id_set).values_list("id", flat=True))
                    queue.extend(children)
            else:
                if FileEntry.objects.filter(
                    project_id=entry.project_id,
                    parent_id=entry.parent_id,
                    name=entry.name,
                    deleted_at__isnull=True,
                ).exclude(id=entry.id).exists():
                    return Response({"detail": "恢复失败：同目录下存在同名条目"}, status=status.HTTP_400_BAD_REQUEST)

                entry.deleted_at = None
                entry.deleted_by = None
                entry.updated_by = request.user
                entry.save(update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"])
        write_audit(request=request, action="FILE_RESTORE", project=entry.project, path=str(entry.id))
        return Response({"ok": True})

    @action(detail=True, methods=["delete"], url_path="purge")
    def purge(self, request, pk=None):
        entry = self.get_object()
        _require_project_admin(request, project_id=entry.project_id)
        if entry.deleted_at is None:
            return Response({"detail": "仅支持从回收站彻底删除"}, status=status.HTTP_400_BAD_REQUEST)
        entry_id = entry.id
        project = entry.project
        entry.delete()
        write_audit(request=request, action="FILE_PURGE", project=project, path=str(entry_id))
        return Response({"ok": True})


class ProjectEventViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ProjectEvent.objects.select_related("project").order_by("start_at")
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        if self.request.user.is_staff:
            return qs
        return qs.filter(project__memberships__user_id=self.request.user.id, project__memberships__is_active=True).distinct()

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsProjectAdminOrSystemAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        event = serializer.save()
        write_audit(request=self.request, action="EVENT_CREATE", project=event.project, path=str(event.id))

    def perform_update(self, serializer):
        event = serializer.save()
        write_audit(request=self.request, action="EVENT_UPDATE", project=event.project, path=str(event.id))

    def perform_destroy(self, instance):
        write_audit(request=self.request, action="EVENT_DELETE", project=instance.project, path=str(instance.id))
        super().perform_destroy(instance)


class ProjectTaskViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ProjectTask.objects.select_related("project").order_by("status", "sort_order", "-created_at")
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        if self.request.user.is_staff:
            return qs
        return qs.filter(project__memberships__user_id=self.request.user.id, project__memberships__is_active=True).distinct()

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsProjectAdminOrSystemAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        task = serializer.save()
        write_audit(request=self.request, action="TASK_CREATE", project=task.project, path=str(task.id))

    def perform_update(self, serializer):
        task = serializer.save()
        write_audit(request=self.request, action="TASK_UPDATE", project=task.project, path=str(task.id))

    def perform_destroy(self, instance):
        write_audit(request=self.request, action="TASK_DELETE", project=instance.project, path=str(instance.id))
        super().perform_destroy(instance)


class UserAdminViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("username")
    serializer_class = UserAdminSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = AuditLog.objects.select_related("project", "actor").order_by("-created_at")
        project_id = self.request.query_params.get("project")
        action = self.request.query_params.get("action")
        if project_id:
            qs = qs.filter(project_id=project_id)
        if action:
            qs = qs.filter(action=action)
        if self.request.user.is_staff:
            return qs
        return qs.filter(project__memberships__user_id=self.request.user.id, project__memberships__is_active=True).distinct()


class RecycleBinViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RecycleBinItemSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get_queryset(self):
        qs = RecycleBinItem.objects.select_related("deleted_by", "restored_by").order_by("-deleted_at")
        object_type = self.request.query_params.get("type")
        if object_type:
            qs = qs.filter(object_type=object_type)
        include_restored = self.request.query_params.get("include_restored") == "1"
        if not include_restored:
            qs = qs.filter(is_restored=False)
        return qs

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        item: RecycleBinItem = self.get_object()
        if item.is_restored:
            return Response({"ok": False, "error": {"code": "ALREADY_RESTORED", "message": "该条目已恢复"}}, status=400)
        if item.object_type != RecycleBinItem.ObjectType.PROJECT:
            return Response({"ok": False, "error": {"code": "UNSUPPORTED", "message": "暂不支持该类型恢复"}}, status=400)

        payload = item.payload or {}
        p = payload.get("project") or {}
        code = p.get("code")
        if not code:
            return Response({"ok": False, "error": {"code": "BAD_PAYLOAD", "message": "回收站数据损坏"}}, status=400)
        if Project.objects.filter(code=code).exists():
            return Response(
                {"ok": False, "error": {"code": "CODE_CONFLICT", "message": f"项目编码已存在：{code}"}},
                status=400,
            )

        with transaction.atomic():
            project = Project.objects.create(
                code=code,
                name=p.get("name", ""),
                description=p.get("description", ""),
                status=p.get("status", Project.Status.ACTIVE),
                start_date=p.get("start_date") or None,
                end_date=p.get("end_date") or None,
                competition_stage=p.get("competition_stage", Project.CompetitionStage.SCHOOL),
                progress_percent=int(p.get("progress_percent") or 0),
            )
            if p.get("created_at"):
                Project.objects.filter(id=project.id).update(created_at=p.get("created_at"))

            for m in payload.get("memberships") or []:
                user_id = m.get("user_id")
                if not user_id:
                    continue
                membership, _ = ProjectMembership.objects.get_or_create(
                    project=project,
                    user_id=user_id,
                    defaults={
                        "role": m.get("role") or ProjectMembership.Role.MEMBER,
                        "is_active": bool(m.get("is_active", True)),
                    },
                )
                if m.get("joined_at"):
                    ProjectMembership.objects.filter(id=membership.id).update(joined_at=m.get("joined_at"))

            for a in payload.get("awards") or []:
                award = ProjectAward.objects.create(
                    project=project,
                    stage=a.get("stage", ""),
                    title=a.get("title", ""),
                    level=a.get("level", ""),
                    description=a.get("description", ""),
                    awarded_at=a.get("awarded_at") or None,
                )
                if a.get("created_at"):
                    ProjectAward.objects.filter(id=award.id).update(created_at=a.get("created_at"))

            for e in payload.get("events") or []:
                event = ProjectEvent.objects.create(
                    project=project,
                    title=e.get("title", ""),
                    start_at=e.get("start_at"),
                    end_at=e.get("end_at") or None,
                    stage=e.get("stage", ""),
                    description=e.get("description", ""),
                )
                if e.get("created_at"):
                    ProjectEvent.objects.filter(id=event.id).update(created_at=e.get("created_at"))

            for t in payload.get("tasks") or []:
                task = ProjectTask.objects.create(
                    project=project,
                    title=t.get("title", ""),
                    status=t.get("status") or ProjectTask.Status.TODO,
                    start_date=t.get("start_date") or None,
                    end_date=t.get("end_date") or None,
                    progress_percent=int(t.get("progress_percent") or 0),
                    description=t.get("description", ""),
                    sort_order=int(t.get("sort_order") or 0),
                )
                if t.get("created_at"):
                    ProjectTask.objects.filter(id=task.id).update(created_at=t.get("created_at"))

            item.mark_restored(user=request.user)

        write_audit(request=request, action="PROJECT_RESTORE", project=project, path=str(item.id))
        return Response({"ok": True, "data": ProjectSerializer(project).data})

    @action(detail=True, methods=["delete"], url_path="purge")
    def purge(self, request, pk=None):
        item: RecycleBinItem = self.get_object()
        item.delete()
        write_audit(request=request, action="RECYCLE_PURGE", project=None, path=str(pk))
        return Response(status=204)
