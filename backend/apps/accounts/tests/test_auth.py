import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from conftest import PASSWORD, login

pytestmark = pytest.mark.django_db


def test_login_sets_httponly_cookies_and_returns_memberships(world):
    client = APIClient()
    resp = client.post(
        "/api/v1/auth/login", {"email": "ALICE@a.test", "password": PASSWORD}, format="json"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "alice@a.test"
    assert [m["tenant_slug"] for m in body["memberships"]] == ["firm-a"]
    access = resp.cookies["ciatadel_access"]
    refresh = resp.cookies["ciatadel_refresh"]
    assert access["httponly"] and refresh["httponly"]
    assert refresh["path"] == "/api/v1/auth/"
    # Tokens never appear in the JSON body.
    assert access.value not in resp.content.decode()


def test_wrong_password_is_rejected_generically_and_audited(world):
    resp = APIClient().post(
        "/api/v1/auth/login", {"email": "alice@a.test", "password": "nope"}, format="json"
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["detail"] == "Invalid email or password."
    ev = AuditEvent.objects.get(action="auth.login", outcome="failure")
    assert ev.actor_email == "alice@a.test"


def test_unknown_user_gets_same_error(world):
    resp = APIClient().post(
        "/api/v1/auth/login", {"email": "ghost@x.test", "password": "nope"}, format="json"
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["detail"] == "Invalid email or password."


def test_me_requires_authentication(world):
    assert APIClient().get("/api/v1/auth/me").status_code == 401


def test_me_returns_current_user(world):
    client = login(world["bob"])
    assert client.get("/api/v1/auth/me").json()["email"] == "bob@a.test"


def test_logout_clears_cookies_and_blacklists_refresh(world):
    client = login(world["alice"])
    old_refresh = client.cookies["ciatadel_refresh"].value
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204
    assert client.cookies["ciatadel_access"].value == ""
    replay = APIClient()
    replay.cookies["ciatadel_refresh"] = old_refresh
    assert replay.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_rotates_and_old_token_cannot_be_replayed(world):
    client = login(world["alice"])
    old = client.cookies["ciatadel_refresh"].value
    assert client.post("/api/v1/auth/refresh").status_code == 200
    assert client.cookies["ciatadel_refresh"].value != old
    replay = APIClient()
    replay.cookies["ciatadel_refresh"] = old
    assert replay.post("/api/v1/auth/refresh").status_code == 401


def test_unsafe_requests_require_csrf_token(world):
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/v1/auth/csrf")
    token = client.cookies["csrftoken"].value
    # Login without the header is refused...
    bad = client.post(
        "/api/v1/auth/login", {"email": "alice@a.test", "password": PASSWORD}, format="json"
    )
    assert bad.status_code == 403
    ok = client.post(
        "/api/v1/auth/login",
        {"email": "alice@a.test", "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert ok.status_code == 200
    client.credentials(HTTP_X_TENANT_ID=str(world["a"].id))
    # ...and so is an authenticated write without it.
    resp = client.post("/api/v1/matters", {"name": "X"}, format="json")
    assert resp.status_code == 403
    resp = client.post(
        "/api/v1/matters",
        {"name": "X"},
        format="json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert resp.status_code == 201


def test_deactivated_membership_loses_access_immediately(world):
    client = login(world["bob"], world["a"])
    assert client.get("/api/v1/documents").status_code == 200
    world["bob"].memberships.update(is_active=False)
    assert client.get("/api/v1/documents").status_code == 404


def test_inactive_user_cannot_log_in(world):
    world["bob"].is_active = False
    world["bob"].save()
    resp = APIClient().post(
        "/api/v1/auth/login", {"email": "bob@a.test", "password": PASSWORD}, format="json"
    )
    assert resp.status_code == 401


def test_login_is_throttled_per_account_across_ips(world, settings):
    from django.core.cache import cache
    from rest_framework.throttling import SimpleRateThrottle

    cache.clear()
    rates = {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "login": "3/min"}
    SimpleRateThrottle.THROTTLE_RATES = rates
    try:
        codes = []
        for i in range(5):
            # Different client IPs (as forwarded by the proxy), same account.
            resp = APIClient().post(
                "/api/v1/auth/login",
                {"email": "alice@a.test", "password": "bad"},
                format="json",
                HTTP_X_FORWARDED_FOR=f"203.0.113.{i}",
            )
            codes.append(resp.status_code)
        assert codes[:3] == [401, 401, 401] and codes[3:] == [429, 429]
        # Another account is unaffected.
        resp = APIClient().post(
            "/api/v1/auth/login", {"email": "bob@a.test", "password": PASSWORD}, format="json"
        )
        assert resp.status_code == 200
    finally:
        SimpleRateThrottle.THROTTLE_RATES = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        cache.clear()


def test_sign_ins_appear_in_each_firms_audit_log(world):
    from apps.accounts.models import Membership

    Membership.objects.create(user=world["bob"], tenant=world["b"], role="member")
    APIClient().post(
        "/api/v1/auth/login",
        {"email": "bob@a.test", "password": "bad"},
        format="json",
        HTTP_X_FORWARDED_FOR="10.9.9.9, 198.51.100.7",
    )
    login(world["bob"])
    for tenant in (world["a"], world["b"]):
        events = AuditEvent.objects.filter(tenant=tenant, action="auth.login")
        assert {e.outcome for e in events} == {"success", "failure"}
        failure = events.get(outcome="failure")
        assert failure.actor_id is None and failure.actor_email == "bob@a.test"
        # Last hop (appended by our proxy) wins over a spoofable first entry.
        assert failure.ip_address == "198.51.100.7"
    # Firm A's admin sees it through the API; firm B's events stay in firm B.
    alice = login(world["alice"], world["a"])
    rows = alice.get("/api/v1/audit-events?category=security").json()["results"]
    assert any(r["actor_email"] == "bob@a.test" and r["outcome"] == "failure" for r in rows)
    assert all(r["actor_email"] != "dave@b.test" for r in rows)
