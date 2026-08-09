.PHONY: test lint type format format-check

test:
	uv run --project backend pytest -v

lint:
	uv run --project backend ruff check backend

type:
	uv run --project backend pyright

format:
	uv run --project backend ruff format backend

format-check:
	uv run --project backend ruff format --check backend
