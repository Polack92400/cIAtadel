# cIAtadel — Security Design

> POC. This document describes intended controls and how they will be tested.
> It is not a compliance statement.

## 1. Assets and actors

| Asset                              | Why it matters                                  |
|------------------------------------|-------------------------------------------------|
| Uploaded PDFs and extracted text   | Client-confidential (legal privilege, audit)    |
| Embeddings / chunks                | Reconstructable content — same sensitivity      |
| Conversations and answers          | Reveal matters and client strategy              |
| Membership / role data             | Grants access to all of the above               |
| Audit log                          | Evidence; must be tamper-resistant              |
| Secrets (DB, S3, JWT keys)         | Full compromise if leaked                       |

Actors: anonymous internet user; authenticated user of firm A acting
maliciously against firm B; low-privilege member of firm A escalating inside
firm A; a malicious **document** (prompt injection, parser exploit).

## 2. Threats → controls → tests

| # | Threat (STRIDE)                                   | Control                                                                                                                           | Test (Phase 9)                                                  |
|---|---------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| T1 | Cross-tenant read via forged `X-Tenant-ID` (E)   | Tenant resolved only from an **active Membership** of the authenticated user; header is a selector, never trusted                 | user A sends tenant B id → 404, no data                         |
| T2 | IDOR on `/documents/{uuid}` (I)                  | All lookups `Model.objects.for_tenant(request.tenant).get(pk=…)`; other-tenant objects → 404                                       | A fetches/downloads/deletes B's doc id → 404, object unchanged  |
| T3 | Missing filter in a new endpoint (I)             | `TenantScopedViewSet` base class; `for_tenant(None)` returns empty; **PostgreSQL RLS** as backstop                                 | RLS test: raw SQL without tenant context returns 0 rows         |
| T4 | Vector search leaking other tenants (I)          | `tenant_id`/`matter_id` filter in the **same SQL** as the `<=>` ordering, before `LIMIT`                                            | tenant B has a *closer* chunk; A's retrieval never returns it   |
| T5 | Matter-level leak inside a firm (I)              | Retrieval limited to matters the membership can access                                                                            | restricted matter excluded from retrieval + listing             |
| T6 | Conversation snooping (I)                        | Conversations scoped by tenant **and** owner (or explicit sharing)                                                                 | A2 cannot read A1's conversation; B cannot read A's             |
| T7 | Prompt injection in uploaded PDF (T/E)           | Docs are data: delimited, labelled untrusted; system prompt states precedence; model has **no tools** and no authz role; retrieval happens before the LLM so the model can't widen scope | injected "ignore instructions / reveal tenant B" doc → no B content, citations only from authorized chunks |
| T8 | Malicious / malformed PDF (D/E)                  | Size cap, `%PDF-` magic check, MIME check, page/char limits, Celery soft/hard time limits, parse in worker, failures → `FAILED` | truncated, zip-bomb-ish, non-PDF renamed `.pdf`, encrypted PDF  |
| T9 | Storage path disclosure / direct bucket access (I)| Keys `tenants/{tenant}/documents/{doc}.pdf` never sent to client; downloads streamed by Django after authz; bucket private      | API responses contain no `storage_key`, no MinIO host           |
| T10 | Token theft via XSS (S)                         | Access/refresh JWT in **HttpOnly, SameSite=Lax, Secure** cookies; short access TTL; refresh rotation; CSP in Phase 4                | JS cannot read tokens; logout clears cookies                    |
| T11 | CSRF on cookie-auth (T)                          | Django CSRF double-submit on unsafe methods; SameSite=Lax                                                                          | POST without token → 403                                        |
| T12 | Privilege escalation inside firm (E)             | Role checks (`owner/admin/member/viewer`) server-side; admins can't grant above own role; last owner protected                    | member calls admin endpoints → 403                              |
| T13 | Brute force login (S/D)                          | Throttling per target account and per client IP (taken from the last X-Forwarded-For hop added by the trusted proxy), generic errors, failed sign-ins audited in the account's firms | repeated failures → 429 while other accounts still log in |
| T14 | Repudiation (R)                                  | `AuditEvent` append-only (no update/delete API, DB trigger blocks UPDATE/DELETE)                                                   | events written for login, upload, download, delete, role change |
| T15 | Info leak via errors (I)                         | DEBUG off outside dev; uniform error envelope; request ID instead of stack traces                                                  | 404/500 contain no traceback (already tested in Phase 1)        |
| T16 | Celery task tampering (T/E)                      | Tasks take only IDs; worker re-loads the Document and derives tenant from DB; JSON serializer only                                 | task with forged tenant arg impossible by signature             |

## 3. Tenant resolution — the single rule

```
request.tenant = Membership.objects.get(
    user=request.user,
    tenant_id=<X-Tenant-ID header>,     # selector only
    is_active=True,
    tenant__is_active=True,
).tenant                                 # otherwise → 404, request.tenant = None
```

- If the header is missing and the user has exactly one membership, that one
  is used; otherwise the request is rejected.
- Tenant-scoped views refuse to run when `request.tenant is None` (fail
  closed). Nothing ever does `Model.objects.all()` in a tenant view.
- 404 instead of 403 for other tenants' objects, so IDs can't be probed.
- The JWT carries only the user id — not tenants or roles — so revoking a
  membership takes effect on the next request.

## 4. PostgreSQL Row-Level Security (defence in depth)

Plan (Phase 3, tested in Phase 9):

1. Two DB roles: `ciatadel_owner` (owns tables, runs migrations) and
   `ciatadel_app` (runtime; **not owner, not superuser, no BYPASSRLS**).
2. For each tenant-owned table:
   ```sql
   ALTER TABLE documents_document ENABLE ROW LEVEL SECURITY;
   ALTER TABLE documents_document FORCE ROW LEVEL SECURITY;
   CREATE POLICY tenant_isolation ON documents_document
     USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
     WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);
   ```
   An unset setting yields `NULL` → no rows (fail closed).
3. Tenant context is set with `SET LOCAL app.current_tenant = …` (via
   `set_config(..., true)`) inside the request transaction
   (`ATOMIC_REQUESTS=True`). `SET LOCAL` dies with the transaction, so a
   pooled connection (`CONN_MAX_AGE`, or PgBouncer in *transaction* mode) can
   never carry one tenant's context into another request.
4. Celery tasks wrap work in `transaction.atomic()` + the same helper.
5. Cross-tenant tables (`tenants_tenant`, `accounts_user`,
   `accounts_membership`) are not RLS-scoped by tenant; access is
   application-controlled.
6. RLS is a backstop. Application filtering remains mandatory and is what the
   main test suite verifies.

## 5. Prompt-injection posture

- The LLM never decides *what* it may see: authorization and retrieval are
  complete before the prompt is built.
- The model has no tools, no network, no DB access — worst case is a wrong or
  manipulated *answer*, which is mitigated by mandatory citations and a UI that
  separates "From your documents" from "Assistant interpretation".
- Context blocks are delimited and labelled; the system prompt states that
  text inside them is untrusted content and can't change instructions.
- Output is rendered as text/Markdown without raw HTML (no XSS via model).

## 6. Secrets and configuration

- `.env.example` only contains placeholders; `.env` is git-ignored.
- Secrets are never returned by any API or rendered in the frontend bundle.
  Only `BACKEND_INTERNAL_URL` is known to Next.js, and only server-side.
- On AWS: Secrets Manager + KMS; IAM task roles instead of static S3 keys.

## 7. Implementation status

All controls T1–T16 are implemented and covered by tests in
`backend/tests/security`, `backend/apps/*/tests` and `frontend/e2e`
(see `docs/roadmap.md`). Gaps and hardening items are listed in
[`docs/limitations.md`](../limitations.md).

## 8. Known POC limitations (summary)

- No MFA, SSO or password-reset flow (OIDC-ready model only).
- No antivirus / CDR on PDFs (pypdf parsing in a time-limited worker only).
- No per-tenant encryption keys (bucket-level encryption on AWS).
- Ollama runs unauthenticated on the internal network — must stay unexposed.
- Audit log is tamper-resistant at the DB layer, not cryptographically chained.
