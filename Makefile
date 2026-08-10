.PHONY: test lint type format format-check

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
