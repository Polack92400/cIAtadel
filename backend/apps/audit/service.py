import logging

from .models import AuditEvent

logger = logging.getLogger("audit")


def _client_ip(request):
    if request is None:
        return None
    # Behind the Next.js proxy / ALB the left-most X-Forwarded-For is the
    # client. Only trusted because the backend is not reachable directly.
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")
    return ip or None


def record(
    action: str,
    *,
    category: str,
    request=None,
    tenant=None,
    actor=None,
    target=None,
    target_label: str = "",
    outcome: str = "success",
    **metadata,
) -> AuditEvent:
    if actor is None and request is not None and request.user.is_authenticated:
        actor = request.user
    if tenant is None and request is not None:
        tenant = getattr(request, "tenant", None)
    event = AuditEvent.objects.create(
        tenant=tenant,
        actor=actor,
        actor_email=getattr(actor, "email", "") or metadata.pop("email", ""),
        category=category,
        action=action,
        outcome=outcome,
        target_type=type(target).__name__ if target is not None else "",
        target_id=str(getattr(target, "pk", "")) if target is not None else "",
        target_label=target_label[:255],
        metadata=metadata,
        ip_address=_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
        request_id=getattr(request, "request_id", "") if request else "",
    )
    logger.info("audit %s %s outcome=%s", category, action, outcome)
    return event
