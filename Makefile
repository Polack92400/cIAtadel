# Developer shortcuts. Run `make help`.
COMPOSE := docker compose

.PHONY: help env up down reset logs ps test-backend test-e2e lint check

help:
	@echo "env           create .env with random secrets (once)"
	@echo "up            build and start the whole stack (http://localhost:3000)"
	@echo "down          stop the stack (data is kept)"
	@echo "reset         stop the stack and DELETE all data volumes"
	@echo "logs          follow backend + worker logs"
	@echo "ps            service status"
	@echo "test-backend  backend + security test suite (in docker, against PostgreSQL)"
	@echo "test-e2e      Playwright end-to-end tests against the running stack"
	@echo "lint          ruff + eslint + typecheck (local toolchains)"

env:
	./scripts/setup-env.sh

up: env
	$(COMPOSE) up -d --build --wait
	@echo "cIAtadel is up: http://localhost:3000"

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f backend worker

ps:
	$(COMPOSE) ps -a

test-backend: env
	$(COMPOSE) --profile test run --rm --build backend-test

test-e2e:
	cd frontend && npm ci && npx playwright install chromium && npx playwright test

lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint && npm run typecheck

check: lint test-backend
