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
4. **Enter plan mode before any code changes** — use the `/plan` skill (Muse Code: `muse.read_skill("plan")` / `/plan`) to create a draft plan saved to `docs/plans/`. Do not write, edit, or scaffold any Section code until the draft plan exists. The trigger "let's work on the next section" (or any identification of the next Section) means: create the branch, then immediately enter plan mode — not implementation.
5. Approve / Request changes — single gate (revise until approved). If the draft has scope creep, missing tests, or premature abstraction, surface it as open questions in the plan itself — no separate `/grill` skill required. **Do not start implementation until the plan is approved.**
6. Implement only the approved Section
7. Run every acceptance check in that Section
8. **Update `STATE.md` (and `DECISIONS.md` if new durable decision) to current reality in the same commit as the Section — see §15 Freshness Contract. Copy actual `make test`/`make lint`/`make type`/`make format-check` output, file tree under `What exists`, and `Boundaries` into `STATE.md`. Never leave `BUILD_SPEC.md` marked `COMPLETE` while `STATE.md` still reflects the previous Section.**
9. Push the feature branch to GitHub `adamontherun` (`git push -u origin section/<n>-<slug>`)
10. Stop — do not auto-advance. Report files changed, commands, tests, risks, and the pushed branch URL. The report's `Last known green` must match the just-pushed commit's gates.

Only the `Status` line of a Section may be updated after all gates pass.

> **Hard gate:** No source edits (`backend/`, `frontend/`, `STATE.md`, `DECISIONS.md` beyond the branch itself) before steps 4–5 are complete. If you catch yourself about to code after step 3, stop and produce the plan first.

> **Freshness gate:** Do not push a Section branch while `STATE.md` is stale (test counts, file list, `Boundaries`, `Last known green`, or `BUILD_SPEC.md Status` mismatch reality). If you discover staleness at any point in the session, fix `STATE.md` immediately in the next commit — even if the current task is not a Section.

## 4. Autonomy

- **Highly autonomous by default.** Do not check in frequently or ask for permission to proceed within an active Section. Make the smallest correct decision that satisfies the active Section's acceptance criteria and the conventions in this file.
- **Check in only when necessary:** ambiguous requirements where two reasonable interpretations would produce different accepted behavior, a blocked dependency (missing credential, external service down), or a decision that would meaningfully expand scope beyond the active Section.
- **After each Section:** push the feature branch created in §3 step 3 to GitHub (`adamontherun`), then stop, do not auto-advance. Report files changed, commands run, tests/checks run + results, pushed branch URL, and known risks/follow-ups — then wait for human go-ahead to start the next Section.

## 5. Git workspace safety

Before starting any Section:

1. Verify this is the real repository checkout:
   - `git rev-parse --show-toplevel`
   - `git remote get-url origin`
   - `git status --short`
   - `git branch --show-current`

2. Fetch the remote and start the Section branch from the current remote main:
   - `git fetch origin`
   - ensure local `main` matches or can fast-forward to `origin/main`
   - create `section/<n>-<slug>` from `origin/main`

3. Never create a temporary clone, temporary Git repository, or `/tmp` copy as a workaround for Git sandbox restrictions.

4. Never push commits from a temporary copy of the workspace.

5. If the sandbox prevents writing `.git`, creating/switching a branch, committing, or pushing:
   - stop Git operations
   - preserve all working-tree files
   - tell the user the exact Git command that must be run outside Muse
   - after the user runs it, re-read Git state in the original workspace before continuing

6. Do not run `git init` inside an existing project merely because Git commands fail. First determine whether `.git` is missing, inaccessible, sandboxed, or the checkout is incorrect.

7. Before declaring a Section complete, verify:
   - current branch is `section/<n>-<slug>`
   - working tree contains only intended changes
   - the Section commit exists locally
   - the remote Section branch points to the pushed Section commit

The original project directory is authoritative. Build/cache workarounds may use `/tmp` when appropriate; Git repository state must not.

## 6. FastAPI Conventions

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

## 13. Knowledge Graph (Graphify)

Project has a deterministic knowledge graph at `graphify-out/` (tree-sitter AST, local-first, no LLM for code). Prefer the graph over raw grep for codebase questions.

Rules:

- If `graphify-out/graph.json` exists: start with `graphify query "<question>"` (BFS, ~2k token budget). Use `graphify path "<A>" "<B>"` to trace two concepts and `graphify explain "<concept>"` for one node. Try `graphify god-nodes --top 10` for hubs; raise budget with `--budget 4000` if truncated.
- Only read `graphify-out/GRAPH_REPORT.md` for broad architecture; load `graphify-out/graph.json` / `graph.html` directly only if query/path/explain was insufficient. If `graphify-out/wiki/index.md` exists, use it for broad navigation.
- After touching `backend/` or `docs/`: run `graphify update .` (code-only, no API cost). A `post-commit` hook also rebuilds automatically; full LLM re-extraction is `graphify extract .` (needs `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GEMINI_API_KEY`) and `graphify extract . --code-only` for code alone.
- Visual: `open graphify-out/graph.html` (force-directed, click/filter/search).
- Skills are at `.claude/skills/graphify/SKILL.md` + `.agents/skills/graphify/SKILL.md`; Muse hook guard is in `.claude/settings.json` — this `AGENTS.md` section is the binding for Muse.

## 14. What Not To Do

- Don't implement future Sections early (8 ages, spoilage, credit, brands, automation, generic content DSL, LLMs for rival decisions) — `BUILD_SPEC.md` forbids it.
- Don't put executable formulas in content JSON — Python owns formulas, content supplies parameters.
- Don't chase repo-wide 100% coverage.
- Don't let LLMs determine rival money/investments/state — deterministic scoring functions only.

## 15. STATE.md Freshness Contract

`STATE.md` is the live handoff, not a historical log. It must describe the **current** commit, not the previous Section.

**When to update (same commit as the code change):**

- Every Section completion — `STATE.md` header `Section N — COMPLETE`, `What exists` file tree, `Boundaries` (reliability `10000` vs `9000`, `delay_turns` constraint, `cash_after_trade`/`inventory_after_trade`, `price_value_effect` parents, arbitrage `arbitrage_margin` vs `before_price`), `Normal verification` / `Last known green` gate results, and `BUILD_SPEC.md Status` line must be updated together. Never commit `BUILD_SPEC.md: Status COMPLETE` without updating `STATE.md` in the same commit.
- Any fix that changes gate results (test count, `Boundaries`, file list) — update `STATE.md` in that same fix commit, even if the task description says "do not otherwise change Section 5 behavior".
- Any session where you touch `backend/app/domain`, `backend/app/engine`, `backend/tests`, `BUILD_SPEC.md`, or `DECISIONS.md` — re-read `STATE.md` before finishing and sync it.

**What counts as stale (fix immediately, do not push stale):**

- `Last known green` test count / file count / `ruff`/`pyright` output does not match the just-run `make test` / `make lint` / `make type` / `make format-check` output.
- `What exists` tree omits a new file (e.g. `test_two_markets_route.py`, `RouteState`, `TURN_ORDER` extension) or still lists a removed one.
- `Boundaries` still describes the old `reliability_bps=9000` / `delivered==effective unless <9000` / `delay_turns=0` unconstrained / `price_value_effect parents inventory+price` / `shipment parents route_capacity,inventory` / `trade_arbitrage net only` after those were fixed to `10000` / `delivered = effective * reliability_bps //10000` / `delay_turns le=0` / `inventory_after_trade+price` / `cash_after_trade` / `arbitrage_margin at resolved prices`.
- `BUILD_SPEC.md Status` says `COMPLETE` while `STATE.md` header still says `Section N-1`.

**How to keep it fresh:**

- After `make test` / `make lint` / `make type` / `make format-check` pass, copy the **actual** observed output into `STATE.md` (`79 passed`, `21 files already formatted`, `0 errors`, etc.) — do not reuse the previous Section's numbers.
- After any `cargo`/`uv` / file-tree change, regenerate the `What exists` tree from `ls`.
- Verify before push: `git diff --cached --stat` must include `STATE.md` whenever `BUILD_SPEC.md`, `backend/app/domain/types.py`, `backend/app/engine/turn.py`, `backend/app/domain/trace.py`, or any `backend/tests/*.py` is in the same push.

If you discover `STATE.md` is stale mid-session (including after a `fix:` commit that only updated code), treat it as a blocking defect: update `STATE.md` in the next commit and push before stopping.
