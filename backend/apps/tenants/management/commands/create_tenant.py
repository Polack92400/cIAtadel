from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.accounts.models import Membership
from apps.accounts.roles import Role
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Create a firm (tenant) and its first owner."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--owner-email", required=True)
        parser.add_argument("--owner-password", required=True)
        parser.add_argument("--owner-name", default="")

    @transaction.atomic
    def handle(self, *args, **o):
        slug = slugify(o["name"])[:63]
        if Tenant.objects.filter(slug=slug).exists():
            raise CommandError(f"A firm with slug {slug!r} already exists.")
        User = get_user_model()
        email = o["owner_email"].lower()
        user = User.objects.filter(email=email).first()
        if user is None:
            validate_password(o["owner_password"])
            user = User.objects.create_user(email, o["owner_password"], full_name=o["owner_name"])
        tenant = Tenant.objects.create(name=o["name"], slug=slug)
        Membership.objects.create(user=user, tenant=tenant, role=Role.OWNER)
        self.stdout.write(
            self.style.SUCCESS(f"Created firm {tenant.name} ({tenant.id}) owned by {email}")
        )
