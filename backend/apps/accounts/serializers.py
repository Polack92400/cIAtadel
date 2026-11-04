from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Membership
from .roles import Role

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, max_length=256)


class MembershipSummarySerializer(serializers.ModelSerializer):
    tenant_id = serializers.UUIDField(source="tenant.id")
    tenant_name = serializers.CharField(source="tenant.name")
    tenant_slug = serializers.CharField(source="tenant.slug")

    class Meta:
        model = Membership
        fields = ["tenant_id", "tenant_name", "tenant_slug", "role"]


class MeSerializer(serializers.ModelSerializer):
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "memberships"]

    def get_memberships(self, user):
        qs = user.memberships.select_related("tenant").filter(
            is_active=True, tenant__is_active=True
        )
        return MembershipSummarySerializer(qs.order_by("tenant__name"), many=True).data


class MemberSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    last_login = serializers.DateTimeField(source="user.last_login", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user_id",
            "email",
            "full_name",
            "role",
            "is_active",
            "created_at",
            "last_login",
        ]
        read_only_fields = ["id", "created_at"]


class MemberCreateSerializer(serializers.Serializer):
    """Controlled user creation by a firm administrator.

    If the email already exists the existing account is attached to the firm
    (its password is not changed); otherwise a user is created with the
    initial password chosen by the admin.
    """

    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=Role.choices, default=Role.MEMBER)
    initial_password = serializers.CharField(
        write_only=True, required=False, trim_whitespace=False, max_length=256
    )

    def validate(self, attrs):
        attrs["email"] = attrs["email"].lower()
        exists = User.objects.filter(email=attrs["email"]).exists()
        if not exists:
            pwd = attrs.get("initial_password")
            if not pwd:
                raise serializers.ValidationError(
                    {"initial_password": "Required when creating a new user."}
                )
            validate_password(pwd)
        return attrs
