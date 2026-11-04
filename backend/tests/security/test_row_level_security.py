"""PostgreSQL RLS backstop: even raw SQL without an application filter
cannot cross tenants when running as the (non-superuser) application role."""

import pytest
from django.db import connection, transaction

from apps.audit.models import AuditEvent
from apps.core.tenancy import set_db_tenant
from apps.documents.models import Document

pytestmark = [pytest.mark.django_db, pytest.mark.security]


@pytest.fixture
def app_role(world):
    with connection.cursor() as cur:
        cur.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        if not cur.fetchone()[0]:
            pytest.skip("needs a superuser test connection to create a probe role")
        cur.execute("CREATE ROLE rls_probe NOLOGIN NOSUPERUSER NOBYPASSRLS")
        cur.execute(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rls_probe"
        )
    for t, title in ((world["a"], "A doc"), (world["b"], "B doc")):
        Document.objects.create(
            tenant=t,
            title=title,
            original_filename="x.pdf",
            size_bytes=1,
            sha256=title,
            storage_key="k",
        )

    def run(sql, params=(), tenant=None):
        # SET LOCAL survives a released savepoint, so always reset explicitly.
        with transaction.atomic(), connection.cursor() as cur:
            set_db_tenant(tenant.id if tenant is not None else None)
            cur.execute("SET LOCAL ROLE rls_probe")
            try:
                cur.execute(sql, params)
                return cur.fetchall() if cur.description else cur.rowcount
            finally:
                if not connection.needs_rollback:
                    cur.execute("RESET ROLE")

    return run


def test_no_tenant_context_sees_nothing(app_role):
    assert app_role("SELECT title FROM documents_document") == []


def test_tenant_context_sees_only_its_rows(app_role, world):
    rows = app_role("SELECT title FROM documents_document", tenant=world["a"])
    assert rows == [("A doc",)]


def test_cross_tenant_update_affects_nothing(app_role, world):
    n = app_role(
        "UPDATE documents_document SET title = 'pwned' WHERE title = 'B doc'", tenant=world["a"]
    )
    assert n == 0
    assert Document.objects.get(tenant=world["b"]).title == "B doc"


def test_cannot_insert_row_for_another_tenant(app_role, world):
    from django.db import DatabaseError

    with pytest.raises(DatabaseError):
        app_role(
            "INSERT INTO documents_document (id, tenant_id, title, original_filename, "
            "content_type, size_bytes, sha256, storage_key, status, error_code, error_message, "
            "chunk_count, created_at, updated_at) VALUES (gen_random_uuid(), %s, 't', 'f', "
            "'application/pdf', 1, 'h', 'k', 'pending', '', '', 0, now(), now())",
            [str(world["b"].id)],
            tenant=world["a"],
        )


def test_audit_log_is_append_only_at_db_level(world):
    from django.db import DatabaseError

    ev = AuditEvent.objects.create(category="security", action="x", tenant=world["a"])
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditEvent.objects.filter(pk=ev.pk).update(action="tampered")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditEvent.objects.filter(pk=ev.pk).delete()
    with pytest.raises(RuntimeError):
        ev.save()
