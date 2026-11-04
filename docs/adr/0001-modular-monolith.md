# ADR 0001 — Modular monolith

**Context.** A POC with one team, strong consistency needs (documents, chunks,
permissions in one transaction) and a hard isolation requirement.

**Decision.** One Django project with nine apps (`core`, `tenants`,
`accounts`, `matters`, `documents`, `rag`, `ai_engine`, `conversations`,
`audit`) and one Celery worker running the same codebase. Apps communicate via
Python service functions, not HTTP.

**Consequences.** Simple deployment (two process types from one image on
ECS). Tenant checks live in one place. Apps must respect the dependency
direction documented in `architecture/overview.md`; extraction into services
stays possible later because `ai_engine` and `rag` are behind interfaces.
