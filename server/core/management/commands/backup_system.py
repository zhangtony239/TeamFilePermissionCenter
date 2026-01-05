import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings

class Command(BaseCommand):
    help = "Backup the database to a JSON file"

    def handle(self, *args, **options):
        backup_dir = os.path.join(settings.BASE_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(backup_dir, filename)
        
        self.stdout.write(f"Backing up to {filepath}...")
        
        with open(filepath, "w", encoding="utf-8") as f:
            # Exclude contenttypes and auth.Permission to avoid conflicts on restore if schema changes slightly
            # But for full restore, we might need them.
            # For "core" app, it's safe.
            call_command("dumpdata", "core", indent=2, stdout=f)
            
        self.stdout.write(self.style.SUCCESS(f"Backup created: {filename}"))
