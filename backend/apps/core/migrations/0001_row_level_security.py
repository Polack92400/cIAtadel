"""PostgreSQL Row-Level Security on every tenant-owned table.

Defence in depth behind application filtering (see
docs/architecture/security-design.md §4):
  * ENABLE + FORCE so even the table owner is subject to the policy
    (superusers still bypass: the runtime role must not be one).
  * The tenant comes from the transaction-local setting app.current_tenant;
    when unset, NULLIF(...) yields NULL and no row matches (fail closed).
"""

from django.db import migrations

TABLES = [
    "matters_matter",
    "documents_document",
    "rag_documentchunk",
    "conversations_conversation",
    "conversations_message",
    "conversations_citation",
]
CURRENT = "NULLIF(current_setting('app.current_tenant', true), '')::uuid"


def forward_sql():
    stmts = []
    for t in TABLES:
        stmts += [
            f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;",
            f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY;",
            f"CREATE POLICY tenant_isolation ON {t} USING (tenant_id = {CURRENT}) "
            f"WITH CHECK (tenant_id = {CURRENT});",
        ]
    # Audit: rows may be written without a tenant (e.g. failed logins), but
    # can only be *read* inside the matching tenant context.
    stmts += [
        "ALTER TABLE audit_auditevent ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE audit_auditevent FORCE ROW LEVEL SECURITY;",
        f"CREATE POLICY audit_read ON audit_auditevent FOR SELECT USING (tenant_id = {CURRENT});",
        f"CREATE POLICY audit_insert ON audit_auditevent FOR INSERT "
        f"WITH CHECK (tenant_id IS NULL OR tenant_id = {CURRENT});",
        # Append-only, enforced by the database itself.
        """
        CREATE OR REPLACE FUNCTION audit_block_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit events are append-only';
        END;
        $$ LANGUAGE plpgsql;
        """,
        "CREATE TRIGGER audit_no_update_delete BEFORE UPDATE OR DELETE ON audit_auditevent "
        "FOR EACH ROW EXECUTE FUNCTION audit_block_mutation();",
    ]
    return stmts


def reverse_sql():
    stmts = [
        "DROP TRIGGER IF EXISTS audit_no_update_delete ON audit_auditevent;",
        "DROP FUNCTION IF EXISTS audit_block_mutation();",
        "DROP POLICY IF EXISTS audit_read ON audit_auditevent;",
        "DROP POLICY IF EXISTS audit_insert ON audit_auditevent;",
        "ALTER TABLE audit_auditevent NO FORCE ROW LEVEL SECURITY;",
        "ALTER TABLE audit_auditevent DISABLE ROW LEVEL SECURITY;",
    ]
    for t in TABLES:
        stmts += [
            f"DROP POLICY IF EXISTS tenant_isolation ON {t};",
            f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY;",
            f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY;",
        ]
    return stmts


class Migration(migrations.Migration):
    dependencies = [
        ("matters", "0001_initial"),
        ("documents", "0002_initial"),
        ("rag", "0001_initial"),
        ("conversations", "0002_initial"),
        ("audit", "0001_initial"),
    ]

    operations = [migrations.RunSQL(forward_sql(), reverse_sql())]
