from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import FileEntry, RecycleBinItem

class Command(BaseCommand):
    help = "Cleanup recycle bin items older than 30 days"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete items older than this many days",
        )

    def handle(self, *args, **options):
        days = options["days"]
        threshold = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"Cleaning up items deleted before {threshold}...")

        # 1. Cleanup FileEntries (Soft Deleted)
        # Note: We should probably delete children first if we were doing cascading, 
        # but Django's on_delete=CASCADE handles it if we delete parents.
        # However, here we are deleting specific entries.
        # If a folder is soft-deleted, its children are also soft-deleted (by the view logic).
        # If we hard-delete the folder, the children (if they exist in DB) will be hard-deleted by CASCADE 
        # because FileEntry.parent has on_delete=models.CASCADE.
        # So we just need to find the top-level deleted items? 
        # No, we can just delete all matching items.
        
        files_qs = FileEntry.objects.filter(deleted_at__lt=threshold)
        files_count = files_qs.count()
        if files_count > 0:
            # We loop to ensure signals or storage cleanup if we had any (we don't have signals yet, but good practice)
            # But for bulk delete efficiency:
            files_qs.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {files_count} expired file entries."))
        else:
            self.stdout.write("No expired file entries found.")

        # 2. Cleanup RecycleBinItems (Projects)
        # Only delete if NOT restored.
        projects_qs = RecycleBinItem.objects.filter(deleted_at__lt=threshold, is_restored=False)
        projects_count = projects_qs.count()
        if projects_count > 0:
            projects_qs.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {projects_count} expired project recycle bin items."))
        else:
            self.stdout.write("No expired project recycle bin items found.")
