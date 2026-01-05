from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AuditLog, FileACL, FileEntry, FileVersion, Project, ProjectAward, ProjectEvent, ProjectMembership, ProjectTask, RecycleBinItem

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "display_name", "email", "is_active", "is_staff"]


class UserAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "username", "display_name", "email", "is_active", "is_staff", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password", "")
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if password is not None and password != "":
            instance.set_password(password)
        instance.save()
        return instance


class ProjectSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "code",
            "name",
            "description",
            "status",
            "start_date",
            "end_date",
            "competition_stage",
            "progress_percent",
            "created_at",
            "members_count",
        ]


class ProjectMembershipSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProjectMembership
        fields = ["id", "project", "user", "user_id", "role", "joined_at", "is_active"]
        read_only_fields = ["project", "joined_at"]


class ProjectAwardSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)

    class Meta:
        model = ProjectAward
        fields = [
            "id",
            "project",
            "project_code",
            "project_name",
            "stage",
            "title",
            "level",
            "description",
            "awarded_at",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class ProjectEventSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)

    class Meta:
        model = ProjectEvent
        fields = [
            "id",
            "project",
            "project_code",
            "project_name",
            "title",
            "start_at",
            "end_at",
            "stage",
            "description",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class ProjectTaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)

    class Meta:
        model = ProjectTask
        fields = [
            "id",
            "project",
            "project_code",
            "project_name",
            "title",
            "status",
            "start_date",
            "end_date",
            "progress_percent",
            "description",
            "sort_order",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "project",
            "project_code",
            "project_name",
            "actor",
            "action",
            "path",
            "result",
            "reason",
            "ip",
            "user_agent",
            "created_at",
        ]


class RecycleBinItemSerializer(serializers.ModelSerializer):
    deleted_by = UserBriefSerializer(read_only=True)
    restored_by = UserBriefSerializer(read_only=True)

    class Meta:
        model = RecycleBinItem
        fields = [
            "id",
            "object_type",
            "object_id",
            "object_code",
            "object_name",
            "payload",
            "deleted_by",
            "deleted_at",
            "is_restored",
            "restored_by",
            "restored_at",
        ]
        read_only_fields = fields


class FileEntrySerializer(serializers.ModelSerializer):
    owner_user = serializers.IntegerField(source="owner_user_id", read_only=True)
    original_path = serializers.SerializerMethodField()

    class Meta:
        model = FileEntry
        fields = [
            "id",
            "project",
            "parent",
            "name",
            "is_dir",
            "size_bytes",
            "mime_type",
            "storage_key",
            "created_at",
            "updated_at",
            "deleted_at",
            "is_personal",
            "owner_user",
            "original_path",
        ]

    def get_original_path(self, obj) -> str:
        # 仅对回收站条目计算原路径，避免普通列表 N+1 性能损耗
        if obj.deleted_at is None:
            return ""
        
        path_parts = []
        curr = obj.parent
        # 限制最大深度防止死循环
        depth = 0
        while curr and depth < 20:
            path_parts.append(curr.name)
            curr = curr.parent
            depth += 1
        
        # 结果如 "/docs/specs/"
        return "/" + "/".join(reversed(path_parts)) + ("/" if path_parts else "")
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]


class FileDirNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileEntry
        fields = ["id", "name", "parent"]


class FileACLSerializer(serializers.ModelSerializer):
    target_entry = serializers.IntegerField(source="target_entry_id", allow_null=True, required=False)
    subject_user = serializers.IntegerField(source="subject_user_id", allow_null=True, required=False)

    class Meta:
        model = FileACL
        fields = [
            "id",
            "project",
            "target_entry",
            "subject_kind",
            "subject_user",
            "subject_role",
            "effect",
            "actions",
            "inherit",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]


class FileVersionSerializer(serializers.ModelSerializer):
    created_by = UserBriefSerializer(read_only=True)

    class Meta:
        model = FileVersion
        fields = [
            "id",
            "file_entry",
            "version_number",
            "size_bytes",
            "mime_type",
            "created_by",
            "created_at",
        ]
