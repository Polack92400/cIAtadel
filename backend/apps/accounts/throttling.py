from rest_framework.throttling import SimpleRateThrottle


class LoginAccountThrottle(SimpleRateThrottle):
    """Limits attempts per target account, whatever the source IP."""

    scope = "login"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "")).strip().lower()[:254]
        if not email:
            return None
        return self.cache_format % {"scope": self.scope, "ident": email}


class LoginIPThrottle(SimpleRateThrottle):
    """Limits attempts per client IP (resolved through the trusted proxy)."""

    scope = "login_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
