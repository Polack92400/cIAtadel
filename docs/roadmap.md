# Delivery roadmap

| Phase | Scope                                              | Status           |
|-------|----------------------------------------------------|------------------|
| 1     | Architecture and project scaffolding               | ✅ Awaiting review |
| 2     | Docker Compose and local infrastructure            | ⏳ Next          |
| 3     | Django models, authentication, tenant isolation, RLS | Planned        |
| 4     | Next.js frontend and authentication integration    | Planned          |
| 5     | Document management and MinIO integration         | Planned          |
| 6     | Celery PDF processing and pgvector indexing        | Planned          |
| 7     | Ollama integration and RAG                         | Planned          |
| 8     | Chat interface and source citations                | Planned          |
| 9     | Security tests and automated integration tests     | Planned          |
| 10    | Documentation and Terraform preparation            | Planned          |

## Phase 1 — delivered

- Architecture overview with diagrams: `architecture/overview.md`
- Threat model / security design: `architecture/security-design.md`
- ADRs 0001–0004: `adr/`
- Django project: split settings (base/dev/test/prod), 9 apps, custom UUID
  `User`, minimal `Tenant`, `TenantOwnedModel` + fail-closed
  `TenantScopedQuerySet`, request-ID middleware, error envelope, health
  endpoints, deny-by-default DRF config.
- Next.js 15 App Router scaffold: Tailwind v4 tokens, shadcn/ui config,
  TanStack Query provider, same-origin API client, `/api` rewrite to Django,
  security headers.
- `.env.example`, `.gitignore`, `Makefile`, GitHub Actions CI.

## Phase 1 — remaining limitations

- No Docker Compose yet (Phase 2) — the stack does not start as a whole.
- No authentication endpoints, memberships or RLS yet (Phase 3).
- `TenantOwnedModel` is not used by any concrete model yet.
- CI runs backend tests against PostgreSQL but nothing PostgreSQL-specific is
  tested until Phase 3.
