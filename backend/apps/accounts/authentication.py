from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


def enforce_csrf(request) -> None:
    """Same CSRF validation Django applies to session-authenticated requests."""
    check = _CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied(f"CSRF failed: {reason}")


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate from the HttpOnly access-token cookie.

    Because the browser attaches cookies automatically, every unsafe request
    must also pass Django's CSRF check (double-submit token).
    """

    def authenticate(self, request):
        raw = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS)
        if not raw:
            return None
        validated = self.get_validated_token(raw)
        user = self.get_user(validated)
        if not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive.")
        enforce_csrf(request)
        return user, validated

    def authenticate_header(self, request):
        # Makes DRF answer 401 (not 403) for missing/expired credentials.
        return 'Cookie realm="api"'
