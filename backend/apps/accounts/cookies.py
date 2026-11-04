from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


def _common():
    return {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
    }


def set_auth_cookies(response, refresh: RefreshToken) -> None:
    jwt = settings.SIMPLE_JWT
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS,
        str(refresh.access_token),
        max_age=int(jwt["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        path=settings.AUTH_COOKIE_ACCESS_PATH,
        **_common(),
    )
    response.set_cookie(
        settings.AUTH_COOKIE_REFRESH,
        str(refresh),
        max_age=int(jwt["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=settings.AUTH_COOKIE_REFRESH_PATH,
        **_common(),
    )
    # Non-sensitive hint so the frontend middleware can redirect to /login
    # without being able to read either token.
    response.set_cookie(
        "ciatadel_session",
        "1",
        max_age=int(jwt["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path="/",
        httponly=False,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(settings.AUTH_COOKIE_ACCESS, path=settings.AUTH_COOKIE_ACCESS_PATH)
    response.delete_cookie(settings.AUTH_COOKIE_REFRESH, path=settings.AUTH_COOKIE_REFRESH_PATH)
    response.delete_cookie("ciatadel_session", path="/")
