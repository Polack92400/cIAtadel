from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import exceptions, generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit import service as audit
from apps.audit.models import AuditEvent
from apps.core.permissions import TenantScopedMixin

from .authentication import enforce_csrf
from .cookies import clear_auth_cookies, set_auth_cookies
from .models import Membership
from .roles import RANK, Role
from .serializers import (
    LoginSerializer,
    MemberCreateSerializer,
    MemberSerializer,
    MeSerializer,
)

User = get_user_model()
SEC = AuditEvent.Category.SECURITY
ADM = AuditEvent.Category.ADMIN


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Issues the CSRF cookie used by the double-submit protection."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "ok"})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        enforce_csrf(request)
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].lower()
        user = authenticate(request, email=email, password=ser.validated_data["password"])
        if user is None:
            # Returned (not raised) so the audit row is committed.
            audit.record(
                "auth.login", category=SEC, request=request, outcome="failure", email=email
            )
            return Response(
                {"error": {"status": 401, "detail": "Invalid email or password."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        refresh = RefreshToken.for_user(user)
        User.objects.filter(pk=user.pk).update(last_login=refresh.current_time)
        audit.record("auth.login", category=SEC, request=request, actor=user)
        response = Response(MeSerializer(user).data)
        set_auth_cookies(response, refresh)
        return response


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf(request)
        raw = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if not raw:
            raise exceptions.NotAuthenticated("No session.")
        try:
            old = RefreshToken(raw)
            user = User.objects.get(pk=old["user_id"], is_active=True)
            old.blacklist()  # rotation: each refresh token is single-use
        except (TokenError, User.DoesNotExist, KeyError):
            response = Response(
                {"error": {"status": 401, "detail": "Session expired."}}, status=401
            )
            clear_auth_cookies(response)
            return response
        response = Response({"detail": "ok"})
        set_auth_cookies(response, RefreshToken.for_user(user))
        return response


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf(request)
        raw = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if raw:
            try:
                token = RefreshToken(raw)
                actor = User.objects.filter(pk=token["user_id"]).first()
                token.blacklist()
                audit.record("auth.logout", category=SEC, request=request, actor=actor)
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


# --- Firm administration ------------------------------------------------------


class MemberListCreateView(TenantScopedMixin, generics.ListCreateAPIView):
    min_role_read = Role.ADMIN
    min_role_write = Role.ADMIN
    serializer_class = MemberSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Membership.objects.filter(tenant=self.tenant)
            .select_related("user")
            .order_by("user__email")
        )

    def create(self, request, *args, **kwargs):
        ser = MemberCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        _assert_can_grant(self.membership, data["role"])
        with transaction.atomic():
            user = User.objects.filter(email=data["email"]).first()
            created_user = user is None
            if created_user:
                user = User.objects.create_user(
                    data["email"], data["initial_password"], full_name=data.get("full_name", "")
                )
            membership, created = Membership.objects.get_or_create(
                user=user, tenant=self.tenant, defaults={"role": data["role"]}
            )
            if not created:
                raise exceptions.ValidationError({"email": "Already a member of this firm."})
        audit.record(
            "member.added",
            category=ADM,
            request=request,
            target=membership,
            target_label=user.email,
            role=data["role"],
            new_account=created_user,
        )
        return Response(MemberSerializer(membership).data, status=status.HTTP_201_CREATED)


class MemberDetailView(TenantScopedMixin, generics.RetrieveUpdateAPIView):
    min_role_read = Role.ADMIN
    min_role_write = Role.ADMIN
    serializer_class = MemberSerializer
    http_method_names = ["get", "patch"]

    def get_queryset(self):
        return Membership.objects.filter(tenant=self.tenant).select_related("user")

    def perform_update(self, serializer):
        target: Membership = serializer.instance
        me = self.membership
        new_role = serializer.validated_data.get("role", target.role)
        new_active = serializer.validated_data.get("is_active", target.is_active)
        if target.pk == me.pk:
            raise exceptions.PermissionDenied("You cannot change your own membership.")
        if RANK[target.role] > RANK[me.role]:
            raise exceptions.PermissionDenied("You cannot modify a member above your role.")
        _assert_can_grant(me, new_role)
        demoting_owner = target.role == Role.OWNER and (new_role != Role.OWNER or not new_active)
        if demoting_owner:
            owners = Membership.objects.filter(
                tenant=self.tenant, role=Role.OWNER, is_active=True
            ).count()
            if owners <= 1:
                raise exceptions.ValidationError("A firm must keep at least one active owner.")
        before = {"role": target.role, "is_active": target.is_active}
        instance = serializer.save()
        audit.record(
            "member.updated",
            category=ADM,
            request=self.request,
            target=instance,
            target_label=instance.user.email,
            before=before,
            after={"role": instance.role, "is_active": instance.is_active},
        )


def _assert_can_grant(me: Membership, role: str) -> None:
    if RANK[role] > RANK[me.role]:
        raise exceptions.PermissionDenied("You cannot grant a role above your own.")
