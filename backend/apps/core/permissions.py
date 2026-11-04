"""Tenant-aware DRF building blocks.

`TenantScopedMixin` is the base for every view touching tenant data. It:
  1. resolves the active tenant from the authenticated user's *active*
     memberships (the X-Tenant-ID header is only a selector),
  2. sets the RLS tenant for the current request transaction,
  3. enforces a minimum role for reads and for writes,
  4. returns 404 (never 403) when the tenant is not one of the user's, so
     tenant IDs cannot be probed.
"""

import uuid

from django.conf import settings
from rest_framework import exceptions, permissions

from apps.accounts.models import Membership
from apps.accounts.roles import Role, role_at_least

from .tenancy import set_db_tenant


def resolve_membership(user, requested_tenant_id: str | None) -> Membership:
    memberships = Membership.objects.select_related("tenant").filter(
        user=user, is_active=True, tenant__is_active=True
    )
    if requested_tenant_id:
        try:
            tenant_uuid = uuid.UUID(str(requested_tenant_id))
        except ValueError as exc:
            raise exceptions.NotFound("Workspace not found.") from exc
        membership = memberships.filter(tenant_id=tenant_uuid).first()
        if membership is None:
            raise exceptions.NotFound("Workspace not found.")
        return membership
    only = list(memberships[:2])
    if len(only) == 1:
        return only[0]
    if not only:
        raise exceptions.PermissionDenied("You are not a member of any workspace.")
    raise exceptions.ValidationError({"tenant": "Select a workspace (X-Tenant-ID header)."})


class IsTenantMember(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        membership = resolve_membership(request.user, request.META.get(settings.TENANT_HEADER))
        request.membership = membership
        request.tenant = membership.tenant
        set_db_tenant(membership.tenant_id)

        safe = request.method in permissions.SAFE_METHODS
        minimum = view.get_min_role(safe) if hasattr(view, "get_min_role") else Role.VIEWER
        if not role_at_least(membership.role, minimum):
            raise exceptions.PermissionDenied("Your role does not allow this action.")
        return True


class TenantScopedMixin:
    """Mix into APIView / GenericAPIView subclasses."""

    permission_classes = [permissions.IsAuthenticated, IsTenantMember]
    min_role_read: str = Role.VIEWER
    min_role_write: str = Role.MEMBER

    def get_min_role(self, safe: bool) -> str:
        return self.min_role_read if safe else self.min_role_write

    @property
    def tenant(self):
        return self.request.tenant

    @property
    def membership(self):
        return self.request.membership
