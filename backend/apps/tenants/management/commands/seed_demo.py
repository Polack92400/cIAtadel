"""Idempotent demo data: two fictional firms, users with different roles, a
restricted matter, and synthetic PDFs pushed through the real pipeline."""

import hashlib
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Membership
from apps.accounts.roles import Role
from apps.core.tenancy import tenant_context
from apps.documents import services
from apps.documents.models import Document
from apps.documents.synthetic import DEMO_DOCUMENTS, make_pdf
from apps.matters.models import Matter
from apps.tenants.models import Tenant

FIRMS = [
    {
        "slug": "dupont-avocats",
        "name": "Dupont & Associes (law firm)",
        "users": [
            ("alice@dupont.test", "Alice Martin", Role.OWNER),
            ("bob@dupont.test", "Bob Lefevre", Role.MEMBER),
            ("carol@dupont.test", "Carol Petit", Role.VIEWER),
            ("consultant@shared.test", "Sam Consultant", Role.MEMBER),
        ],
        "matters": [
            ("Acme Robotics v. Globex Logistics", "LIT-2025-014", False, []),
            ("Riverside Office Lease", "RE-2023-002", True, ["alice@dupont.test"]),
        ],
    },
    {
        "slug": "northwind-audit",
        "name": "Northwind Audit LLP",
        "users": [
            ("dave@northwind.test", "Dave Okafor", Role.OWNER),
            ("erin@northwind.test", "Erin Walsh", Role.MEMBER),
            ("consultant@shared.test", "Sam Consultant", Role.VIEWER),
        ],
        "matters": [("Contoso Ltd - FY2025 statutory audit", "AUD-FY25-CON", False, [])],
    },
]


class Command(BaseCommand):
    help = "Create demo firms, users, matters and documents (idempotent)."

    def handle(self, *args, **opts):
        password = os.environ.get("DEMO_PASSWORD", "Demo-Password-2026")
        User = get_user_model()
        for firm in FIRMS:
            with transaction.atomic():
                tenant, _ = Tenant.objects.get_or_create(
                    slug=firm["slug"], defaults={"name": firm["name"]}
                )
                for email, name, role in firm["users"]:
                    user = User.objects.filter(email=email).first()
                    if user is None:
                        user = User.objects.create_user(email, password, full_name=name)
                    Membership.objects.get_or_create(
                        user=user, tenant=tenant, defaults={"role": role}
                    )
            with tenant_context(tenant.id):
                matters = {}
                for name, ref, restricted, allowed in firm["matters"]:
                    m, _ = Matter.objects.get_or_create(
                        tenant=tenant,
                        name=name,
                        defaults={"reference": ref, "is_restricted": restricted},
                    )
                    for email in allowed:
                        m.allowed_members.add(
                            Membership.objects.get(tenant=tenant, user__email=email)
                        )
                    matters[name] = m
                owner = Membership.objects.filter(tenant=tenant, role=Role.OWNER).first().user
                for spec in DEMO_DOCUMENTS[firm["slug"]]:
                    data = make_pdf(spec["title"], spec["pages"])
                    sha = hashlib.sha256(data).hexdigest()
                    if Document.objects.for_tenant(tenant).filter(sha256=sha).exists():
                        continue
                    services.create_document(
                        tenant=tenant,
                        user=owner,
                        matter=matters[spec["matter"]],
                        title=spec["title"],
                        filename=spec["filename"],
                        data=data,
                        sha256=sha,
                    )
            self.stdout.write(f"  firm ready: {tenant.name}")
        self.stdout.write(
            self.style.SUCCESS(f"Demo data ready. All demo accounts use the password: {password}")
        )
