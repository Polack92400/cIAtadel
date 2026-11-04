from django.db import models
from django.db.models import Q

from apps.accounts.roles import Role, role_at_least
from apps.core.models import TenantOwnedModel


class Matter(TenantOwnedModel):
    """A client matter / engagement / folder.

    Unrestricted matters are visible to every member of the firm. A
    restricted matter is visible only to admins/owners and to the memberships
    listed in `allowed_members` ("ethical wall").
    """

    name = models.CharField(max_length=200)
    reference = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True, max_length=2000)
    is_restricted = models.BooleanField(default=False)
    allowed_members = models.ManyToManyField(
        "accounts.Membership", blank=True, related_name="restricted_matters"
    )
    created_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "name"], name="uniq_matter_name_per_tenant")
        ]

    def __str__(self) -> str:
        return self.name


def accessible_matters(membership):
    """Matters of the membership's tenant that this member may see."""
    qs = Matter.objects.for_tenant(membership.tenant)
    if role_at_least(membership.role, Role.ADMIN):
        return qs
    return qs.filter(Q(is_restricted=False) | Q(allowed_members=membership)).distinct()


def matter_scope_q(membership, prefix: str = "") -> Q:
    """Q() limiting a tenant-owned model with a `matter` FK to what the member
    may see: no matter ("General") or an accessible matter."""
    if role_at_least(membership.role, Role.ADMIN):
        return Q()
    ids = list(accessible_matters(membership).values_list("id", flat=True))
    return Q(**{f"{prefix}matter__isnull": True}) | Q(**{f"{prefix}matter_id__in": ids})
