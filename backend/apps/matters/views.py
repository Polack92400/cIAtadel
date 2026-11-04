from django.db.models import Count, Q
from rest_framework import exceptions, generics

from apps.accounts.roles import Role, role_at_least
from apps.audit import service as audit
from apps.audit.models import AuditEvent
from apps.core.permissions import TenantScopedMixin

from .models import accessible_matters
from .serializers import MatterSerializer


class MatterListCreateView(TenantScopedMixin, generics.ListCreateAPIView):
    serializer_class = MatterSerializer
    pagination_class = None

    def get_queryset(self):
        return accessible_matters(self.membership).annotate(
            document_count=Count("documents", filter=Q(documents__tenant=self.tenant))
        )

    def perform_create(self, serializer):
        _check_restriction_rights(self.membership, serializer.validated_data)
        matter = serializer.save(tenant=self.tenant, created_by=self.request.user)
        audit.record(
            "matter.created",
            category=AuditEvent.Category.DOCUMENT,
            request=self.request,
            target=matter,
            target_label=matter.name,
        )


class MatterDetailView(TenantScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MatterSerializer
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return accessible_matters(self.membership).annotate(
            document_count=Count("documents", filter=Q(documents__tenant=self.tenant))
        )

    def get_min_role(self, safe):
        if self.request.method == "DELETE":
            return Role.ADMIN
        return super().get_min_role(safe)

    def perform_update(self, serializer):
        _check_restriction_rights(self.membership, serializer.validated_data)
        matter = serializer.save()
        audit.record(
            "matter.updated",
            category=AuditEvent.Category.DOCUMENT,
            request=self.request,
            target=matter,
            target_label=matter.name,
        )

    def perform_destroy(self, instance):
        if instance.documents.exists():
            raise exceptions.ValidationError("Move or delete the matter's documents first.")
        audit.record(
            "matter.deleted",
            category=AuditEvent.Category.DOCUMENT,
            request=self.request,
            target=instance,
            target_label=instance.name,
        )
        instance.delete()


def _check_restriction_rights(membership, data):
    touches = "is_restricted" in data or "allowed_members" in data
    if touches and not role_at_least(membership.role, Role.ADMIN):
        raise exceptions.PermissionDenied("Only administrators can restrict matters.")
