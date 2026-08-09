# Backend — Agent Guide

> Scope: `backend/` only. Root `AGENTS.md` + `BUILD_SPEC.md` still apply. Follow [Beta Acid Reference App](https://github.com/betaacid/FastAPI-Reference-App).

## Layout

```
backend/
  main.py                 # app factory, lifespan (httpx client), routers, error handlers
  database.py             # async engine, session factory, get_db_session
  app/
    domain/               # pure rules — sync, no FastAPI/SQLAlchemy/httpx
    engine/               # simulation kernel — deterministic, integer state
    routers/              # thin — validate + delegate to services
    services/             # business logic — plain async functions
    clients/
      database/           # DB ops — plain async functions
      networking/         # external calls — e.g. SwapiClient class + parse fns
    models/               # SQLAlchemy ORM
    schemas/              # Pydantic Create/Read + external shapes
    errors/               # app exceptions + handlers
    dependencies.py       # ONLY file with `Depends` (DbSession, SwapiClientDep)
    utils/                # stateless helpers
  tests/
    unit_tests/           # mocked — dependency_overrides + @patch + MockTransport
    integration_tests/    # real Postgres + rollback
  alembic/                # from Section 16
```

## Conventions

- **Functions over classes.** `async def add_new_character(data, db, client)` — not `CharacterService`. Class only for real resources (e.g., `SwapiClient(http_client)`).
- **Naming:** `characters_service.py`, `characters_router.py`.
- **Async:** routers/services/clients are `async`; `domain`/`utils` are sync. No blocking calls in `async def`.
- **Deps:** routers inject `DbSession` + `*Dep` from `dependencies.py`, pass plain `AsyncSession` downstream. `get_db_session` owns commit/rollback; clients only `add`/`flush`.
- **Engine purity:** `app/engine` + `app/domain` must not import `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`.

## Engine Rules (BUILD_SPEC.md §§11–14)

- `resolve_turn(state, command, world_context, rng_context) -> TurnResolution(next_state, domain_effects, causal_trace, player_outcome)`
- Deterministic substreams via `hashlib.blake2b`/`sha256` over `run_seed | ruleset_version | turn | namespace | entity_id | ordinal`. No `random`, no `hash()`.
- Canonical `int` state: `Money`, `Quantity`, `BasisPoints` (10_000 = 100%), `PriceMilliunits`. Quantize `Decimal` explicitly; test rounding.
- Emit `CausalTrace` during resolution — don't diff snapshots. Player drivers (≤3) derived deterministically from trace.

## Testing

```bash
uv sync
uv run pytest tests/unit_tests/ -v
uv run pytest tests/integration_tests/ -v  # needs DATABASE_URL
uv run pytest -v --cov=app
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

- Unit: `dependency_overrides` replaces `get_db_session`; `@patch("app.services.xxx.fn")` for routers; `httpx.MockTransport` for networking clients.
- Integration: `integration_client` fixture overrides `get_db_session` to rollback where prod would commit.

## When to Add DB

Not until `BUILD_SPEC.md` Section 10 (in-memory API) / Section 16 (Postgres + Alembic). Lazy engine in `database.py` so `import app` never requires `DATABASE_URL`.
