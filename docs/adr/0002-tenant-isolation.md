# ADR 0002 — Tenant isolation strategy

**Options considered.**
1. Database-per-tenant — strongest isolation, heavy ops, poor fit for pgvector
   + Django migrations at POC stage.
2. Schema-per-tenant (django-tenants) — good isolation, but complicates
   migrations, cross-tenant users and connection pooling.
3. **Shared schema with `tenant_id` + app-level enforcement + PostgreSQL RLS.**

**Decision.** Option 3. Every tenant-owned model inherits
`core.models.TenantOwnedModel`; views get `request.tenant` resolved from the
user's active `Membership`; querysets use `for_tenant()` which fails closed;
RLS (`FORCE`d, non-owner app role, `SET LOCAL` per transaction) is the
backstop. Other tenants' objects return 404.

**Consequences.** Cheap and simple to operate; isolation depends on discipline
→ enforced by base classes, RLS, and an explicit cross-tenant test suite. The
"Dedicated Customer Account (Premium)" in the target AWS diagram remains
possible: the same images can be deployed against a dedicated database/bucket
for a single tenant.
