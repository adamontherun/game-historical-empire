.PHONY: test lint type format format-check front-type front-lint front-test front-e2e check-all

test:
	uv run --project backend pytest -v

lint:
	uv run --project backend ruff check backend

type:
	cd backend && uv run pyright

format:
	uv run --project backend ruff format backend

format-check:
	uv run --project backend ruff format --check backend

front-type:
	cd frontend && npm run typecheck

front-lint:
	cd frontend && npm run lint

front-test:
	cd frontend && npm run test

front-e2e:
	cd frontend && npx playwright test

check-all: test lint type format-check front-type front-lint front-test
	@echo "check-all: backend + frontend gates green"
