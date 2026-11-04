# Delivery roadmap

| Phase | Scope | Status |
|---|---|---|
| 1 | Architecture and project scaffolding | ✅ Done |
| 2 | Docker Compose and local infrastructure | ✅ Done |
| 3 | Django models, authentication, tenant isolation, RLS | ✅ Done |
| 4 | Next.js frontend and authentication integration | ✅ Done |
| 5 | Document management and MinIO integration | ✅ Done |
| 6 | Celery PDF processing and pgvector indexing | ✅ Done |
| 7 | Ollama integration and RAG | ✅ Done |
| 8 | Chat interface and source citations | ✅ Done |
| 9 | Security tests and automated integration tests | ✅ Done |
| 10 | Documentation and Terraform preparation | ✅ Done |

## Definition of done (from the brief)

| Criterion | Where |
|---|---|
| Starts locally through Docker Compose | `docker compose up -d --build --wait` (README) |
| Two fictional firms | `seed_demo`: Dupont & Associes, Northwind Audit; `create_tenant` command |
| Multiple users with different permissions | owner / admin / member / viewer, ethical-wall matters |
| Upload and manage PDFs | Documents pages; upload, filter, move, download, delete |
| Asynchronous processing | Celery worker, live status in the UI |
| Query through a local LLM | Ollama (`llama3.2:3b` + `nomic-embed-text`) |
| Source references | Citations with document and page, excerpt, link |
| Conversations persist | Conversation history per user and firm |
| Cross-tenant access rejected | `backend/tests/security/`, Playwright `authorization.spec.ts` |
| Automated functional and security tests pass | 86 backend tests, 9 Playwright tests, CI |
| Setup and architecture documentation | README, `docs/` |

## Test inventory

- `backend/apps/*/tests`: auth (cookies, CSRF, rotation, throttling,
  deactivation), member administration and role escalation, document
  validation/processing/deletion, chunking and extraction.
- `backend/tests/security`: tenant isolation and IDOR on every endpoint,
  forged tenant header, mass assignment, matter ACLs, PostgreSQL RLS with a
  non-superuser role, append-only audit, vector-search isolation, prompt
  injection.
- `backend/tests/integration`: upload → index → question → cited answer;
  insufficient context; LLM outage leaves no partial state.
- `frontend/e2e`: login/logout, HttpOnly cookies, unauthorized navigation,
  cross-firm URL access, ethical wall, upload → indexing → delete, invalid
  upload, chat with citations and persistence.
