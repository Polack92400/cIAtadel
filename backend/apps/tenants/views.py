from rest_framework import generics, serializers

from apps.accounts.roles import Role
from apps.audit import service as audit
from apps.audit.models import AuditEvent
from apps.core.permissions import TenantScopedMixin

from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "created_at", "member_count"]
        read_only_fields = ["id", "slug", "created_at"]

    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class CurrentTenantView(TenantScopedMixin, generics.RetrieveUpdateAPIView):
    """The active firm. Never addressed by ID in the URL: always the one
    resolved from the caller's membership."""

    serializer_class = TenantSerializer
    min_role_write = Role.ADMIN
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.tenant

    def perform_update(self, serializer):
        tenant = serializer.save()
        audit.record(
            "tenant.updated",
            category=AuditEvent.Category.ADMIN,
            request=self.request,
            target=tenant,
            target_label=tenant.name,
        )
