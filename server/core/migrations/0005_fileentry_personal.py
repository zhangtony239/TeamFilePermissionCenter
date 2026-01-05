from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_fileentry"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="fileentry",
            name="is_personal",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="fileentry",
            name="owner_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="owned_file_entries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="fileentry",
            index=models.Index(fields=["project", "is_personal", "owner_user"], name="core_fileen_project_6c9c62_idx"),
        ),
    ]
