from django.core.management.base import BaseCommand

from apps.documents.storage import get_storage


class Command(BaseCommand):
    help = "Create the document bucket if it does not exist."

    def handle(self, *args, **opts):
        get_storage().ensure_bucket()
        self.stdout.write(self.style.SUCCESS("Storage bucket ready."))
