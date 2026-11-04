from rest_framework import generics, serializers

from apps.accounts.roles import Role
from apps.core.permissions import TenantScopedMixin

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "created_at",
            "actor_email",
            "category",
            "action",
            "outcome",
            "target_type",
            "target_id",
            "target_label",
            "metadata",
            "ip_address",
            "request_id",
        ]


class AuditEventListView(TenantScopedMixin, generics.ListAPIView):
    """Firm-scoped audit trail, admins only. Events without a tenant (e.g.
    failed logins with unknown emails) are platform-level and not shown."""

    serializer_class = AuditEventSerializer
    min_role_read = Role.ADMIN

    def get_queryset(self):
        qs = AuditEvent.objects.filter(tenant=self.tenant)
        p = self.request.query_params
        if cat := p.get("category"):
            qs = qs.filter(category=cat)
        if action := p.get("action"):
            qs = qs.filter(action=action)
        if actor := p.get("actor"):
            qs = qs.filter(actor_email__icontains=actor)
        return qs
