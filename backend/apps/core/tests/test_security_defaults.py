"""Guards on security-relevant defaults, so regressions fail CI."""

import pytest
from django.conf import settings


def test_api_denies_by_default():
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]


def test_requests_are_atomic_for_rls_tenant_context():
    assert settings.DATABASES["default"]["ATOMIC_REQUESTS"] is True


def test_custom_user_model():
    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_tests_never_call_real_ai_providers():
    assert settings.AI["LLM_PROVIDER"] == "fake"
    assert settings.AI["EMBEDDING_PROVIDER"] == "fake"


@pytest.mark.django_db
def test_unknown_api_route_does_not_leak_debug_page(api_client):
    resp = api_client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    assert b"Traceback" not in resp.content


@pytest.mark.security
def test_tenant_scoped_queryset_fails_closed():
    from apps.core.models import TenantScopedQuerySet
    from apps.tenants.models import Tenant

    qs = TenantScopedQuerySet(model=Tenant)
    assert qs.for_tenant(None).query.is_empty()
