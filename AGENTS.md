# Historical Empire — Agent Guide

> This is the implementation authority for AI agents working in this repo.
> Product vision is broader than the first playable. Build **one `BUILD_SPEC.md` Section at a time, in order, and stop at its gate.**

## 1. Project

Mobile-first economic strategy / tycoon game. Player builds a business dynasty across changing economic regimes by making one meaningful allocation decision per turn and experiencing deterministic, explainable consequences. Hosted on **Render** (FastAPI backend + web frontend).

Long-term promise: spot the next economic bottleneck before rivals — know when yesterday's winning strategy is obsolete.

## 2. Stack & Hosting

- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), `asyncpg`, Alembic (sync migrations), `httpx.AsyncClient`
- **Frontend:** Vite + React + TypeScript + TanStack Query (mobile-first, `390×844` must be excellent)
- **Package manager:** `uv` (`uv sync`, `uv run ...`) — matches [Beta Acid FastAPI Reference App](https://github.com/betaacid/FastAPI-Reference-App)
- **DB (from Section 16):** Postgres on Render. Before that: in-memory sessions only.
- **Hosting:** Render — backend as web service, frontend as static site. `render.yaml` added at Section 10/16.

## 3. Authority & Execution

Authority:

- `BUILD_SPEC.md` active Section — implementation authority (what to build now)
- `AGENTS.md` — standing engineering and agent rules (how to build)
- `DECISIONS.md` — durable decisions that refine the spec
- `STATE.md` — current handoff state (what is complete, what is next)

Precedence when rules conflict:

1. Currently active numbered Section in `BUILD_SPEC.md`
2. `DECISIONS.md`
3. `AGENTS.md` and global rules in `BUILD_SPEC.md` (Parts I–III)
4. Future Sections (context, not scope)
5. Older drafts

Protocol for every Section:

1. Read `BUILD_SPEC.md` fully, then the active Section again
2. Inspect repo + tests before changing anything
3. Create feature branch `section/<n>-<slug>` (e.g. `section/2-core-types`) from `main` before any code changes
4. Use `/plan` to create a draft plan
5. Exit/cancel the initial plan approval (do not approve the draft)
6. Use `/grill` to pressure-test the saved draft plan for scope creep, missing tests, premature abstraction
7. Revise the plan
8. Approve the final plan
9. Use `/goal` to implement only the approved Section
10. Run every acceptance check in that Section
11. Push the feature branch to GitHub `adamontherun` (`git push -u origin section/<n>-<slug>`)
12. Stop — do not auto-advance. Report files changed, commands, tests, risks, and the pushed branch URL.

Only the `Status` line of a Section may be updated after all gates pass.

## 4. Autonomy

- **Highly autonomous by default.** Do not check in frequently or ask for permission to proceed within an active Section. Make the smallest correct decision that satisfies the active Section's acceptance criteria and the conventions in this file.
- **Check in only when necessary:** ambiguous requirements where two reasonable interpretations would produce different accepted behavior, a blocked dependency (missing credential, external service down), or a decision that would meaningfully expand scope beyond the active Section.
- **After each Section:** push the feature branch created in §3 step 3 to GitHub (`adamontherun`), then stop, do not auto-advance. Report files changed, commands run, tests/checks run + results, pushed branch URL, and known risks/follow-ups — then wait for human go-ahead to start the next Section.

## 5. Repository Structure

```
backend/
  app/
    domain/          # pure business rules — sync, no I/O
    engine/          # simulation kernel — pure, deterministic
    routers/         # thin FastAPI routers — validate + delegate
    services/        # business logic — coordinates clients
    clients/
      database/      # DB operations (repository layer)
      networking/    # external API clients
    models/          # SQLAlchemy ORM models
    schemas/         # Pydantic request/response schemas
    errors/          # custom exceptions + handlers
    dependencies.py  # ONLY file that knows about `Depends`
    utils/           # stateless helpers
  tests/
    unit_tests/      # mocked — never touches DB/network
    integration_tests/ # real Postgres (rollback), real network
  main.py            # app factory, lifespan, router registration
  database.py        # async engine, session factory, get_db_session
frontend/            # Vite+React — minimal until Section 11
docs/
BUILD_SPEC.md
DECISIONS.md
AGENTS.md            # this file
```

Create abstractions after 2 concrete use cases. Do not scaffold future ages/systems early.

## 6. FastAPI Conventions (Beta Acid Reference App)

Follow https://github.com/betaacid/FastAPI-Reference-App exactly:

```
Router -> Service -> Database Client -> Database
                \-> Networking Client -> external API
```

- **Layers depend only downward.** Routers inject `DbSession` + clients, then pass them as plain args. Services/repositories never import `Depends`.
- **Plain functions over classes.** `async def add_new_character(input, db, swapi_client)` — not service classes. A class is justified only when it holds real state/resource (e.g. `SwapiClient` holding `httpx.AsyncClient` pool).
- **File naming:** `characters_service.py`, `characters_router.py` — not `characters.py` / `router.py`.
- **Async by default for I/O.** Routers, services, DB clients, networking clients are `async` with `AsyncSession` + `httpx.AsyncClient`. Pure `domain/`/`utils/` stays sync. Never block inside `async def` — no `requests.get`, no sync SQLAlchemy.
- **Shared `httpx.AsyncClient`** created once in `main.py` lifespan, closed on shutdown, injected via nested deps (`router -> get_swapi_client -> get_http_client -> request.app.state.http_client`).
- **Transactions:** boundary in `get_db_session` (commit on success, rollback on raise). Clients only `add`/`flush`. Never `commit` in a client.
- **Schemas vs models:** SQLAlchemy models in `app/models/`, Pydantic schemas in `app/schemas/` (app-facing `Create`/`Read` + external-API-facing shapes separately).
- **Errors:** HTTP failures wrapped into app exceptions at client boundary (`SwapiCharacterError` pattern) in `app/errors/`, handled centrally in `main.py`.

Example:

```python
# routers/characters_router.py — thin, injects, delegates
@characters_router.post("/", response_model=StarWarsCharacterRead)
async def create_character(
    input_character: StarWarsCharacterCreate,
    db: DbSession,
    swapi_client: SwapiClientDep,
) -> StarWarsCharacterRead:
    return await characters_service.add_new_character(input_character, db, swapi_client)


# services/characters_service.py — plain async function, no FastAPI imports
async def add_new_character(
    input_character: StarWarsCharacterCreate,
    db: AsyncSession,
    swapi_client: SwapiClient,
) -> StarWarsCharacterRead:
    ...


# dependencies.py — ONLY place with Depends
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
SwapiClientDep = Annotated[SwapiClient, Depends(get_swapi_client)]
```

## 7. Global Technical Rules (from BUILD_SPEC.md)

- **Simulation authority:** backend engine is source of truth. Clients send commands, never state mutations. Engine decides cost/validity/effects.
- **Determinism:** same `state + command + world_context + seed` → same result. Never use global `random`. Derive substreams via stable hash (BLAKE2/SHA-256) over `run_seed + ruleset_version + turn + namespace + entity_id + ordinal`. Never `hash()`.
- **Canonical numerics:** `Money=int`, `Quantity=int`, `BasisPoints=int` (10_000 = 100%), `PriceMilliunits=int`. Transient `Decimal` must be quantized explicitly. Rounding is deterministic and tested. Nothing negative where invalid.
- **Pure engine:** `backend/app/engine` + `domain` import no FastAPI/React/SQLAlchemy/Clerk/LLM code. Shape: `resolve_turn(state, command, world_context, rng_context) -> TurnResolution(next_state, domain_effects, causal_trace, player_outcome)`. Testable without network/DB.
- **Causal trace:** emitted structurally during resolution, not reconstructed by diffing. Flat deltas are insufficient — chain/edges needed. Player-facing drivers (≤3) derived deterministically from trace.
- **Author cause, simulate consequences.** `drought -> farm output -> supply -> price pressure -> price` — never `price *= 1.4`.

## 8. Coding Standards

- **Lint/format/type:** `ruff` (lint + format) + `pyright` strict. These are Section 1 gates — CI fails on violations.
- **Docstrings:** Google-style only on public `engine`/`domain`/`services` APIs. No docstrings on trivial routers/clients.
- **Comments:** concise, never long chain-of-thought. Code is the truth.
- **Type hints:** required on all public functions. `pyright` strict passes.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `chore:`). No direct pushes to `main` without review (when branch protection exists).

## 9. Testing

User preference: **heavy unit coverage for business logic/services, some integration, limited Playwright — no hard gate yet, report only.**

Priority (BUILD_SPEC.md §16):

```
VERY HIGH  engine unit tests
HIGH       invariants / property tests
HIGH       headless simulation tests
MODERATE   API integration tests
LIMITED    critical Playwright browser flows
```

- **Unit:** `tests/unit_tests/` — every layer isolated. Injected deps via `dependency_overrides`, plain functions via `@patch`. `httpx.MockTransport` for networking clients. No real DB/network. Add `pytest-asyncio` only when genuine async tests are introduced.
- **Integration:** `tests/integration_tests/` — real Postgres + real external calls. `integration_client` overrides `get_db_session` to **rollback** instead of commit. Requires `.env` with `DATABASE_URL`. Lazy engine creation so imports don't need DB.
- **Playwright:** only critical path (start → 5-turn completion, mobile `390×844` + desktop smoke). Screenshots for first decision / drought warning / drought reveal / summary. No coverage gate on UI.
- **Coverage:** tracked (`pytest --cov`) but **not blocking** until Section 3–4 kernel stabilizes. Target when gating is added: `90%+ engine/domain/services`, `80%+ overall`.

Commands:

```bash
uv sync --project backend
make test          # = pytest
make lint          # = ruff check backend
make type          # = pyright
make format-check  # = ruff format --check backend
```

## 10. API Contract (from Section 10, for reference)

In-memory sessions until Section 16. Three endpoints only:

```
POST /api/v1/games
GET  /api/v1/games/{game_id}
POST /api/v1/games/{game_id}/choices/{choice_id}
```

- `GameView` is presentation-oriented (game_id, revision, turn, signal, player/empire/market summaries, route, rival headlines, choices, outcome). Frontend never recomputes economy.
- Mutating requests include `expected_revision` — stale revision fails with conflict. Invalid commands never mutate.

OpenAPI at `/docs` (FastAPI default).

## 11. Frontend Rules (from Section 11)

- Mobile-first cards/typography/hierarchy, not dense tables. Required decision info visible without detail drill-down.
- One major action per turn — opportunity cost is core.
- Outcome reveal is a payoff moment (time advances → world → numbers → drivers → causal why → rivals → next threat).
- Empire tableau shows compounding visibly (names/scale/operation counts), not free building placement.
- Prevent double-submit on commit.

## 12. Render Deployment

- Backend: `uvicorn main:app` with `DATABASE_URL` + `PYTHON_VERSION=3.12`. `alembic upgrade head` runs on deploy (sync connection in `alembic/env.py`).
- Frontend: Vite static build, `VITE_API_URL` pointing to backend.
- Keep `render.yaml` minimal — don't introduce Docker unless Section 16 requires it.

## 13. What Not To Do

- Don't implement future Sections early (8 ages, spoilage, credit, brands, automation, generic content DSL, LLMs for rival decisions) — `BUILD_SPEC.md` forbids it.
- Don't put executable formulas in content JSON — Python owns formulas, content supplies parameters.
- Don't chase repo-wide 100% coverage.
- Don't let LLMs determine rival money/investments/state — deterministic scoring functions only.
