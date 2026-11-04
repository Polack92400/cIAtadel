from rest_framework import serializers

from apps.accounts.models import Membership

from .models import Matter


class MatterSerializer(serializers.ModelSerializer):
    document_count = serializers.IntegerField(read_only=True, default=0)
    allowed_members = serializers.PrimaryKeyRelatedField(
        many=True, required=False, queryset=Membership.objects.none()
    )

    class Meta:
        model = Matter
        fields = [
            "id",
            "name",
            "reference",
            "description",
            "is_restricted",
            "allowed_members",
            "document_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        # Only memberships of *this* tenant can be referenced (anti-IDOR).
        self.fields["allowed_members"].child_relation.queryset = (
            Membership.objects.filter(tenant=tenant) if tenant else Membership.objects.none()
        )

    def validate_name(self, value):
        request = self.context["request"]
        qs = Matter.objects.for_tenant(request.tenant).filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A matter with this name already exists.")
        return value
