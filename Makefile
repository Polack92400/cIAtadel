# Developer shortcuts. Docker targets become available in Phase 2.
.PHONY: help backend-install backend-lint backend-test frontend-install frontend-check check

help:
	@grep -E '^[a-z-]+:' Makefile | cut -d: -f1

backend-install:
	cd backend && pip install -r requirements-dev.txt

backend-lint:
	cd backend && ruff check . && ruff format --check .

backend-test:
	cd backend && pytest

frontend-install:
	cd frontend && npm ci

frontend-check:
	cd frontend && npm run lint && npm run typecheck && npm run build

check: backend-lint backend-test frontend-check
