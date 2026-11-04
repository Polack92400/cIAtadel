"""Tenant context helpers.

Application code always filters by tenant explicitly. In addition, on
PostgreSQL every tenant-owned table has a Row-Level Security policy that
compares `tenant_id` with the transaction-local setting `app.current_tenant`.
`set_config(..., is_local => true)` scopes it to the current transaction, so
pooled connections can never leak one tenant's context into another request.
"""

from contextlib import contextmanager

from django.db import connection, transaction

SETTING = "app.current_tenant"


def set_db_tenant(tenant_id) -> None:
    """Set the RLS tenant for the *current transaction* (no-op off Postgres)."""
    if connection.vendor != "postgresql":
        return
    if not connection.in_atomic_block:
        # Outside a transaction set_config(local) would be lost immediately;
        # failing loudly prevents silently running without the RLS backstop.
        raise RuntimeError("set_db_tenant() must be called inside transaction.atomic()")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, true)", [SETTING, str(tenant_id) if tenant_id else ""]
        )


@contextmanager
def tenant_context(tenant_id):
    """Run a block (Celery task, management command) inside one tenant."""
    with transaction.atomic():
        set_db_tenant(tenant_id)
        yield
