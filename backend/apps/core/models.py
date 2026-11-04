"""Base classes every tenant-owned model will inherit (used from Phase 3).

Rule: any row that belongs to a firm has a non-nullable `tenant` FK and is
only ever fetched through `Model.objects.for_tenant(tenant)`. Views get the
tenant from `request.tenant`, which is resolved server-side from the user's
memberships — never from a raw client value.
"""

import uuid

from django.db import models


class UUIDModel(models.Model):
    """UUID primary keys: no enumerable IDs in URLs (IDOR is still enforced
    by tenant filtering — UUIDs are defense in depth, not access control)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        if tenant is None:
            # Fail closed: a missing tenant must never mean "all tenants".
            return self.none()
        return self.filter(tenant=tenant)


class TenantOwnedModel(UUIDModel):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="+",
        db_index=True,
    )

    objects = TenantScopedQuerySet.as_manager()

    class Meta:
        abstract = True
