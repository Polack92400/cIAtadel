# cIAtadel

Secure, multi-tenant AI workspace for professional firms (lawyers,
accountants, auditors): upload PDFs, organise them by matter, and ask
questions answered from your own documents with citations — with strict
isolation between firms.

> **Proof of concept.** Fictional data only. No production-grade compliance
> or certification is claimed.

## Status

Phase 1 of 10 — architecture and scaffolding. See [`docs/roadmap.md`](docs/roadmap.md).

## Documentation

- [Product brief](docs/brief.md)
- [Architecture overview](docs/architecture/overview.md)
- [Security design & threat model](docs/architecture/security-design.md)
- [Architecture decision records](docs/adr/README.md)
- AWS target diagram: [`mermaid-diagram.png`](mermaid-diagram.png)

## Stack

| Layer      | Technology                                                     |
|------------|----------------------------------------------------------------|
| Frontend   | Next.js (App Router), React, TypeScript, Tailwind, shadcn/ui, TanStack Query |
| Backend    | Django 5.2 LTS, Django REST Framework, SimpleJWT (HttpOnly cookies) |
| Data       | PostgreSQL 16 + pgvector, MinIO (S3 API)                        |
| AI         | Ollama (configurable LLM + embedding models), custom RAG        |
| Async      | Celery + Redis                                                 |
| Tooling    | Docker Compose, GitHub Actions, Pytest, Playwright, Terraform (layout only) |

## Running Phase 1 locally (without Docker)

Docker Compose arrives in Phase 2. Until then:

```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
```

```bash
cd backend && pytest
```

```bash
cd frontend && npm ci && npm run lint && npm run typecheck && npm run build
```

Or everything at once: `make check`.

## Repository layout

```
backend/    Django modular monolith (config/, apps/<9 apps>/)
frontend/   Next.js App Router application
docs/       brief, architecture, security design, ADRs, roadmap
```
