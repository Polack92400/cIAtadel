"""Tenant A must never read, change or infer Tenant B's data."""

import uuid

import pytest

from apps.accounts.models import Membership
from apps.conversations.models import Conversation
from apps.documents.models import Document
from apps.matters.models import Matter
from conftest import pdf_bytes, upload

pytestmark = [pytest.mark.django_db, pytest.mark.security]


@pytest.fixture
def b_doc(as_user, run_tasks):
    resp = run_tasks(
        upload,
        as_user("dave"),
        pdf_bytes("Firm B secret: merger price 99M."),
        "b-secret.pdf",
        title="B secret",
    )
    return Document.objects.get(pk=resp.json()["id"])


def test_document_list_contains_only_own_tenant(as_user, b_doc):
    data = as_user("alice").get("/api/v1/documents").json()
    assert data["count"] == 0


@pytest.mark.parametrize(
    "method,suffix",
    [("get", ""), ("patch", ""), ("delete", ""), ("get", "/download"), ("post", "/reprocess")],
)
def test_idor_on_other_tenant_document_returns_404(as_user, b_doc, method, suffix):
    client = as_user("alice")
    resp = getattr(client, method)(
        f"/api/v1/documents/{b_doc.pk}{suffix}", {"title": "pwned"}, format="json"
    )
    assert resp.status_code == 404
    b_doc.refresh_from_db()
    assert b_doc.title == "B secret"


def test_forged_tenant_header_is_rejected(world, b_doc):
    from conftest import login

    client = login(world["alice"], world["b"])  # alice claims to be in firm B
    for path in (
        "/api/v1/documents",
        f"/api/v1/documents/{b_doc.pk}",
        "/api/v1/members",
        "/api/v1/audit-events",
        "/api/v1/dashboard",
        "/api/v1/tenant",
    ):
        assert client.get(path).status_code == 404, path


@pytest.mark.parametrize("header", ["not-a-uuid", str(uuid.uuid4()), "' OR 1=1 --"])
def test_garbage_tenant_header(world, header):
    from conftest import login

    client = login(world["alice"])
    client.credentials(HTTP_X_TENANT_ID=header)
    assert client.get("/api/v1/documents").status_code == 404


def test_body_cannot_override_tenant(as_user, world, run_tasks):
    client = as_user("alice")
    resp = client.post(
        "/api/v1/matters", {"name": "M", "tenant": str(world["b"].id)}, format="json"
    )
    assert resp.status_code == 201
    assert Matter.objects.get(pk=resp.json()["id"]).tenant_id == world["a"].id
    resp = run_tasks(upload, client, pdf_bytes("x"), tenant=str(world["b"].id))
    assert Document.objects.get(pk=resp.json()["id"]).tenant_id == world["a"].id


def test_cannot_file_document_into_other_tenant_matter(as_user, world):
    b_matter = Matter.objects.create(tenant=world["b"], name="B matter")
    resp = upload(as_user("alice"), pdf_bytes(), matter=str(b_matter.pk))
    assert resp.status_code == 400
    assert Document.objects.count() == 0


def test_cannot_reference_other_tenant_membership_in_matter_acl(as_user, world):
    dave_m = Membership.objects.get(user=world["dave"])
    resp = as_user("alice").post(
        "/api/v1/matters",
        {"name": "Wall", "is_restricted": True, "allowed_members": [str(dave_m.pk)]},
        format="json",
    )
    assert resp.status_code == 400


def test_conversations_are_isolated_by_tenant_and_user(as_user, world):
    conv_b = Conversation.objects.create(tenant=world["b"], user=world["dave"], title="B chat")
    conv_alice = Conversation.objects.create(tenant=world["a"], user=world["alice"], title="A")
    bob = as_user("bob")
    for conv in (conv_b, conv_alice):  # other firm, and same-firm colleague
        assert bob.get(f"/api/v1/conversations/{conv.pk}").status_code == 404
        assert (
            bob.post(
                f"/api/v1/conversations/{conv.pk}/messages", {"content": "hi"}, format="json"
            ).status_code
            == 404
        )
        assert bob.delete(f"/api/v1/conversations/{conv.pk}").status_code == 404
    assert bob.get("/api/v1/conversations").json()["count"] == 0


def test_audit_log_is_tenant_scoped(as_user, b_doc):
    events = as_user("alice").get("/api/v1/audit-events").json()["results"]
    assert all(e["target_label"] != "B secret" for e in events)
    assert not any(e["actor_email"] == "dave@b.test" for e in events)


def test_restricted_matter_hidden_from_non_allowed_members(as_user, world, run_tasks):
    alice = as_user("alice")
    m = alice.post(
        "/api/v1/matters", {"name": "Ethical wall", "is_restricted": True}, format="json"
    ).json()
    doc = run_tasks(upload, alice, pdf_bytes("walled"), matter=m["id"]).json()
    bob = as_user("bob")
    assert all(x["id"] != m["id"] for x in bob.get("/api/v1/matters").json())
    assert bob.get(f"/api/v1/documents/{doc['id']}").status_code == 404
    assert bob.get(f"/api/v1/documents/{doc['id']}/download").status_code == 404
    assert bob.get("/api/v1/documents").json()["count"] == 0
    # Granting access makes it visible.
    bob_m = Membership.objects.get(user=world["bob"])
    alice.patch(f"/api/v1/matters/{m['id']}", {"allowed_members": [str(bob_m.pk)]}, format="json")
    assert bob.get(f"/api/v1/documents/{doc['id']}").status_code == 200


def test_member_cannot_lift_matter_restriction(as_user):
    alice = as_user("alice")
    m = alice.post("/api/v1/matters", {"name": "Wall"}, format="json").json()
    resp = as_user("bob").patch(
        f"/api/v1/matters/{m['id']}", {"is_restricted": True}, format="json"
    )
    assert resp.status_code == 403


def test_unauthenticated_access_is_denied_everywhere(world, api_client, b_doc):
    for path in (
        "/api/v1/documents",
        f"/api/v1/documents/{b_doc.pk}/download",
        "/api/v1/conversations",
        "/api/v1/members",
        "/api/v1/dashboard",
    ):
        assert api_client.get(path).status_code == 401, path


def test_responses_never_leak_internal_storage_details(as_user, run_tasks):
    client = as_user("bob")
    run_tasks(upload, client, pdf_bytes())
    for path in ("/api/v1/documents", "/api/v1/dashboard"):
        text = client.get(path).content.decode()
        assert "tenants/" not in text and "storage_key" not in text and "minio" not in text
