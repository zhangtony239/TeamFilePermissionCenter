from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_default_root_acls(apps, schema_editor):
    Project = apps.get_model("core", "Project")
    FileACL = apps.get_model("core", "FileACL")

    for p in Project.objects.all().iterator():
        # ProjectAdmin：默认全权限（本项目）
        if not FileACL.objects.filter(
            project_id=p.id,
            target_entry__isnull=True,
            subject_kind="ROLE",
            subject_role="ProjectAdmin",
        ).exists():
            FileACL.objects.create(
                project_id=p.id,
                target_entry=None,
                subject_kind="ROLE",
                subject_role="ProjectAdmin",
                effect="ALLOW",
                actions=[
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
                inherit=True,
            )

        # Member：默认只读（避免升级后看不到任何文件），后续可通过 DENY/ALLOW 收窄范围
        if not FileACL.objects.filter(
            project_id=p.id,
            target_entry__isnull=True,
            subject_kind="ROLE",
            subject_role="Member",
        ).exists():
            FileACL.objects.create(
                project_id=p.id,
                target_entry=None,
                subject_kind="ROLE",
                subject_role="Member",
                effect="ALLOW",
                actions=["LIST", "PREVIEW", "DOWNLOAD"],
                inherit=True,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_fileentry_personal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FileACL",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject_kind", models.CharField(choices=[("USER", "用户"), ("ROLE", "角色")], max_length=8)),
                ("subject_role", models.CharField(blank=True, max_length=32)),
                ("effect", models.CharField(choices=[("ALLOW", "允许"), ("DENY", "拒绝")], max_length=8)),
                ("actions", models.JSONField(default=list)),
                ("inherit", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_file_acls",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="file_acls", to="core.project"),
                ),
                (
                    "subject_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="file_acls",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "target_entry",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="acls",
                        to="core.fileentry",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="fileacl",
            index=models.Index(fields=["project", "target_entry"], name="core_facl_prj_tgt_idx"),
        ),
        migrations.AddIndex(
            model_name="fileacl",
            index=models.Index(fields=["project", "subject_kind", "subject_user"], name="core_facl_prj_usr_idx"),
        ),
        migrations.AddIndex(
            model_name="fileacl",
            index=models.Index(fields=["project", "subject_kind", "subject_role"], name="core_facl_prj_role_idx"),
        ),
        migrations.RunPython(seed_default_root_acls, migrations.RunPython.noop),
    ]
