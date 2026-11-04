import pytest

from apps.accounts.models import Membership
from apps.audit.models import AuditEvent

pytestmark = pytest.mark.django_db


def test_admin_can_list_and_create_members(as_user):
    client = as_user("alice")
    assert len(client.get("/api/v1/members").json()) == 3
    resp = client.post(
        "/api/v1/members",
        {
            "email": "new@a.test",
            "full_name": "New",
            "role": "member",
            "initial_password": "a-strong-password-42",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert AuditEvent.objects.filter(action="member.added").exists()


def test_member_and_viewer_cannot_administer(as_user):
    assert as_user("bob").get("/api/v1/members").status_code == 403
    assert as_user("carol").get("/api/v1/members").status_code == 403


def test_weak_initial_password_rejected(as_user):
    resp = as_user("alice").post(
        "/api/v1/members",
        {"email": "w@a.test", "role": "member", "initial_password": "123"},
        format="json",
    )
    assert resp.status_code == 400


def test_admin_cannot_grant_above_own_role(world, as_user):
    alice_m = Membership.objects.get(user=world["alice"])
    bob_m = Membership.objects.get(user=world["bob"])
    bob_m.role = "admin"
    bob_m.save()
    client = as_user("bob")
    resp = client.patch(
        f"/api/v1/members/{Membership.objects.get(user=world['carol']).pk}",
        {"role": "owner"},
        format="json",
    )
    assert resp.status_code == 403
    resp = client.patch(f"/api/v1/members/{alice_m.pk}", {"is_active": False}, format="json")
    assert resp.status_code == 403


def test_last_owner_cannot_be_demoted(world, as_user):
    from apps.accounts.models import Membership as M

    bob_m = M.objects.get(user=world["bob"])
    bob_m.role = "owner"
    bob_m.save()
    client = as_user("bob")
    alice_m = M.objects.get(user=world["alice"])
    assert (
        client.patch(f"/api/v1/members/{alice_m.pk}", {"role": "member"}, format="json").status_code
        == 200
    )
    # bob is now the only owner and cannot change himself either
    assert (
        client.patch(f"/api/v1/members/{bob_m.pk}", {"role": "member"}, format="json").status_code
        == 403
    )


def test_cannot_modify_member_of_another_firm(world, as_user):
    dave_m = Membership.objects.get(user=world["dave"])
    resp = as_user("alice").patch(f"/api/v1/members/{dave_m.pk}", {"role": "viewer"}, format="json")
    assert resp.status_code == 404
    dave_m.refresh_from_db()
    assert dave_m.role == "owner"
