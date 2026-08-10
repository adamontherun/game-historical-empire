# Section 10 — Minimal FastAPI Boundary — Plan

**Date:** 2026-08-10
**Branch:** `section/10-fastapi-boundary` (from `origin/main` at `0d28df6` Section 9 COMPLETE)
**Spec Authority:** `BUILD_SPEC.md` Section 10 (Status: NOT STARTED) + global §§10–16 + `DECISIONS.md` 015/016 + `STATE.md` §9 + `AGENTS.md` §§6/10
**Related:** `backend/app/domain/types.py`, `backend/app/domain/trace.py`, `backend/app/domain/pressure.py`, `backend/app/engine/prototype.py`, `backend/app/engine/turn.py`, `backend/app/engine/actor.py`, `backend/app/engine/rivals.py`, `backend/tests/test_engine_purity.py`

---

## Goal

Expose the existing deterministic 5-turn game through exactly three in-memory endpoints while keeping `backend/app/engine` + `backend/app/domain` pure, satisfying AC1–AC6 so a client can play the full prototype without reproducing economic formulas.

---

## Success Criteria (maps to Section 10 AC + global rules)

1. **Five-turn creation & completion (AC1).** `POST /api/v1/games` creates a game; five successive `POST …/choices/{choice_id}` with correct `expected_revision` advance `turn 0→5` and then present a `completion_summary`. Any API test doing `1× create + 5× choices` reaches `turn == turn_limit == 5`. GET between turns reflects mutated state.
2. **Invalid commands cannot mutate (AC2).** An unknown or not-currently-offered `choice_id` returns 4xx without calling `resolve_turn` and without incrementing `revision` or `turn`. Verified by `GET` before/after showing identical state.
3. **Stale revisions cannot mutate (AC3).** Every mutating POST carries `expected_revision: int`; server compares atomically to current `revision`. Mismatch → `409 Conflict` with no mutation (GET after still same).
4. **No client formula needed (AC4).** `GameView` carries every number the frontend would otherwise compute — see Key Decision K4 for operational test. One API test can render "why" entirely from response fields.
5. **Engine stays pure (AC5).** `backend/app/engine/*.py` + `backend/app/domain/*.py` import no `fastapi`/`sqlalchemy`/`httpx`/`asyncpg`/`alembic`. Enforced by a failing test, not convention.
6. **No regressions (AC6).** Existing 133 backend tests remain green; `ruff check`, `ruff format --check`, `pyright --strict` stay 0 errors.

---

## Context And Current Facts

- `STATE.md` §9: `GameState{turn, run_seed, ruleset_version, player{cash, inventory{grain}, farm_capacity, storage_capacity}, market{Home + regional_output}, river_market, route{transport 300, capacity 20, reliability 10000, established}}`, `PlayerCommand{7 types: expand_farm, build_granary, buy_grain, sell_grain, hold, secure_route, ship_grain}` with optional `quantity`. `FiveTurnGame` owns `GameState` + `history: tuple[TurnResolution,5]` + `rivals` (`rivals.py` session-owned, integer bps scoring, structured `next_world_known`). `PRESSURE_ARC: tuple[PressureState,5]` (activation_turn==index, `PRESSURE_NORMAL/DROUGHT` constants), `resolve_turn(state, command, pressure, rng_context) -> TurnResolution{next_state, domain_effects, causal_trace{nodes, edges}, player_outcome{wealth_delta, drivers ≤3}}`. Price-taking boundary explicit: sales/shipments are price-taking. Determinism via `rng_for` (BLAKE2, no global random). Tuned start state `storage 130`, `transport 300`.
- Current backend has **no** `app/main.py`, no `app/api/`, no `app/schemas/`, no `app/dependencies.py`, no `fastapi` dependency yet in `pyproject.toml` (evidence: `backend/pyproject.toml` dependencies only `pydantic>=2.7`, no `fastapi`, no `app/main.py` found via `ls backend/app/*.py`). `DECISIONS.md 006` says "in-memory sessions until Section 16" — matches Section 10 scope.
- `backend/tests/test_engine_purity.py:8` already forbids imports of `{"fastapi","sqlalchemy","httpx","asyncpg","openai","clerk"}` via AST walk over `ENGINE_DIR + DOMAIN_DIR`. Currently all 133 tests pass; that test is the pattern to reuse.
- `Makefile` gates: `make test` = `uv run --project backend pytest -v`, `make lint` = `ruff check`, `make type` = `pyright`, `make format-check`. Plan must keep these.
- `FiveTurnGame.available_commands() -> list[str]` exists but returns raw type names only (no quantity, no choice identity). Section 10's `available_choices` and `choice_id` need to replace/augment that at the API boundary — the engine already enumerates all 7 verbs; the API must map each to a stable `choice_id` that maps 1:1 to a `PlayerCommand` for the current turn, including quantity-qualified variants (buy/sell/ship).
- `TURN_ORDER = "pressure_stage -> world -> command -> production -> regional_output -> home_supply -> … -> valuation"` — relevant because `latest_outcome.drivers` already derive deterministically from trace (global §14).

---

## Constraints And Non-goals

**Must satisfy:**
- In-memory sessions only; no `DATABASE_URL`, no `SQLAlchemy`, no `AsyncSession`, no `Alembic`, no migration.
- Exactly three endpoints (spec verbatim): `POST /api/v1/games`, `GET /api/v1/games/{game_id}`, `POST /api/v1/games/{game_id}/choices/{choice_id}`. No history endpoint, no `/advisor`, no free-text draft.
- `expected_revision` optimistic concurrency on **every** mutating POST; stale fails deterministically.
- `GameView` is presentation-oriented — frontend recomputes nothing economic.
- `engine` + `domain` remain import-free of web/DB; transaction boundary is in-memory atomic check, not DB transaction.
- Integer numerics only (`Money/Quantity/PriceMilliunits/BasisPoints` already constrained); rounding tested; no new state field or verb, no generic content DSL.

**Explicitly out of scope (do not build):**
- PostgreSQL, SQLAlchemy, Alembic, `render.yaml`, authentication/Clerk, LLM endpoints, history endpoint, cloud deployment. Section 11 React is later — no frontend scaffolding beyond what `GameView` makes possible.

---

## Key Decisions

### K1 — Where `GameView` lives (pure engine boundary, global §13)

- **Decision:** `GameView` + `ChoiceView` + `OutcomeView` live **outside** engine/domain, in `backend/app/api/schemas.py` (or `backend/app/schemas/game_view.py` — both outside `domain`/`engine`). `backend/app/api/` owns FastAPI types; it may *import* `GameState`/`TurnResolution`/`PressureState` to map, but `domain`/`engine` never import `app/api/*` or `fastapi`.
- **Evidence:** `engine` today imports only `pydantic` + domain types + `rng/rounding/pressure`. Adding `fastapi` there would trip `test_engine_purity.py:8` (already enumerates forbidden `fastapi`). Mapping lives in `backend/app/api/mappers.py` (pure function `game_to_view(session) -> GameView`) and is tested without HTTP.
- **Rejected:** Putting `GameView` in `domain/types.py` — would couple presentation to canonical state and force engine to know about `available_choices` (a view concern). Putting it in `engine/prototype.py` — prototype is orchestrator, not view.
- **Consequence:** AC5 guard remains simple: forbidden-import test covers the same `ENGINE_DIR + DOMAIN_DIR` and passes even after new API layers are added.

### K2 — `choice_id`: what it IS and how it prevents mutation on invalid input (AC2)

- **Decision:** A `choice_id` is a **stable, server-derived identifier for one concrete `PlayerCommand` legal at the current turn's view**. Canonical form:
  - parameterless verbs: `expand_farm`, `build_granary`, `hold`, `secure_route`
  - quantity verbs: `buy_grain:20`, `sell_grain:30`, `ship_grain:10` — `f"{type}:{quantity}"` (quantity is the resolved affordable headroom-bounded amount the view offered that turn, not an arbitrary client-supplied int).
  `GameView.available_choices: list[ChoiceView{id, label, kind, quantity?}]` enumerates the **exact set** accepted by `POST …/choices/{choice_id}` at this `revision`. The route parameter is the map key: server does `choice = session.choice_map[choice_id]` (built from `available_choices`); if missing → `404 Not Found`, no engine call, no state change. Valid choices are the ones the engine *would* accept for this turn — empty or unknown IDs never reach `resolve_turn`.

- **What the API rejects vs what the engine bounds:**
  - **API rejects (no mutation):** unknown `choice_id`, choice from prior revision (stale choice), `choice_id` not in current `available_choices`, missing/mismatched `expected_revision`.
  - **Engine bounds (still no negatives, but via trace):** `buy_grain` beyond cash/storage → `resolve_buy` clamps `actual = min(requested, affordable, space)` with reason `insufficient_cash`/`insufficient_storage` (actor.py:68–128); `ship_grain` beyond capacity/inventory/affordable → `resolve_shipment`; `sell_grain` beyond inventory → `resolve_sell` clamped. These are **not** HTTP errors — they are economic outcomes visible in `causal_trace`/`domain_effects`/`player_outcome`. The API must **not** re-implement affordability checks; it just maps `choice_id` → `PlayerCommand{type, quantity}` and delegates. Reason codes surface in `latest_outcome`.
  - **Backward-compat note:** Section 8's compatibility shim that quietly reinstated a removed string API is the anti-pattern: if a verb is removed from `PlayerCommand`, its `choice_id` must disappear from `available_choices` and POSTing it must 404 — not be aliased.

- **Rejected alternatives:** Free-form body `{type, quantity}` with `choice_id` ignored — breaks "invalid cannot mutate" because a client can invent quantities; server-side revalidation would duplicate engine logic. Pure type without quantity — leaves quantity verbs underspecified. Chosen mapping keeps the path identifier as the authority and keeps quantity server-chosen (client does not invent `quantity=9999`).

- **Quantity strategy for buy/sell/ship choices:** Mirror `engine/harness.py`'s "competent" sizing without overfitting: offer at most one buy amount `min(space - harvest_headroom, affordable, 80)` and one sell/ship per turn at 20/10/50-like buckets already in trace. Exact amounts are view policy, not engine rule; offering `10, 20, 50, 150` buckets would multiply `available_choices` unnecessarily. Start with **one** quantity-qualified choice per kind (plus `hold`) — 4–7 choices max, matching "one major action per turn" (§5). Validate with the harness's `min(space, affordable, 80)` capping.

### K3 — Revision semantics (where, increment, failure, atomicity)

- **Where:** `revision: int` lives on the **session envelope**, not on canonical `GameState`. `GameState.turn` increments via `resolve_turn` (turn 0→5); `revision` is independent and starts `0` at creation. Envelope is `GameSession{game_id: str, revision: int, game: FiveTurnGame, created_at, revision_history}` stored in `backend/app/api/sessions.py: SESSION_STORE: dict[str, GameSession]` guarded by an `asyncio.Lock` (or `threading.Lock` for in-memory single-process).
- **Increment:** Exactly `+1` on each **successful** `POST …/choices/{choice_id}`. `GET` never increments. `POST /games` creates `revision=0`. Failed validations (stale, invalid choice_id, game complete) leave `revision` unchanged.
- **Failure response:** `POST` body `{expected_revision: int}`. If `expected_revision != session.revision` → `409 Conflict` (not 400/422). Body: `{"detail":"conflict: expected_revision X != current Y","expected_revision":X,"current_revision":Y}`. No engine call, no mutation, no `revision` bump. Game-complete (revision==turn_limit already mutated) on POST → `409` or `400` with `detail: "game complete"` (prefer `409` consistently; document one).
- **Atomicity:** The check `if body.expected_revision != session.revision: raise 409` and the subsequent `game.submit(choice) + revision+=1` execute under the same lock (`async with SESSION_LOCK:`). Without this, two concurrent correct-revision requests could both read `revision=2` and both commit, skipping a revision. In CPython single-process in-memory, the lock makes the operation atomic. Test with concurrent `asyncio.gather` of two same-revision POSTs asserts one 200, one 409.
- **Rejected:** `If-Match` header / ETag instead of body field — spec says "Mutating requests include an expected state revision" (body), so body field is canonical. Returning `412 Precondition Failed` — plausible but spec says "must fail" without code; `409 Conflict` is conventional for optimistic concurrency and matches DECISIONS.md 005's "optimistic revision concurrency".

### K4 — AC4 "no frontend formula needed" — operational test

- **Risk:** Prior sections were bitten by unfalsifiable ACs. This plan makes AC4 falsifiable.
- **Decision — what GameView must carry:** Every field the spec's suggested view lists, concretely:

```python
class GameView(BaseModel):
    game_id: str
    revision: int
    turn: int
    turn_limit: int = 5
    signal: str                          # pressure signal prose for this turn
    pressure_stage: str                  # "early_dry" etc (structured, not parsed prose)
    world: WorldCondition                # "drought" | "normal"
    player_summary: {cash, inventory_grain, farm_capacity, storage_capacity, wealth}
    empire_summary: {operations: list[{id, kind, capacity, level}], name_stage?}  # compounding visible without placement
    home_valley_market: {supply, demand, base_price, current_price, responsiveness}
    river_town_market: {supply, demand, base_price, current_price}
    route_status: {established, capacity, transport_cost_per_unit, reliability_bps, affordable_ship?, next_margin}
    rival_headlines: {mira: str, daran: str} | None
    available_choices: list[ChoiceView{id, label, kind, quantity?, reason_code_hint?, affordable?}]
    latest_outcome: {
        wealth_delta, inventory_delta, price_delta,
        drivers: tuple[OutcomeDriver{label, impact_money, impact_bps, reason_code, causal_node_ids}, 0..3],
        domain_effects: list[DomainEffect{metric, before, after, delta, reason_code}],
        # causal_trace omitted from default GameView if large; expose as `debug_trace: CausalTrace` under ?trace=1 or in latest_outcome for reveal
    } | None  # None before first turn
    completion_summary: StrategicSummary | None  # populated when turn==turn_limit
```

Key properties:
  - `wealth`/`price`/`inventory` already computed by `turn.py` wealth decomposition (`wealth_delta = cash_effect + quantity_value_effect + price_value_effect`) — frontend never does `value = qty*price//1000`.
  - `available_choices[*].label` is human text generated at the boundary (e.g. "Buy 20 grain — 3,400 cash") using `cost_for_quantity(quantity, current_price)` (actor) — frontend does not recompute cost.
  - `route_status.next_margin = river_price - transport - home_price` at resolved price is precomputed (like `arbitrage_margin` in turn.py) — frontend does not recompute margin.
  - `rival_headlines` are pre-rendered strings from `RivalTurnResult.headline`.
  - Full `causal_trace.nodes: tuple[CausalNode{id, label, kind, before, after, delta, reason_code, parent_ids}>` is included in `debug_trace` so advisor/reveal can cite `pressure:{id}:{stage}` etc without diffing (global §14). At minimum `latest_outcome.drivers[*].causal_node_ids` must reference trace nodes.

- **Operational test (falsifiable):** A "no-formula" API test `test_frontend_needs_no_formula` will:
  1. `POST /games {"run_seed":"formula-test","ruleset_version":"1.0"}` → asserts `GameView` contains `player_summary.wealth`, `home_valley_market.current_price`, `route_status`, `available_choices[*].id`, and `latest_outcome is None` pre-turn.
  2. For each of 5 turns: pick first `available_choices[0].id`, `POST …/choices/{id} {"expected_revision": rev}` → assert response contains `latest_outcome.drivers` (≤3, each has `impact_money`, `impact_bps`, `label`, `reason_code`), `domain_effects`, and that `player_summary.cash + inventory*price//1000 == wealth` **from response fields only** (no engine import in test file beyond fixtures).
  3. Assert `GET /games/{id}` after each turn returns identical `GameView` (read-only).
  4. Static check: frontend placeholder (none yet) would fail if it had to import `actor.cost_for_quantity` or `turn._target_price` — test greps that Section 11's future client imports only `GameView` JSON, never `backend/app/engine/*.py`.

  Failure of any step = AC4 not met. This replaces the vague "frontend will not need to reproduce formulas" with a byte-specific field checklist plus a value-recomputation-from-response-only assertion.

### K5 — AC5 "engine imports no FastAPI" enforced by TEST

- **Decision:** Retain and **extend** `backend/tests/test_engine_purity.py`. Already AST-walks `ENGINE_DIR + DOMAIN_DIR` and forbids `{"fastapi","sqlalchemy","httpx","asyncpg","openai","clerk"}` top-level imports. Extend to also cover `alembic` (in out-of-scope list) and to assert that **no file under `backend/app/engine/` or `backend/app/domain/` imports from `backend/app/api/`** (reverse dependency). Run in CI as unit test — if a future contributor adds `from app.api.schemas import GameView` inside `engine/turn.py`, this test fails. Section 8 had a compat shim that silently reinstated a removed API; this guard would have caught it at AST time.
- **Evidence:** Need to actually run `python -m ast` on current `backend/app/engine/*.py` — done via `grep -rn "from.*fastapi" backend/app/engine` showing 0 hits today. Guard makes that property permanent.
- **Rejected:** A `pyproject.toml` dependency linter or manual code review — not enforceable.

### K6 — Determinism: how `run_seed` is chosen and reproduced

- **Decision:** `POST /api/v1/games` body is `CreateGameRequest{run_seed?: str, ruleset_version?: str}` (both optional). If `run_seed` absent, server generates `uuid4().hex` (via `secrets`/`uuid`, not `random` global) and echoes it in `GameView.game_id` is *separate* from `run_seed` (game_id is session UUID; run_seed is deterministic seed). If `run_seed` present, server uses it verbatim (validated as `str`, length 1..64, no `hash()`). `ruleset_version` defaults to `"1.0"` (matches `default_start_state`). Session is constructed as `FiveTurnGame(seed=run_seed, version=ruleset_version)`. This keeps the existing `resolve_turn(state, command, pressure, rng_context)` determinism intact: same `(run_seed, ruleset_version, choice sequence)` → same history via `rng_for` substreams over `run_seed+r_version+turn+namespace`.
- **Reproduction test:** `test_api_determinism` creates two games with same `run_seed="det-api-001"` and posts the same 5 `choice_id`s, asserts `GET` after each turn yields identical `GameView` JSON (including `home_valley_market.current_price`, `latest_outcome`, `rival_headlines`). A second test without explicit seed asserts each POST returns distinct `run_seed`-derived evolution (not required to match).
- **Rejected:** Using `random.randint` or `hash((seed, turn))` for substreams — violates global §11 (stable hash). Using `time.time()` as seed default without echoing `run_seed` — makes reproduction impossible.

### K7 — Minimal server surface & app wiring

- **Decision:** Create `backend/app/main.py` with `create_app() -> FastAPI` factory (lifespan no DB), mount `backend/app/api/router.py` (`APIRouter(prefix="/api/v1")`) with the three routes. Use Pydantic v2 schemas; wire a module-level `SESSION_STORE` + `SESSION_LOCK` in `backend/app/api/sessions.py`. No `dependencies.py` `Depends` needed for DB; keep pattern ready for Section 16. Add `fastapi` + `uvicorn` to `backend/pyproject.toml` dependencies (only addition to deps).
- **Rejected:** SQLAlchemy session, `get_db_session`, `httpx.AsyncClient` wiring — in-memory only, so adding them early would violate "explicitly out of scope". A class-based `GameService` — contradicts AGENTS.md §6 plain-functions-over-classes at this boundary; use plain module functions `create_game(req) -> GameView`, `get_game(id) -> GameView`, `choose(game_id, choice_id, body) -> GameView`.

---

## Recommended Approach

Build the narrowest FastAPI shim that turns `FiveTurnGame` into an HTTP resource without touching `engine`/`domain` logic.

Flow:

```
POST /api/v1/games {run_seed?, ruleset_version?}
  └─ generate game_id (uuid4 hex) + revision=0
  └─ FiveTurnGame(seed=run_seed or uuid4, version=...)
  └─ build GameView via mapper (signal from pressure_for_turn(len(history)),
      markets from state, route_status, rival_headlines from rival_history[-1],
      available_choices from legality helpers, latest_outcome None)
  └─ store in SESSION_STORE[game_id]

GET /api/v1/games/{game_id}
  └─ read from store (no lock needed for read-only copy, lock for consistency)
  └─ return GameView as above (includes current revision so client need not track)

POST /api/v1/games/{game_id}/choices/{choice_id} {expected_revision: int}
  └─ async with SESSION_LOCK:
       1) stale check: body.expected_revision != session.revision → 409, no mutation
       2) game_complete check: session.game.is_complete → 409
       3) choice_id lookup: session.choice_map[choice_id] → 404 if missing
       4) resolve: pressure = pressure_for_turn(len(history)), command = choice.command,
          ctx = game.state.to_turn_context(), res = resolve_turn(game.state, command, pressure, ctx)
          (engine's rng validation `rng_context == state context` enforced)
       5) commit: game.submit(command) already does steps 1-5 inclusive including rival settlement;
          since FastAPI layer cannot double-call resolve_turn, it delegates single `game.submit()` which internally does rival+world resolution atomically.
          Actually: to avoid double-resolve, the API layer calls ONLY game.submit(command) — not resolve_turn separately.
       6) revision += 1
       7) rebuild and return new GameView (now with latest_outcome populated from res, revision bumped, rival_headlines updated)
```

Crucial: the API must **not** call `resolve_turn` directly in addition to `game.submit` — `game.submit` already does rival choice + `resolve_turn` + rival settlement. Calling both would double-advance turn. The mapper is the only place that reads `game.history[-1]` for `latest_outcome`.

`available_choices` policy (server-chosen quantities):
- `hold` always.
- `expand_farm` if `cash >= 500`.
- `build_granary` if `inventory + farm*YIELD > storage` and `cash >= 300` and `turn < 4`.
- `buy_grain:N` where `N = min(storage - (inventory+harvest), affordable, 80)` capped at 80 if `N>0` and `turn in (1,2)`.
- `sell_grain:N` where `N = min(inventory, 150)` if `turn==4` and `inventory>0`.
- `secure_route` if not established and `cash >= 400` and `turn==0`.
- `ship_grain:N` if established and `inventory>0` and `river - transport - home > 0` where `N = min(inventory, capacity, affordable_by_transport)`.

This matches `engine/harness.py` competent sizing without duplicating engine clamp math — the actual clamp still happens in `actor.resolve_*`.

---

## Work Plan

**Slice 1 — Dependency + app skeleton (no logic yet, keeps AC6 green)**

1. Add `fastapi>=0.110`, `uvicorn>=0.30` to `backend/pyproject.toml` `[project].dependencies`; `httpx>=0.27` already transitive but ensure for `TestClient`. `uv sync --project backend` stays passing.
2. Create `backend/app/api/__init__.py`, `backend/app/api/sessions.py` (store + lock + `GameSession` dataclass), `backend/app/api/schemas.py` (`CreateGameRequest`, `CreateChoiceRequest{expected_revision}`, `ChoiceView`, `GameView` with all fields above), `backend/app/api/mappers.py` (`to_game_view(session) -> GameView`, `choices_for(session) -> list[ChoiceView]` + `choice_map`). Pure mapping, no engine mutation.
3. Create `backend/app/main.py` with `create_app()` + `app = create_app()` for uvicorn/ASGI.
4. Create `backend/app/api/router.py` with three handlers (thin, delegate to `backend/app/api/service.py` plain `async def` functions) — wire to `main.py`.

**Slice 2 — Logic + error semantics**

5. Implement `backend/app/api/service.py` with `create_game()`, `get_game()`, `choose()` including stale/invalid/complete checks under lock, delegating to `FiveTurnGame`. Ensure `choice_id` lookup is exact match against current `available_choices[*].id`.
6. Ensure `GET` returns `404` for missing `game_id` with `{"detail":"game not found"}`; `POST choice` with bad `choice_id` → `404`; stale revision → `409`; complete game → `409`.

**Slice 3 — Purity + tests + gates**

7. Extend `backend/tests/test_engine_purity.py` to forbid `alembic` and `from app.api` imports in engine/domain.
8. Add `backend/tests/test_api_sessions.py` (or `backend/tests/test_api.py`) covering:
   - `test_create_and_complete_five_turn_game` (AC1)
   - `test_invalid_choice_cannot_mutate` (AC2) — POST bad id, then GET, assert turn+revision unchanged
   - `test_stale_revision_cannot_mutate` (AC3) — two POSTs with same revision, second 409, GET unchanged
   - `test_frontend_needs_no_formula` (AC4 operational)
   - `test_engine_still_pure` (AC5, re-uses purity test)
   - `test_determinism_same_seed_same_choices` (K6)
   - `test_game_complete_then_reject` (edge)
   - `test_concurrent_same_revision_one_wins` (atomicity, lock)
   Keep all existing 133 tests passing.

Ordering invariant: Slice 1 then 2 then 3; each slice keeps `make test/lint/type` passing incrementally.

---

## Validation Plan

| Check | Command | Expected evidence |
|-------|---------|-------------------|
| Unit | `make test` (= `uv run --project backend pytest -v`) | 133 existing + ~8 new API tests pass; no existing failure. |
| API 5-turn | `test_create_and_complete_five_turn_game` | `GET` after 5th choice: `turn==5`, `revision==5`, `is_complete`/`completion_summary` present, no 6th choice allowed. |
| Invalid choice | `test_invalid_choice_cannot_mutate` | `POST …/choices/bad-id {"expected_revision":0}` → `404`; subsequent `GET` has same `revision`/`turn`. |
| Stale revision | `test_stale_revision_cannot_mutate` | Client reads `revision=1`, two concurrent POSTs with `expected=1` → one `200` (revision 2), one `409` with `current_revision:2`; `GET` confirms. |
| No formula | `test_frontend_needs_no_formula` | Asserts field set from K4 + `wealth == cash + grain*price//1000` using response values only. |
| Determinism | `test_determinism_same_seed_same_choices` | Two independent sessions with same seed+same 5 choice_ids produce identical `GET` JSON (prices, headlines, drivers). |
| Purity guard | `make test -k test_engine_source_contains_no_forbidden_imports` | Fails if any engine/domain file imports `fastapi`/`sqlalchemy`/`alembic`/`httpx`/`app.api`. |
| Lint/type/format | `make lint` → `make type` → `make format-check` | `All checks passed`, `0 errors`, `N files already formatted`. |
| Out-of-scope absence | `grep -R "sqlalchemy\|Alembic\|asyncpg\|Clerk\|openai" backend/app/api --include="*.py"` | 0 hits (no premature persistence/auth/LLM wiring). |

Manual/smoke not needed (headless API only until Section 11).

---

## Risks / Rollback

- **Risk: `choice_id` with quantity invents arbitrary `quantity=9999`.** Mitigated by server-chosen quantities in `available_choices`; route rejects IDs not in map before engine call. Cost is small bucket set, not arbitrary.
- **Risk: double `resolve_turn` (API calls it and `game.submit` also does).** Mitigated by delegating solely to `game.submit` — document as hard rule in service code comment. A test asserts `turn` increments by exactly 1 per POST.
- **Risk: revision vs `GameState.turn` confusion.** Keep them distinct: `turn` is economic turn (0..5, from GameState), `revision` is optimistic concurrency (0..5 in this section, but diverges if future non-turn mutations exist). Tests assert both.
- **Risk: in-memory store lost on reload.** In-scope per DECISIONS 006; no rollback needed — persistence is Section 16.
- **Rollback:** Delete `backend/app/api/`, `backend/app/main.py`, and `fastapi`/`uvicorn` from deps — engine/domain unchanged so `make test` reverts to Section 9 green.

---

## Self-Grill (decision-forcing questions; answered from code/evidence)

### Q1 — Does `GameView` actually include `causal_trace`/`player_outcome.drivers`, or is that just in the engine?

**Evidence:** `engine/prototype.py:372` returns `TurnResolution` with `causal_trace: CausalTrace{nodes: tuple[CausalNode...>}` and `player_outcome: PlayerOutcome{drivers: tuple[OutcomeDriver≤3>}`; `domain/trace.py:39` defines `CausalNode{parent_ids}` and `PlayerOutcome`. The current `Makefile` game stores no view — so the plan's K4 field list is **not yet verified to be exposed**. The operational test must assert the HTTP JSON contains `latest_outcome.drivers[*].label` and that at least 3 turns include `pressure_stage` as a root node (checked via `debug_trace`).

**Answer:** Include `latest_outcome.drivers` (labels + impact_bps + reason_code) plus `domain_effects` by default, and `debug_trace: CausalTrace` on demand. Without drivers, the frontend cannot satisfy global §14 "trace is first-class output" and AC4 is unfalsifiable — the plan already corrects the vague spec by specifying the exact JSON paths.

### Q2 — Is `test_engine_purity.py` actually checking `fastapi`, and could the new API slip an import into `engine`?

**Evidence:** Ran `grep -rn "from.*fastapi\|import fastapi" backend/app/engine/ backend/app/domain/` → 0 hits today; `backend/tests/test_engine_purity.py:8` sets `FORBIDDEN_TOP_LEVEL = {"fastapi", ...}` and AST-walks `ENGINE_DIR + DOMAIN_DIR` (computed locally). So a `fastapi` import in `engine/actor.py` would already fail — but `alembic` and an import from `app.api` are **not** in the set, so the Section 8 shim-style regression (reimporting removed API) could recur via `from app.api.schemas import ChoiceView` inside `engine`.

**Answer:** Extend the forbidden set to include `alembic` and add a reverse check: no file under `engine/`/`domain/` may contain `from app.api` or `import app.api`. The grill converts "good intentions" into a test.

### Q3 — Could two concurrent `POST choices` with the same correct `expected_revision` both mutate?

**Evidence:** Today `FiveTurnGame.submit` is synchronous and takes no lock; `backend/app/api/sessions.py` does not exist yet, so there is no `SESSION_LOCK`. A naive implementation `if rev != expected: raise 409; game.submit(cmd); session.revision += 1` without `async with lock:` is racy under `asyncio` (`uvicorn` runs multiple concurrent coroutines). The spec's "atomic with respect to mutation" requires explicit locking.

**Answer:** Wrap the read-check-mutate in `async with SESSION_LOCK` (single global `asyncio.Lock`). A new test `test_concurrent_same_revision_one_wins` that `asyncio.gather`s two POSTs with same revision asserts exactly one `200`, one `409` — this test would fail without the lock, proving necessity.

### Q4 — If the API returns a capped `actual=2` for `buy_grain:80`, does the frontend see the cap or just "bought 80"?

**Evidence:** `engine/actor.py:resolve_buy` returns `actual` clamped to `min(requested, affordable, space)` and reason `insufficient_*`; `engine/turn.py` emits `purchase_quantity_value` with `actual`. So the engine already truncates safely. The API's job is only to surface `actual` in the outcome, not to pre-validate affordability.

**Answer:** The plan deliberately **does not** make short-cash/short-storage a 4xx. POST `buy_grain:80` with only cash for 20 is `200 OK` with `latest_outcome` showing `actual=20, reason=insufficient_cash` in trace — this preserves "engine decides cost/validity" (global §10). Marking it `422` would duplicate `actor.resolve_buy` logic and is out-of-scope. Only unknown `choice_id` is 404.

### Q5 — Does `available_choices` shrink after some choices (e.g., `secure_route` twice)?

**Evidence:** `engine/prototype.py` has no "choice exhaustion" — `secure_route` after `established==True` proceeds via `resolve_secure_route` and would be reason `already_established` (or similar) if repeated. Offering `secure_route` twice would allow the invalid-command test to confuse "engine-capped" with "API-rejected".

**Answer:** The mapper must regenerate `available_choices` from current `GameState.route.established`, `player.cash`, and `turn_idx = len(history)` each GET/POST response, omitting choices whose preconditions are false (no `secure_route` once established, no `ship_grain` when margin ≤0 or inventory 0). A test asserts `secure_route` is present at `turn 0` but absent after being taken, proving the map is not static.

### Q6 — Is `run_seed` optional or required, and can a player replay with an observed seed?

**Evidence:** `domain/types.py:GameState{run_seed: str, ruleset_version: str}` stores whatever string is given; `engine/rng.py:rng_for` hashes `run_seed + ruleset_version + …` via `hashlib.blake2b`. `backend/tests/test_determinism.py` shows tests pass `seed="det-seed"` explicitly and compare identical histories. No current API generates a seed — so reproduction today requires passing a seed.

**Answer:** Make `run_seed` optional on `POST /games`; if absent, server generates `uuid4().hex` and echoes it in `GameView.game_id`'s companion `run_seed` field. Tests that pass `"formula-test"` or `"det-api-001"` reproduce exactly by posting the same `choice_id`s in order. This satisfies "integers only, no global random" — generation uses `uuid`/`secrets`, not `random`, and the deterministic path uses `rng_for`.

### Q7 — Does any plan step build React or touch the DB?

**Evidence:** `DECISIONS.md 006` says in-memory until Section 16; `BUILD_SPEC.md §10` explicitly says OUT: `PostgreSQL, SQLAlchemy, Alembic, authentication, history endpoint, cloud deployment`. `backend/pyproject.toml` today has no `sqlalchemy`/`alembic`.

**Answer:** No `frontend/` changes, no `SQLAlchemy`, no `alembic` migration, no `render.yaml`. The only new dependency is `fastapi` + `uvicorn` (and transitive `anyio/starlette/httpx` for `TestClient`). The validation table's "out-of-scope absence" grep ensures this — if a follow-on adds `get_db_session`, that grep fails and the plan has been violated.

### Q8 — Where should `GameView` and mapping live so the engine never knows about HTTP status codes?

**Evidence:** `AGENTS.md §6` mandates `Router -> Service -> Database Client -> Database` with `Depends` only at the edge, services as plain functions, and `app/models` vs `app/schemas` separation. `engine/prototype.py` is pure; `domain/trace.py` uses `tuple`, not `list`. Adding `from fastapi import HTTPException` into `engine` would be a layer violation.

**Answer:** Keep `domain/types.py` + `trace.py` + `pressure.py` + `engine/*.py` unchanged except possibly a helper `all_commands_for_view` if reused. New files are strictly `backend/app/api/schemas.py`, `backend/app/api/mappers.py`, `backend/app/api/service.py`, `backend/app/api/router.py`, `backend/app/api/sessions.py`, `backend/app/main.py`. None of the `engine/` or `domain/` files gains a top-level import ending in `fastapi` or `app.api`.

### Q9 — What HTTP code for stale revision, and what if the user doesn't send `expected_revision`?

**Evidence:** Spec says "Mutating requests include an expected state revision; a stale revision must fail." No code is prescribed. Conventional mapping is `409 Conflict` for optimistic concurrency; `422 Unprocessable Entity` is for validation errors (Pydantic). Missing `expected_revision` should be `422` (body validation), stale mismatch `409`.

**Answer:** `CreateChoiceRequest{expected_revision: Annotated[int, Field(ge=0)]}` — absent field → FastAPI's Pydantic validation returns `422`. Present but wrong value → handler returns `409 {"detail": "conflict …", "expected_revision": x, "current_revision": y}`. This separates "you forgot revision" from "you have a stale view" and matches DECISIONS.md 005's revision concurrency phrasing.

### Q10 — Could `choice_id` be enumerated as an integer index (0,1,2) instead of `type:qty` strings?

**Evidence:** Index-based IDs would be fragile across revisions — inserting a new choice shifts `hold` from `0` to `1` and a stale client would mutate incorrectly. String IDs like `expand_farm` and `buy_grain:20` are stable ELIs and self-describing in logs, matching prior sections where commands were described by type strings (`engine/actor.py` constants). `FiveTurnGame.available_commands()` already uses strings.

**Answer:** Reject integer indexing; use the stable `f"{type}" / f"{type}:{quantity}"` form defined in K2. The 404-on-unknown-id test would otherwise be ordering-sensitive. Keep `choice_id` opaque from the frontend's perspective — it copies the `available_choices[*].id` verbatim, never synthesizes.

---

## What The Grill Changed (vs draft)

1. **Revision atomicity made explicit.** Draft had "compare revision then mutate" with no lock. Grill Q3 forced `async with SESSION_LOCK` and a concurrent conflict test — without it two concurrent correct-revision POSTs could both commit.
2. **AC4 operationalized into a falsifiable test.** Draft listed fields vaguely. Grill Q1 forced a step-by-step "no-formula" integration test that asserts response-only recomputation plus exact field checklist; a vague criterion would have been unfalsifiable.
3. **AC5 guard extended beyond `fastapi`.** Draft cited existing `test_engine_purity.py` as sufficient. Grill Q2 surfaced the `alembic` and `from app.api` reverse import as an unguarded leak (the Section 8 shim regression pattern) — guard now forbids both.
4. **Choice vs engine bound split clarified.** Draft risked duplicating affordability checks. Grill Q4 drew a hard line: unknown `choice_id` is 404 (API concern), short-cash/short-storage is a clamped 200 with reason `insufficient_*` in trace (engine concern). No double implementation.
5. **Available-choices dynamism required.** Draft treated choices as static. Grill Q5 forced per-turn regeneration (omit `secure_route` once established, etc.) and a regression test that quantity verbs' caps update.
6. **Scope tightened, no DB/React added.** Grill Q7 prevented scope creep (SQLAlchemy/Alembic/Render/LLM/history) that future sections own; validated via "out-of-scope absence" grep.
7. **Rejected integer `choice_id` alternative.** Grill Q10 explicitly rejected integer indexing in favor of stable `type:qty` strings.

## Revisions To Be Made Before Implementation (downward only)

- Do **not** add `backend/app/dependencies.py` DB wiring or `httpx.AsyncClient` lifecycle — keep `main.py` lifespan minimal for in-memory store (no `httpx` pool until Section 17).
- Do **not** offer 3–4 quantity buckets per verb; one server-chosen quantity per kind is the smallest coherent set (4–7 choices total).
- Do **not** return full `causal_trace` by default on every `GameView` if it bloats the payload; return `latest_outcome{drivers, domain_effects}` plus optional `?trace=1` or `debug_trace` field populated from `game.history[-1].causal_trace` only for the latest turn — keeps AC4 satisfied without shipping 5 traces.

## Open Questions

- **None that blocks planning.** Product-owner escalation: whether to return `completion_summary: StrategicSummary` at turn 5 vs a flatter `final_wealth/wealth_delta_total` — spec suggests `completion_summary`. Plan includes it; if owner prefers flatter payload, mapper field is trivial to rename without engine change.

**Escalation:** One item marked `ESCALATE` in the original task — "what exactly must GameView carry" — is answered deterministically in K4 with a field checklist and an operational test; the remaining ambiguity (exact bucket sizes for `buy_grain`) is view policy and can be tuned in Section 11 without touching engine.

