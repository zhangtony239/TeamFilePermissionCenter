from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    display_name = models.CharField(max_length=64, blank=True)

    def __str__(self) -> str:
        return self.display_name or self.username


class Project(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "进行中"
        ARCHIVED = "ARCHIVED", "归档"
        ENDED = "ENDED", "结束"

    class CompetitionStage(models.TextChoices):
        SCHOOL = "SCHOOL", "校赛"
        CITY = "CITY", "市赛"
        PROVINCE = "PROVINCE", "省赛"
        NATIONAL = "NATIONAL", "国赛"

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    competition_stage = models.CharField(
        max_length=16, choices=CompetitionStage.choices, default=CompetitionStage.SCHOOL
    )
    progress_percent = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


class ProjectMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "Admin", "系统管理员"
        PROJECT_ADMIN = "ProjectAdmin", "项目管理员"
        MEMBER = "Member", "项目成员"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("project", "user")


class ProjectAward(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="awards")
    stage = models.CharField(max_length=32)
    title = models.CharField(max_length=128)
    level = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    awarded_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ProjectEvent(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=128)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    stage = models.CharField(max_length=32, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ProjectTask(models.Model):
    class Status(models.TextChoices):
        TODO = "TODO", "未开始"
        DOING = "DOING", "进行中"
        DONE = "DONE", "已完成"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.TODO)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=64)
    path = models.CharField(max_length=512, blank=True)
    result = models.CharField(max_length=32, default="OK")
    reason = models.CharField(max_length=128, blank=True)
    ip = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RecycleBinItem(models.Model):
    class ObjectType(models.TextChoices):
        PROJECT = "PROJECT", "项目"

    object_type = models.CharField(max_length=32, choices=ObjectType.choices)
    object_id = models.BigIntegerField(null=True, blank=True)
    object_code = models.CharField(max_length=64, blank=True)
    object_name = models.CharField(max_length=128, blank=True)

    payload = models.JSONField(default=dict)

    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="deleted_items")
    deleted_at = models.DateTimeField(auto_now_add=True)

    is_restored = models.BooleanField(default=False)
    restored_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="restored_items")
    restored_at = models.DateTimeField(null=True, blank=True)

    def mark_restored(self, *, user: User | None = None):
        self.is_restored = True
        self.restored_by = user
        self.restored_at = timezone.now()
        self.save(update_fields=["is_restored", "restored_by", "restored_at"])


class FileEntry(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="file_entries")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=255)
    is_dir = models.BooleanField(default=False)

    size_bytes = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=128, blank=True)
    storage_key = models.CharField(max_length=512, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_file_entries",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_file_entries",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_file_entries",
    )

    # 个人区：同项目内对其他成员不可见
    is_personal = models.BooleanField(default=False)
    owner_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_file_entries",
    )

    class Meta:
        indexes = [
            models.Index(fields=["project", "parent", "is_dir"], name="core_fileen_project_f25027_idx"),
            models.Index(fields=["project", "deleted_at"], name="core_fileen_project_4a2c11_idx"),
            models.Index(fields=["project", "is_personal", "owner_user"], name="core_fileen_project_6c9c62_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class FileACL(models.Model):
    class SubjectKind(models.TextChoices):
        USER = "USER", "用户"
        ROLE = "ROLE", "角色"

    class Effect(models.TextChoices):
        ALLOW = "ALLOW", "允许"
        DENY = "DENY", "拒绝"

    class Action(models.TextChoices):
        LIST = "LIST", "列表"
        PREVIEW = "PREVIEW", "预览"
        DOWNLOAD = "DOWNLOAD", "下载"
        UPLOAD = "UPLOAD", "上传"
        UPDATE = "UPDATE", "覆盖更新"
        MOVE = "MOVE", "移动/改名"
        DELETE = "DELETE", "删除"
        RESTORE = "RESTORE", "恢复"
        ACL_ADMIN = "ACL_ADMIN", "权限管理"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="file_acls")

    # target_entry 为空表示“项目根（root）”的 ACL
    target_entry = models.ForeignKey(
        FileEntry,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="acls",
    )

    subject_kind = models.CharField(max_length=8, choices=SubjectKind.choices)
    subject_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="file_acls",
    )
    # 角色值：Admin/ProjectAdmin/Member（与 ProjectMembership.Role 保持一致）
    subject_role = models.CharField(max_length=32, blank=True)

    effect = models.CharField(max_length=8, choices=Effect.choices)
    actions = models.JSONField(default=list)
    inherit = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_file_acls",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "target_entry"], name="core_facl_prj_tgt_idx"),
            models.Index(fields=["project", "subject_kind", "subject_user"], name="core_facl_prj_usr_idx"),
            models.Index(fields=["project", "subject_kind", "subject_role"], name="core_facl_prj_role_idx"),
        ]

    def __str__(self) -> str:
        target = str(self.target_entry_id) if self.target_entry_id else "root"
        subject = (
            f"user:{self.subject_user_id}"
            if self.subject_kind == self.SubjectKind.USER
            else f"role:{self.subject_role}"
        )
        return f"{self.project_id}:{target} {subject} {self.effect}"
