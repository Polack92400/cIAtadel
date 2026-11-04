# cIAtadel — Architecture Overview

> Status: Phase 1 (architecture + scaffolding). POC with fictional data only —
> no compliance or certification is claimed.

## 1. Guiding principles

1. **Tenant isolation first.** Every tenant-owned row carries a non-nullable
   `tenant` FK; every query goes through a tenant-scoped manager; PostgreSQL
   Row-Level Security is a second, independent line of defence.
2. **Modular monolith.** One Django project, nine bounded apps, one Celery
   worker image. No microservices until a real scaling need appears.
3. **Single front door.** The browser only talks to Next.js. Next.js proxies
   `/api/*` to Django on the internal network. PostgreSQL, MinIO, Redis and
   Ollama are never reachable from the browser (and mostly not from the host).
4. **Providers behind interfaces.** Storage (S3 API), LLM and embeddings
   (provider registry) and identity (`external_subject` on `User`) are
   configured, not hard-coded — so the AWS move swaps adapters, not business
   logic.
5. **Documents are untrusted input.** Parsed in a worker with time/size limits,
   never executed, and treated as *data* inside LLM prompts.

## 2. Local runtime (Docker Compose — Phase 2)

```mermaid
flowchart LR
    B[Browser] -->|HTTPS/HTTP :3000| FE[Next.js<br/>frontend]
    subgraph internal[Internal Docker network — not published to host]
        FE -->|/api/* rewrite| API[Django + DRF<br/>gunicorn]
        API --> PG[(PostgreSQL 16<br/>+ pgvector)]
        API --> S3[(MinIO<br/>S3 API)]
        API --> R[(Redis)]
        API -->|chat| OL[Ollama]
        R --> W[Celery worker]
        W --> PG
        W --> S3
        W -->|embeddings| OL
    end
```

Only the frontend port is published by default. MinIO console / Postgres can be
exposed through an opt-in `docker-compose.override.yml` for debugging.

## 3. Backend modules

| App             | Responsibility                                                                  | Key models (planned)                       |
|-----------------|----------------------------------------------------------------------------------|--------------------------------------------|
| `core`          | Request IDs, health, error envelope, `TenantOwnedModel`, tenant-scoped querysets | abstract bases only                        |
| `tenants`       | Firms, tenant resolution (`request.tenant`), RLS context                         | `Tenant`                                   |
| `accounts`      | Users, memberships, roles, cookie-JWT auth, OIDC-ready identity                  | `User`, `Membership`, `Invitation`         |
| `matters`       | Matters / folders; optional per-matter access restriction                        | `Matter`, `MatterAccess`                   |
| `documents`     | Upload validation, storage keys, lifecycle, dedup, deletion                      | `Document`                                 |
| `rag`           | Extraction, chunking, embeddings, **tenant-filtered** vector search              | `DocumentChunk` (pgvector)                 |
| `ai_engine`     | `LLMProvider` / `EmbeddingProvider` interfaces; Ollama + Fake adapters; prompts  | none                                       |
| `conversations` | Chat sessions, messages, citations, streaming                                    | `Conversation`, `Message`, `Citation`      |
| `audit`         | Append-only security & activity log                                              | `AuditEvent`                               |

Dependency direction (no cycles): `core ← tenants ← accounts ← matters ←
documents ← rag ← conversations`, with `ai_engine` used by `rag` and
`conversations`, and `audit` usable by everyone.

### Planned data model

```mermaid
erDiagram
    TENANT ||--o{ MEMBERSHIP : has
    USER ||--o{ MEMBERSHIP : has
    TENANT ||--o{ MATTER : owns
    MATTER ||--o{ MATTER_ACCESS : restricts
    MEMBERSHIP ||--o{ MATTER_ACCESS : grants
    TENANT ||--o{ DOCUMENT : owns
    MATTER ||--o{ DOCUMENT : contains
    DOCUMENT ||--o{ DOCUMENT_CHUNK : "split into"
    TENANT ||--o{ DOCUMENT_CHUNK : "denormalised tenant_id"
    TENANT ||--o{ CONVERSATION : owns
    USER ||--o{ CONVERSATION : starts
    CONVERSATION ||--o{ MESSAGE : contains
    MESSAGE ||--o{ CITATION : cites
    CITATION }o--|| DOCUMENT_CHUNK : references
    TENANT ||--o{ AUDIT_EVENT : scopes

    MEMBERSHIP { uuid id  enum role "owner|admin|member|viewer" }
    DOCUMENT { uuid id  string sha256  enum status  string storage_key }
    DOCUMENT_CHUNK { uuid id  int page  text content  vector embedding }
```

`DocumentChunk` deliberately duplicates `tenant_id` and `matter_id` so the
vector search can filter on them in the same SQL statement as the similarity
ordering (no post-filtering of results that already crossed a boundary).

## 4. Key flows

### 4.1 Authenticated, tenant-scoped API request

```mermaid
sequenceDiagram
    participant B as Browser
    participant N as Next.js
    participant D as Django
    participant P as PostgreSQL
    B->>N: GET /api/v1/documents (cookie, X-Tenant-ID hint)
    N->>D: proxied request
    D->>D: authenticate JWT from HttpOnly cookie
    D->>P: SELECT membership WHERE user=? AND tenant=? AND active
    alt no membership
        D-->>B: 404 (not 403 — do not confirm existence)
    else member
        D->>P: SET LOCAL app.current_tenant = <tenant uuid>
        D->>P: SELECT ... WHERE tenant_id = <tenant uuid>  (+ RLS)
        D-->>B: 200 JSON
    end
```

### 4.2 Document ingestion (Phases 5–6)

```mermaid
sequenceDiagram
    participant U as User
    participant D as Django
    participant S as MinIO
    participant P as PostgreSQL
    participant Q as Redis/Celery
    participant O as Ollama
    U->>D: POST /documents (PDF)
    D->>D: authz, size cap, magic bytes, sha256 dedup per tenant
    D->>S: put tenants/{tenant}/documents/{doc}.pdf
    D->>P: Document(status=PENDING)
    D->>Q: process_document(doc_id) on_commit
    Q->>P: reload Document, re-derive tenant from DB
    Q->>S: get object
    Q->>Q: extract text per page (pypdf, limits, timeout)
    Q->>Q: chunk (size/overlap, keep page numbers)
    Q->>O: embed chunks
    Q->>P: replace chunks atomically, status=READY
    Note over Q,P: any failure → status=FAILED + error code, no partial chunks
```

### 4.3 RAG question (Phases 7–8)

1. Authenticate; resolve tenant from membership; check matter access.
2. Embed the question.
3. `SELECT ... FROM rag_documentchunk WHERE tenant_id = :t AND matter_id = ANY(:allowed) AND document.status='READY' ORDER BY embedding <=> :q LIMIT :k` — the filter and the ranking happen **in the same query**.
4. Build the prompt: system rules → retrieved passages wrapped in delimited,
   labelled `<document>` blocks marked as untrusted → user question.
5. Call the LLM (streamed when possible); require answers to cite `[n]`
   markers; respond "not found in the provided documents" when context is
   insufficient.
6. Persist `Message` + `Citation` rows (doc, page, chunk) under the same tenant.

## 5. Frontend

Next.js App Router + TypeScript + Tailwind + shadcn/ui + TanStack Query.

- Same-origin only; tokens live in HttpOnly cookies, CSRF double-submit for
  mutations (`src/lib/api.ts`).
- Route groups (Phase 4): `(auth)/login`, `(app)/[tenant]/dashboard`,
  `documents`, `assistant`, `admin`, `audit`. Middleware redirects
  unauthenticated users; **the server remains the only authority** — hidden UI
  is never treated as access control.

## 6. AWS target mapping (Phase 10, not deployed)

See `../../mermaid-diagram.png` for the target landing zone.

| Local          | AWS                                    | Abstraction that makes the swap cheap              |
|----------------|----------------------------------------|----------------------------------------------------|
| MinIO          | S3 (SSE-KMS, Block Public Access)      | boto3 S3 client; `S3_ENDPOINT_URL` empty on AWS    |
| PostgreSQL     | RDS PostgreSQL + pgvector              | `DATABASE_URL`                                     |
| Redis          | ElastiCache (TLS)                      | `REDIS_URL`                                        |
| Containers     | ECS Fargate behind ALB                 | same images; config via env/Secrets Manager        |
| Ollama         | Bedrock or EC2 GPU (vLLM)              | `ai_engine` provider registry                      |
| `.env`         | Secrets Manager / SSM                  | env injection by ECS task definition               |
| —              | KMS                                    | S3/RDS encryption, later per-tenant keys           |
| stdout logs    | CloudWatch Logs                        | structured logs with request IDs                   |
| Django auth    | Cognito / OIDC (Keycloak)              | `User.external_subject`, pluggable authenticator   |

## 7. Repository layout

```
.
├── backend/                 Django modular monolith
│   ├── config/              settings (base/dev/test/prod), urls, celery, wsgi/asgi
│   ├── apps/                core, tenants, accounts, matters, documents,
│   │                        rag, ai_engine, conversations, audit
│   └── tests/               cross-app security + integration suites (Phase 9)
├── frontend/                Next.js App Router
├── docs/
│   ├── brief.md             product brief
│   ├── architecture/        this overview + security design
│   ├── adr/                 architecture decision records
│   └── roadmap.md           phase tracker
├── infra/terraform/         (Phase 10) module skeleton
├── docker-compose.yml       (Phase 2)
├── .env.example
└── .github/workflows/ci.yml
```
