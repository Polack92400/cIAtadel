import logging

from .models import AuditEvent

logger = logging.getLogger("audit")


def _client_ip(request):
    if request is None:
        return None
    # Exactly one trusted proxy (Next.js / ALB) appends the real client
    # address as the LAST X-Forwarded-For entry; earlier entries are
    # client-controlled and must not be trusted. Same rule as DRF NUM_PROXIES.
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = fwd.split(",")[-1].strip() if fwd else request.META.get("REMOTE_ADDR")
    return ip or None


def record_for_user_firms(action: str, *, user, request=None, outcome="success", **metadata):
    """Record an account-level event (login, logout) in the audit trail of
    every firm the user belongs to, so each firm's admins see their members'
    sign-ins and failed attempts. Unknown users get one platform-level row."""
    from apps.core.tenancy import set_db_tenant

    tenant_ids = []
    if user is not None:
        tenant_ids = list(
            user.memberships.filter(is_active=True).values_list("tenant_id", flat=True)
        )
    if not tenant_ids:
        return [
            record(
                action,
                category="security",
                request=request,
                actor=user,
                outcome=outcome,
                **metadata,
            )
        ]
    events = []
    try:
        for tid in tenant_ids:
            set_db_tenant(tid)  # RLS: inserts must match the tenant context
            events.append(
                record(
                    action,
                    category="security",
                    request=request,
                    actor=user if outcome == "success" else None,
                    outcome=outcome,
                    tenant_id_override=tid,
                    **metadata,
                )
            )
    finally:
        set_db_tenant(None)
    return events


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
    tenant_id_override = metadata.pop("tenant_id_override", None)
    email = metadata.pop("email", "")
    if tenant is None and request is not None:
        tenant = getattr(request, "tenant", None)
    event = AuditEvent.objects.create(
        tenant_id=tenant_id_override or (tenant.pk if tenant is not None else None),
        actor=actor,
        actor_email=getattr(actor, "email", "") or email,
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
