from django.contrib import admin

from .models import AuditLog, FileACL, FileEntry, Project, ProjectAward, ProjectEvent, ProjectMembership, ProjectTask, RecycleBinItem, User


admin.site.register(User)
admin.site.register(Project)
admin.site.register(ProjectMembership)
admin.site.register(ProjectAward)
admin.site.register(ProjectEvent)
admin.site.register(ProjectTask)
admin.site.register(AuditLog)
admin.site.register(RecycleBinItem)
admin.site.register(FileEntry)
admin.site.register(FileACL)
