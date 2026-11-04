import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import Membership
from apps.accounts.roles import Role
from apps.documents.synthetic import make_pdf
from apps.tenants.models import Tenant

PASSWORD = "correct-horse-battery-staple"  # noqa: S105 - test fixture


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def _user(email, tenant=None, role=Role.MEMBER):
    user = get_user_model().objects.create_user(email, PASSWORD, full_name=email.split("@")[0])
    if tenant:
        Membership.objects.create(user=user, tenant=tenant, role=role)
    return user


@pytest.fixture
def world(db):
    """Two firms. A: alice (owner), bob (member), carol (viewer). B: dave (owner)."""
    a = Tenant.objects.create(name="Firm A", slug="firm-a")
    b = Tenant.objects.create(name="Firm B", slug="firm-b")
    return {
        "a": a,
        "b": b,
        "alice": _user("alice@a.test", a, Role.OWNER),
        "bob": _user("bob@a.test", a, Role.MEMBER),
        "carol": _user("carol@a.test", a, Role.VIEWER),
        "dave": _user("dave@b.test", b, Role.OWNER),
    }


def login(user, tenant=None, client=None) -> APIClient:
    client = client or APIClient()
    resp = client.post(
        "/api/v1/auth/login", {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert resp.status_code == 200, resp.content
    if tenant is not None:
        client.credentials(HTTP_X_TENANT_ID=str(tenant.id))
    return client


@pytest.fixture
def as_user(world):
    def _as(name, tenant_key=None):
        user = world[name]
        tenant = world[tenant_key] if tenant_key else user.memberships.first().tenant
        return login(user, tenant)

    return _as


def pdf_bytes(
    text="The termination notice period is ninety days.", title="Test document", pages=None
) -> bytes:
    return make_pdf(title, pages or [[text]])


def upload(client, data: bytes, name="doc.pdf", **extra):
    from django.core.files.uploadedfile import SimpleUploadedFile

    f = SimpleUploadedFile(name, data, content_type="application/pdf")
    return client.post("/api/v1/documents", {"file": f, **extra}, format="multipart")


@pytest.fixture
def run_tasks(django_capture_on_commit_callbacks):
    """Execute on_commit callbacks (Celery dispatch, eager) inside tests."""

    def _run(fn, *args, **kwargs):
        with django_capture_on_commit_callbacks(execute=True):
            return fn(*args, **kwargs)

    return _run
