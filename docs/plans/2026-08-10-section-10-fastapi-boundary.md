# Section 10 — Minimal FastAPI Boundary — Plan

**Date:** 2026-08-10 — Revised 2026-08-10 per consolidated review rounds 1+2 (B1–B7 BLOCKING, C1–C7 BLOCKING C3/C4)
**Branch:** `section/10-fastapi-boundary` (from `origin/main` at `0d28df6` Section 9 COMPLETE)
**Spec Authority:** `BUILD_SPEC.md` Section 10 (Status: NOT STARTED) + global §§10–16 + `DECISIONS.md` 015/016 + `STATE.md` §9 + `AGENTS.md` §§6/10
**Related:** `backend/app/domain/types.py:40` (`OperationState` dormant), `backend/app/domain/trace.py`, `backend/app/domain/pressure.py`, `backend/app/engine/prototype.py` (`TURN_LIMIT:49`, `turn_limit:211`, `StrategicSummary:137`), `backend/app/engine/turn.py` (`arbitrage_margin:215,1297`), `backend/app/engine/actor.py`, `backend/app/engine/rivals.py`, `backend/tests/test_engine_purity.py:8`

**Review disposition:** Round 1 B1–B7 verified fixed. Round 2 adds C1 (B4 reason correction — `OperationState` exists but dormant), C2 (B2 reason trim), plus two new blockers **C3** (completion_summary smuggles history) and **C4** (current-turn vs latest-outcome context conflation), and C5–C7 (per-session lock, missing deps, cleanup). This revision addresses all of B1–B7 and C1–C7; C3/C4 change `GameView`/`OutcomeView` shape and are blocking. Approved to implement once reflected — see Work items below.

---

## Goal

Expose the existing deterministic 5-turn game through exactly three in-memory endpoints while keeping `backend/app/engine` + `backend/app/domain` pure, satisfying AC1–AC6 so a client can play the full prototype without reproducing economic formulas.

---

## Success Criteria (maps to Section 10 AC + global rules)

1. **Five-turn creation & completion (AC1).** `POST /api/v1/games` creates a game; five successive `POST …/choices/{choice_id}` with correct `expected_revision` advance `turn 0→TURN_LIMIT` and then present a `completion_summary`. Any API test doing `1× create + 5× choices` reaches `turn == turn_limit == TURN_LIMIT`. GET between turns reflects mutated state.
2. **Invalid commands cannot mutate (AC2).** An unknown or not-currently-offered `choice_id` returns 404 without calling `resolve_turn` and without incrementing `revision` or `turn`. Verified by `GET` before/after showing identical state. `GET` on unknown `game_id` → 404.
3. **Stale revisions cannot mutate (AC3).** Every mutating POST carries `expected_revision: int`; server compares atomically to current `revision`. Mismatch → `409 Conflict` with no mutation (GET after still same). Missing field → `422`.
4. **No client formula needed (AC4).** `GameView` carries every number the frontend would otherwise compute — see Key Decision K4 for the completeness checklist. One API test can render "why" entirely from response fields (no recomputation), plus a separate internal-consistency check.
5. **Engine stays pure (AC5).** `backend/app/engine/*.py` + `backend/app/domain/*.py` import no `fastapi`/`sqlalchemy`/`alembic`/`httpx`/`asyncpg`/`openai`/`clerk`, and no file under those dirs imports from `app.api`. Enforced by a failing test, not convention.
6. **No regressions (AC6).** Existing 133 backend tests remain green; `ruff check`, `ruff format --check`, `pyright --strict` stay 0 errors.

---

## Context And Current Facts

- `STATE.md` §9: `GameState{turn, run_seed, ruleset_version, player{cash, inventory{grain}, farm_capacity, storage_capacity}, market{Home + regional_output}, river_market, route{transport 300, capacity 20, reliability 10000, established}}`, `PlayerCommand{7 types: expand_farm, build_granary, buy_grain, sell_grain, hold, secure_route, ship_grain}` with optional `quantity`. `FiveTurnGame` owns `GameState` + `history: tuple[TurnResolution,TURN_LIMIT]` + `rivals` (integer bps scoring), `PRESSURE_ARC: tuple[PressureState,5]`, `resolve_turn(state, command, pressure, rng_context) -> TurnResolution{next_state, domain_effects, causal_trace{nodes, edges}, player_outcome{wealth_delta, drivers ≤3}}`. Price-taking boundary explicit. Determinism via `rng_for` (BLAKE2). Tuned start state `storage 130`, `transport 300`.
- Current backend has **no** `app/main.py`, no `app/api/`, no `fastapi` in `pyproject.toml` (only `pydantic>=2.7`). `DECISIONS.md 006`: in-memory until Section 16 — matches Section 10.
- `backend/tests/test_engine_purity.py:8` forbids `{"fastapi","sqlalchemy","httpx","asyncpg","openai","clerk"}` via AST walk — does **not** cover `alembic` or reverse `from app.api` imports (confirmed by grep 0 hits today, but guard is incomplete — K5 extends it).
- `Makefile` gates: `make test` = `uv run --project backend pytest -v`, `make lint`, `make type`, `make format-check`.
- `FiveTurnGame.available_commands() -> list[str]` at `prototype.py:307` returns all seven verbs **unconditionally** with no turn gating. `resolve_turn` accepts any verb on any turn; affordability is clamped in `actor.resolve_*` with `insufficient_*` reason, never refused by turn index. Harness `policy_storage_heavy` / `policy_trade_heavy` in `engine/harness.py` gate on `turn in (1,2)` / `turn==4` / `turn==0` — those are **measuring instruments**, not engine rules. Original plan incorrectly lifted them into `available_choices`.
- `prototype.py:49` defines `TURN_LIMIT: int = 5`; `prototype.py:211` exposes it as `turn_limit`. Hard-coding `5` in the view would duplicate that constant (AC4 forbids).
- `turn.py:215/1297` computes `arbitrage_margin` as `ship_revenue - ship_cost - (ship_effective * new_price // 1000)` — a third copy of `river - transport - home` alongside the harness policy inline and the planned mapper.

---

## Constraints And Non-goals

**Must satisfy:**
- In-memory sessions only; no `DATABASE_URL`, no `SQLAlchemy`, no `AsyncSession`, no `Alembic`.
- Exactly three endpoints: `POST /api/v1/games`, `GET /api/v1/games/{game_id}`, `POST /api/v1/games/{game_id}/choices/{choice_id}`. No history endpoint, no `?trace=1`, no `If-Match`/ETag header — revision is in body.
- `expected_revision` optimistic concurrency on every mutating POST; stale → `409`, missing → `422`, game-complete on POST → `409` (not 400, consistently).
- `GameView` presentation-oriented; frontend recomputes nothing economic.
- `engine` + `domain` import-free of web/DB; `revision` lives on envelope, not `GameState`.
- Integer numerics only; no new verb/state field/content DSL.

**Explicitly out of scope:**
- PostgreSQL/SQLAlchemy/Alembic/`render.yaml`/authentication/LLM/history/cloud deploy. Section 11 React is later — no frontend scaffolding.

---

## Key Decisions

### K1 — Where `GameView` lives (pure engine boundary, global §13)

- **Decision:** `GameView` + `ChoiceView` + `OutcomeView` live **outside** engine/domain, in `backend/app/api/schemas.py` (alt: `backend/app/schemas/game_view.py` — either outside `domain`/`engine`). `backend/app/api/` may import `GameState`/`TurnResolution`/`PressureState` to map, but `domain`/`engine` never import `app/api/*` or `fastapi`.
- **Evidence:** Engine today imports only `pydantic` + domain types + `rng/rounding/pressure`. `test_engine_purity.py:8` would trip on `fastapi`. Mapping in `backend/app/api/mappers.py` (`game_to_view(session) -> GameView`) is tested without HTTP.
- **Rejected:** Putting `GameView` in `domain/types.py` or `engine/prototype.py`.
- **Consequence:** Purity guard stays simple.

### K2 — `choice_id`: what it IS and how it prevents mutation (AC2) — **REVISED per B1/B6**

- **Decision:** A `choice_id` is a **stable, server-derived identifier for one concrete `PlayerCommand` legal at the current view**. Canonical form:
  - parameterless: `expand_farm`, `build_granary`, `hold`, `secure_route`
  - quantity verbs: `buy_grain:40`, `sell_grain:30`, `ship_grain:10` — `f"{type}:{quantity}"`
  `GameView.available_choices: list[ChoiceView{id, label, kind, quantity?}]` enumerates the exact set accepted by `POST …/choices/{choice_id}` **at this revision**. Server does `choice = session.choice_map[choice_id]`; missing → `404`, no engine call. Client copies `id` verbatim, never synthesizes.

- **What the API rejects vs what the engine bounds:**
  - **API rejects (no mutation, 404):** unknown `choice_id`, choice from prior revision (stale `choice_map`), `choice_id` not in current `available_choices`.
  - **Engine bounds (200 with trace, not 4xx):** `buy_grain` beyond cash/storage → `resolve_buy` clamps `actual = min(requested, affordable, space)` with `insufficient_cash`/`insufficient_storage`; `ship_grain` beyond capacity/inventory/affordable → `resolve_shipment`; `sell_grain` beyond inventory → `resolve_sell`. These surface as `reason_code` in `causal_trace`/`domain_effects`, not HTTP errors. API must **not** re-validate affordability.

- **`available_choices` policy — legality + affordability ONLY (B1 fix):** Every condition that mentions a turn index or `margin > 0` from the original plan is **deleted**. New rules (mirrored exactly in `backend/app/api/mappers.py:choices_for`):

```python
# Pure legality/affordability — derived from engine preconditions only
hold            # always (1)
expand_farm     # if cash >= EXPAND_FARM_COST (actor.EXPAND_FARM_COST = 500)
build_granary   # if cash >= BUILD_GRANARY_COST (=300), ANY turn (not turn<4)
secure_route    # if not route.established and cash >= ROUTE_ESTABLISH_COST (=400)
buy_grain:N     # ANY turn, if N>0  — see quantity rule below (not turn in (1,2))
sell_grain:N    # ANY turn, if inventory.grain > 0 (not turn==4)
ship_grain:N    # if route.established and inventory.grain > 0 — DO NOT gate on margin>0
```

`ship_grain` at a loss is legal and pedagogically required — drought peak makes it loss-making by design; hiding it removes the lesson. Surface `route_status.next_margin` (via engine helper, B6) so the player sees it is negative and decides.

- **Falsifiable guard (B1):** New regression test `test_available_choices_turn_invariant` — at a **fixed** cash/inventory/route state, calling the mapper at `turn_idx` 0..4 produces **identical** `available_choices` sets except where an engine-level precondition genuinely changed (`route.established` flips, `cash` crosses `EXPAND_FARM_COST`, `inventory` goes to 0). Would fail the original plan because `buy_grain` vanished outside (1,2).

- **Quantity — deliberate design call (DECISIONS entry, B1):** Offer **TWO** options per quantity verb — a partial and a full commit — not the single amount originally planned. E.g. `buy_grain:40` + `buy_grain:80` where `80 = min(headroom, affordable, 80)`, `40 = max(80//2, 1)` when affordable permits; similarly `sell_grain: N//2` + `sell_grain:N` (N = min(inventory, 150) or inventory), `ship_grain: cap//2` + `ship_grain:cap`. A continuous slider would violate BUILD_SPEC 4 (avoid tuning exact quantities), but one server-picked amount removes the depth-of-commitment decision — Section 9 proved scaled buys were the whole gap between strawman and competent policies. Two keeps the list at **~6–8 items** and preserves "how much do I commit" while staying far from spreadsheet-tuning. Concrete mapping is view policy (not engine rule); exact numbers are mapper constants, not content DSL.

- **Rejected:** Free-form body `{type, quantity}` (lets client invent `9999`, duplicates engine clamp); pure type without quantity (underspecified); integer index `0,1,2` (ordering-fragile, fails stale-choice test); turn-gated / margin-gated lists (now deleted).

- **B6 co-fix:** `next_margin = river_price - transport - home_price` exists in three places. Extract one pure helper in the engine — e.g. `actor.ship_margin(river_price: PriceMilliunits, transport_cost_per_unit: PriceMilliunits, home_price: PriceMilliunits) -> int` — and have `engine/harness.py:policy_trade_heavy`, `engine/turn.py:1297` (replacing inline `ship_revenue - ship_cost - …` or post-hoc), and `api/mappers.py:route_status.next_margin` all call it. Economic formulas belong in the engine (global §10). Mapper stays a mapper.

### K3 — Revision semantics (where, increment, failure, atomicity) — **REVISED per B7/C5**

- **Where:** `revision: int` lives on the **session envelope**, not `GameState`. `GameState.turn` is economic turn (0→TURN_LIMIT); `revision` is optimistic concurrency. Envelope is `GameSession{game_id: str, revision: int, game: FiveTurnGame, created_at, lock: asyncio.Lock}` stored in `backend/app/api/sessions.py: SESSION_STORE: dict[str, GameSession]`. `lock` is **per-session** (C5) — see Atomicity. **No `revision_history`** — cut per B7/C7; no history in this section. `created_at` harmless.

- **Increment:** Exactly `+1` on each **successful** `POST …/choices/{choice_id}`. `GET` never increments. `POST /games` creates `revision=0`. Failed validations (stale, invalid choice_id, game complete) leave `revision` unchanged. `turn_limit` is **derived** from `prototype.TURN_LIMIT` (imported, not hard-coded `5`).

- **Failure responses (decided per B7):**
  - Missing `expected_revision` in body → `422 Unprocessable Entity` (Pydantic validation).
  - `expected_revision != session.revision` → `409 Conflict` body `{"detail":"conflict: expected_revision X != current Y","expected_revision":X,"current_revision":Y}` — no mutation.
  - `POST` on complete game (`session.game.is_complete`) → `409 Conflict` `{"detail":"game complete"}` — **consistently 409**, documented. Not 400.
  - Unknown `game_id` on `GET` or `POST` → `404 Not Found` `{"detail":"game not found"}`. Unknown `choice_id` → `404`.

- **Atomicity & lock choice (B7/C5 fix):**
  - Handlers are `async def`.
  - Each `GameSession` owns its own `asyncio.Lock` (`session.lock`). Both `get_game()` and `choose()` acquire `async with session.lock:` — C5: GET must also take the same per-session lock because the mapper walks `state`, `history`, and `rivals` while building the view; a concurrent `choose()` mutating midway would produce a **torn view** mixing pre- and post-turn values. Per-session locks let unrelated games proceed independently, removing the global-serialization concern. Honest reasoning: with `async def` handlers and **no `await` between the revision check and the mutate**, the operation is already atomic on a single-threaded event loop — the lock is **defensive belt-and-braces** against a future `await` sneaking between check and mutate. State it rather than implying the race exists today.
  - The `asyncio.gather` concurrency test (`test_concurrent_same_revision_one_wins`) must use a real async client (`httpx.AsyncClient` + `ASGITransport`) and `pytest-asyncio` (C6), not `TestClient` gymnastics, because only `async def` + `asyncio.Lock` is exercised that way. `threading.Lock` under `async def` would not correctly block the event loop.

- **Rejected:** Single global `SESSION_LOCK` (replaced by per-session per C5), `If-Match`/ETag header (spec says body field), `412 Precondition Failed`, `threading.Lock` + async mix, `GET` without lock.

### K4 — AC4 "no frontend formula needed" — **REVISED per B2/B3/B4/B5/C1/C3/C4**

- **Risk:** Prior sections were bitten by unfalsifiable ACs; original plan had two such lapses (B3).

- **Correction C1 to B4 reason:** Round 1 claimed `OperationState` was invented (grep returned 0). That grep was wrong — `OperationState` **does exist** at `domain/types.py:40` (`id/kind/capacity/level`). The conclusion (`empire_summary` must not synthesize operations) is still correct, for a better reason: `types.py:59` says `OperationState` "exists as a standalone type for future Section 5 use" — a **dormant type deliberately not embedded in `PlayerState`** to avoid duplicate sources of truth for capacity. Synthesizing `farm_1`/`granary_1` with invented `level` values would turn a dormant type into fictional canonical-looking state and create a second source of truth for `farm_capacity`/`storage_capacity`. Keep as three concrete fields; fix the stated reason (C1). Also drop one B2 argument per C2: `?trace=1` on `GET /games/{id}` would not violate the three-endpoint spec (still same endpoint), but the conclusion rests on the other three reasons (unmeasured optimization, two shapes of GameView, drivers referencing `causal_node_ids` while omitting those nodes — unresolvable reveal). `empire_summary` reason below is updated accordingly.

- **Decision — what `GameView` must carry (concrete, exhaustive):**

```python
class GameView(BaseModel):
    game_id: str
    run_seed: str                          # B5: echoed so omitted-seed games are reproducible; distinct from game_id
    revision: int
    turn: int
    turn_limit: int                        # B7: derived from prototype.TURN_LIMIT, not literal 5
    signal: str                            # B4/C4: "the decision you are about to make" — from pressure_for_turn(len(history)) or "" when complete
    pressure_stage: str                    # B4/C4: next-turn context; OutcomeView carries resolved context separately
    world: WorldCondition                  # B4/C4: next-turn world
    player_summary: {cash, inventory_grain, farm_capacity, storage_capacity, wealth}
    empire_summary: {farm_capacity, storage_capacity, route_established}  # C1: dormant OperationState not embedded; exactly the three concrete fields to avoid second source of truth
    home_valley_market: {supply, demand, base_price, current_price, responsiveness}
    river_town_market: {supply, demand, base_price, current_price}
    route_status: {established, capacity, transport_cost_per_unit, reliability_bps, next_margin}
                                           # B1/B6: next_margin via actor.ship_margin(), shown even when negative
    rival_headlines: {mira: str, daran: str} | None
    available_choices: list[ChoiceView{id, label, kind, quantity?, cost?}]
                                           # B1: two quantities per verb (partial+full), legality/affordability only
                                           # B3: each choice's label AND its cash cost via actor.cost_for_quantity()
    latest_outcome: OutcomeView | None     # None before first turn; C4: carries its OWN resolved context below
    completion_summary: CompletionSummaryView | None  # C3: API-owned, end-screen values only — NOT StrategicSummary

class OutcomeView(BaseModel):              # C4 — resolves current-turn vs latest-outcome conflation
    # Context of the turn just resolved — distinct from top-level "next decision" context
    resolved_turn: int                     # turn index just submitted (0..TURN_LIMIT-1)
    title: str                             # TURN_LIMIT title for that turn (e.g. "Drought")
    pressure_stage: str                    # stage of resolved turn (e.g. "drought") — check vs top-level aftermath
    world: WorldCondition                  # world of resolved turn — "drought" when drought just resolved
    command_type: str                      # submitted PlayerCommand.type (e.g. "hold")
    command_quantity: int | None           # submitted quantity if any
    # Economic result
    wealth_delta: int
    inventory_delta: int
    price_delta: int
    drivers: tuple[OutcomeDriver{label, impact_money, impact_bps, reason_code, causal_node_ids}, 0..3]
    domain_effects: list[DomainEffect{metric, before, after, delta, reason_code}]
    causal_trace: CausalTrace{nodes: tuple[CausalNode{id, label, kind, before, after, delta, reason_code, parent_ids}>}
                                           # B2: UNCONDITIONAL, latest turn only — not debug_trace, not ?trace=1 (C2 trims one reason, keeps three)

class CompletionSummaryView(BaseModel):    # C3 — API-owned, no history smuggling
    initial_wealth: int
    final_wealth: int
    wealth_delta_total: int
    final_cash: int
    final_grain: int
    final_farm_capacity: int
    final_storage_capacity: int
    cash_low: int
    peak_inventory: int
    is_complete: bool
    final_rival_headlines: {mira: str, daran: str} | None  # pre-rendered strings only, no raw RivalState/RivalTurnResult
    # NO initial_state, NO final_state, NO history: tuple[TurnResolution,...], NO raw rival states
```

Key properties:
  - `wealth`/`price`/`inventory` are engine-computed (`turn.py` wealth decomposition) — frontend never does `value = qty*price//1000`.
  - Each `available_choices[*].cost` is precomputed by the mapper via `actor.cost_for_quantity(quantity, current_price)` — frontend does not multiply.
  - `route_status.next_margin` is engine helper `actor.ship_margin(river_price, transport, home_price)` — frontend does not recompute margin.
  - `rival_headlines` are pre-rendered `RivalTurnResult.headline` strings.
  - Full `causal_trace.nodes` (expected ~40–60 nodes per turn — B2 says measure before optimizing) is inside `latest_outcome` (OutcomeView), not a separate `debug_trace` and not behind a query param. C2: `?trace=1` would still be the same endpoint, so not a spec violation — the conclusion rests on the other three reasons (unmeasured optimization, two shapes of `GameView`, `drivers[*].causal_node_ids` referencing omitted nodes — unresolvable reveal); global §14 makes the trace first-class and §9 makes the reveal signature. Latest turn only — C3 ensures `completion_summary` does not smuggle the other four traces.
  - `OutcomeView` (C4) disambiguates: top-level `world/pressure_stage/signal` = "the decision you are about to make"; `OutcomeView.world/pressure_stage/title/resolved_turn/command_*` = "the decision you just made". After drought, top-level `world` is `aftermath` while `latest_outcome.world` is `drought` — a client rendering the reveal alongside next-turn context never confuses them. `CompletionSummaryView` (C3) is API-owned — no `initial_state`/`final_state`/`history`/`RivalState`.

- **Operational test — rewritten per B3/C3/C4:**

  `test_frontend_needs_no_formula` is a **completeness** check, not a recomputation:

  For a game with `run_seed="formula-test"` (or any seed) and for each of 5 turns, assert the `GET` / mutated `GameView` JSON **contains as fields** every number Section 11's decision screen must display — without arithmetic:
  - current `wealth`, `player_summary{cash, inventory_grain, farm_capacity, storage_capacity}`, both markets' `current_price`, `route_status{established, capacity, transport_cost_per_unit, next_margin}`, `available_choices[*].{id, label, cost}`, `latest_outcome` after turn 1 with `wealth_delta` and `OutcomeView{resolved_turn, title, pressure_stage, world, command_type, command_quantity}` plus `drivers[*].{label, impact_money, impact_bps, reason_code}` plus `causal_trace.nodes[*].{reason_code, parent_ids}`.
  - If any value can only be obtained by multiplying/dividing two response fields (e.g. choice cost from `qty*price`), that field is missing and the test fails.
  - C3 check inside the same test (or `test_no_history_in_gameview`): the serialized `GameView` at turn 5 JSON has **no `history` key** and no nested `TurnResolution` beyond `latest_outcome` — `completion_summary` is `CompletionSummaryView`, not `StrategicSummary`.
  - C4 check: after submitting on the drought turn (turn index 3), assert `latest_outcome.world == "drought"` while top-level `world` is `aftermath` (since mapper derives top-level from `len(history)`), and `latest_outcome.resolved_turn == 3` with submitted `command_type`.

  Deleted: step 4 ("grep that Section 11's future client imports only GameView JSON") — Section 11 does not exist, so it passes against nothing. Replaced by the completeness list above — the failure mode it was trying to catch (missing field forces formula) is now caught by the list rather than by a vacuous grep.

  Kept separately, **re-labelled as internal-consistency** (not AC4 evidence): `test_gameview_internal_consistency` asserts `wealth == cash + grain*price//1000` from response fields only — proves consistency, but labels honestly that it *writes an economic formula into the test* and therefore is not proof the client avoids formulas (B3 circular). AC4 passes/fails on completeness alone.

### K5 — AC5 "engine imports no FastAPI" enforced by TEST

- **Decision:** Extend `backend/tests/test_engine_purity.py` to: (a) add `alembic` to `FORBIDDEN_TOP_LEVEL`, (b) assert no file under `backend/app/engine/` or `backend/app/domain/` contains `from app.api` or `import app.api` (reverse dependency). Still AST-walks `ENGINE_DIR + DOMAIN_DIR`.
- **Evidence:** `grep -rn "from.*fastapi" backend/app/engine/ backend/app/domain/` = 0 hits today; `FORBIDDEN_TOP_LEVEL` at `test_engine_purity.py:8` does not cover `alembic` or `app.api` — this extension makes the Section 8 shim regression fail fast.
- **Rejected:** Dependency linter / manual review.

### K6 — Determinism: how `run_seed` is chosen and reproduced — **AMENDED per B5**

- **Decision:** `POST /api/v1/games` body `CreateGameRequest{run_seed?: str, ruleset_version?: str}` optional. If `run_seed` absent, server generates `uuid4().hex` via `uuid`/`secrets` (not `random` global), creates `FiveTurnGame(seed=run_seed, version=...)`, and **echoes `run_seed` in `GameView.run_seed`** (B5 fix — original K4 schema omitted it, so omitted-seed games were unreproducible). `game_id` remains a separate session UUID. `ruleset_version` defaults to `"1.0"`. Same `(run_seed, ruleset_version, choice sequence)` → same history via `rng_for` BLAKE2 substreams.
- **Reproduction test:** `test_api_determinism` — two sessions with same explicit `run_seed="det-api-001"` and same 5 `choice_id`s produce identical `GET` JSON (prices, headlines, drivers). Second test: server-minted seed is echoed and re-POSTing a new game with that seed reproduces the first game's history.

### K7 — Minimal server surface & app wiring — **AMENDED per B6/B7/C6/C7**

- **Decision:** `backend/app/main.py` `create_app() -> FastAPI` factory (no DB lifespan), mounts `backend/app/api/router.py` (`APIRouter(prefix="/api/v1")`) with three routes. Plain module functions in `backend/app/api/service.py` (`create_game`, `get_game`, `choose`) — no class-based service. Add `fastapi` + `uvicorn` to `backend/pyproject.toml` `[project].dependencies`; add `httpx` + `pytest-asyncio` to **dev** dependencies per C6 (not relying on transitive `httpx` from `fastapi`; needed for `TestClient` + real async client in concurrency test). `SESSION_STORE: dict[str, GameSession]` where each `GameSession` owns its own `asyncio.Lock` (C5) in `backend/app/api/sessions.py`. `turn_limit` imported from `prototype.TURN_LIMIT`. Also extract `actor.ship_margin` per B6 covering `harness` + `turn.py` + `mappers.py`. C7 confirmed: no `revision_history` on `GameSession`; `created_at` harmless.

---

## Recommended Approach — **REVISED mapper & flow**

```
POST /api/v1/games {run_seed?, ruleset_version?}
  └─ generate game_id = uuid4().hex  (session key, NOT run_seed)
  └─ run_seed = body.run_seed or uuid4().hex  (deterministic seed, echoed)
  └─ FiveTurnGame(seed=run_seed, version=ruleset_version or "1.0")
  └─ revision=0
  └─ build GameView via mappers.to_game_view(session)
       signal = pressure_for_turn(len(history)).signal  # top-level = NEXT decision context (C4)
       markets = state.market / state.river_market
       route_status{established, capacity, transport_cost_per_unit, reliability_bps,
                    next_margin = actor.ship_margin(river_price, transport, home_price)}  # B6
       available_choices = mappers.choices_for(session)  # B1: legality/affordability only, 2 qty options each
       latest_outcome = None
       empire_summary = {farm_capacity, storage_capacity, route_established}  # C1: dormant OperationState reason
       turn_limit = TURN_LIMIT  # B7: imported, not literal
       completion_summary = None (not yet complete; C3: CompletionSummaryView when turn==TURN_LIMIT)
  └─ store SESSION_STORE[game_id] = GameSession{game_id, run_seed, revision, game, created_at, lock=asyncio.Lock()}  # C5 per-session

GET /api/v1/games/{game_id}
  └─ 404 if missing (B7)
  └─ async with session.lock: return to_game_view(session)  # C5: same per-session lock as choose; torn-view fix

POST /api/v1/games/{game_id}/choices/{choice_id} {expected_revision: int}
  └─ async with session.lock:                      # C5: per-session asyncio.Lock, async def
       1) missing field → 422 (FastAPI validation)
       2) unknown game_id → 404
       3) stale check: body.expected_revision != session.revision → 409 (no mutation)
       4) game_complete: session.game.is_complete → 409 {"detail":"game complete"} (B7: consistently 409)
       5) choice_id lookup: session.choice_map[choice_id] → 404 if missing
       6) command = choice.command
       7) ONLY: game.submit(command)  # rival choice + resolve_turn + rival settlement atomically
          never resolve_turn separately (would double-advance)
       8) revision += 1
       9) rebuild & return new GameView
          latest_outcome: OutcomeView{resolved_turn, title, pressure_stage, world, command_type, command_quantity,   # C4
                                     wealth_delta, drivers, domain_effects, causal_trace}  # B2: unconditional, latest only
          top-level signal/pressure_stage/world now = NEXT decision context (derived from len(history)); OutcomeView carries resolved context
          completion_summary: CompletionSummaryView when turn==TURN_LIMIT (C3)
```

Critical invariants still: API never calls `resolve_turn` besides `game.submit`; `choice_id` lookup is exact; `available_choices` recomputed on every response (B1/B7 regression `test_available_choices_turn_invariant` would fail if turn-index leaked in).

`choices_for` sketch (B1, two quantities):

```python
def choices_for(session) -> list[ChoiceView]:
    s = session.game.state
    out = [ChoiceView(id="hold", label="Hold — preserve cash", kind="hold", quantity=None, cost=0)]
    if s.player.cash >= EXPAND_FARM_COST:
        out.append(ChoiceView(id="expand_farm", label="Expand farm — 500 cash → +10 capacity", kind="expand_farm", cost=500))
    if s.player.cash >= BUILD_GRANARY_COST:
        out.append(ChoiceView(id="build_granary", label="Build granary — 300 cash → +50 storage", kind="build_granary", cost=300))
    if not s.route.established and s.player.cash >= ROUTE_ESTABLISH_COST:
        out.append(ChoiceView(id="secure_route", label="Secure river route — 400 cash", kind="secure_route", cost=400))
    # buy_grain: any turn, if headroom>0 — two options (partial/full)
    headroom = s.player.storage_capacity - (s.player.inventory.grain + s.player.farm_capacity * YIELD_PER_CAPACITY)
    affordable = ((s.player.cash + 1)*1000 - 1)//s.market.current_price if s.market.current_price>0 else 0
    max_buy = min(max(headroom,0), affordable, 80)
    if max_buy > 0:
        for qty in sorted({max_buy, max(1, max_buy//2)}):  # two options, deduped
            out.append(ChoiceView(id=f"buy_grain:{qty}", label=f"Buy {qty} grain — {cost_for_quantity(qty, s.market.current_price)} cash",
                                  kind="buy_grain", quantity=qty, cost=cost_for_quantity(qty, s.market.current_price)))
    # sell_grain: any turn, if inventory>0 — two options
    if s.player.inventory.grain > 0:
        n = min(s.player.inventory.grain, 150)
        for qty in sorted({n, max(1, n//2)}):
            out.append(ChoiceView(id=f"sell_grain:{qty}", label=f"Sell {qty} grain", kind="sell_grain", quantity=qty))
    # ship_grain: if established & inventory>0 — TWO options, no margin gate
    if s.route.established and s.player.inventory.grain > 0:
        cap = min(s.player.inventory.grain, s.route.capacity)
        for qty in sorted({cap, max(1, cap//2)}):
            out.append(ChoiceView(id=f"ship_grain:{qty}", label=f"Ship {qty} grain to River Town", kind="ship_grain", quantity=qty))
    return out
```

Amount constants (`80`, `150`, `capacity`) mirror the mapper's pre-clamp choices; the actual clamp still happens in `actor.resolve_*` and surfaces as `insufficient_*`.

---

## Work Plan

**Slice 1 — Engine helper + dependency + app skeleton (no logic, keeps AC6 green)**

1. Extract `actor.ship_margin(river_price, transport, home_price) -> int` in `backend/app/engine/actor.py`; update `engine/turn.py:1297` and `engine/harness.py:policy_trade_heavy` to call it (B6/C6). Pure refactor, no behaviour change — `make test` still 133 pass.
2. Add `fastapi>=0.110`, `uvicorn>=0.30` to `backend/pyproject.toml` `[project].dependencies`; add `httpx` + `pytest-asyncio` to **dev** (`[dependency-groups].dev`) per C6 (not transitive). `uv sync --project backend`.
3. Create `backend/app/api/__init__.py`, `backend/app/api/sessions.py` (`SESSION_STORE`, `GameSession{game_id, run_seed, revision, game, created_at, lock: asyncio.Lock}` — per-session lock C5, no revision_history C7), `backend/app/api/schemas.py` (`CreateGameRequest`, `CreateChoiceRequest{expected_revision: Annotated[int, Field(ge=0)]}`, `ChoiceView`, `GameView` with `run_seed`, `turn_limit` from `TURN_LIMIT`, `latest_outcome: OutcomeView` unconditional causal_trace, `CompletionSummaryView` API-owned, `empire_summary` three fields), `backend/app/api/mappers.py` (`to_game_view`, `choices_for` with B1 legality/affordability + two qty options, `OutcomeView` resolved context C4, `ship_margin` import), `backend/app/main.py` (`create_app()`), `backend/app/api/router.py` (three handlers, thin, delegate to service).

**Slice 2 — Logic + error semantics (B1/B2/B7/C3/C4/C5)**

4. Implement `backend/app/api/service.py` `create_game()`, `get_game()` (async with session.lock, 404 on unknown game_id), `choose()` with `async with session.lock:`, stale→409, complete→409, unknown choice_id→404, then single `game.submit(command)`, `revision+=1`, rebuild `GameView` with `OutcomeView` resolved context (C4) + `CompletionSummaryView` when complete (C3). Both `get_game` and `choose` take same per-session lock (C5 torn-view fix).
5. Ensure `latest_outcome` always carries `causal_trace` (latest turn only) — no `?trace=1`, no `debug_trace` (B2/C2). Measure payload size (node count, JSON bytes) in a test and assert ~40–60 nodes; if measurement shows blow-up, file finding instead of hiding.

**Slice 3 — Purity + tests + gates (B1–B5/B7/C3–C6)**

6. Extend `backend/tests/test_engine_purity.py` — add `alembic` to forbidden + reverse `from app.api` check (K5).
7. Add `backend/tests/test_api.py` (or `test_api_sessions.py`) covering:
   - `test_create_and_complete_five_turn_game` (AC1) — 1×create + 5× choices → `turn==TURN_LIMIT`, `revision==5`, `CompletionSummaryView` present (not StrategicSummary), 6th POST → 409.
   - `test_invalid_choice_cannot_mutate` (AC2) — POST bad `choice_id` → 404, GET unchanged (turn+revision).
   - `test_unknown_game_id_404` (B7) — `GET`/`POST` on random id → 404.
   - `test_no_history_in_gameview` (C3) — at turn 5 serialized `GameView` has no `history` key and no nested `TurnResolution` beyond `latest_outcome`; `completion_summary` has no `initial_state`/`final_state`/`history`.
   - `test_outcome_context_disambiguated` (C4) — after drought turn (idx 3), `latest_outcome.world=="drought"`, `latest_outcome.resolved_turn==3`, while top-level `world=="normal"` (aftermath); `latest_outcome.command_type` matches submitted.
   - `test_stale_revision_cannot_mutate` (AC3) — same-revision double POST, second 409, GET unchanged.
   - `test_concurrent_same_revision_one_wins` (K3/C5/C6) — real `httpx.AsyncClient` + `pytest-asyncio`, `asyncio.gather` two correct-revision POSTs → one 200 one 409.
   - `test_frontend_needs_no_formula` (AC4 completeness per B3) — exhaustive field checklist including `OutcomeView{resolved_turn, title, pressure_stage, world, command_type}+CompletionSummaryView` fields; fails if any value requires `qty*price`.
   - `test_gameview_internal_consistency` (labelled as such, not AC4) — `wealth == cash + grain*price//1000` from response fields.
   - `test_api_determinism` (K6/B5) — two sessions same explicit `run_seed` + same 5 choice_ids → identical GET JSON; minted `run_seed` echoed and re-seedable.
   - `test_available_choices_turn_invariant` (B1 regression) — fixed cash/inventory/route produces identical available_choices across turn_idx 0..4 except where `route.established` genuinely changed.
   - `test_available_choices_include_two_quantities` — `buy_grain:40`+`buy_grain:80` both present when affordable; `ship_grain` present even when `next_margin<0`.
   - `test_ship_margin_single_helper` — grep that `river - transport - home` appears only in `actor.ship_margin`.
   - `test_causal_trace_unconditional` — `latest_outcome.causal_trace` always present after turn 1, no `?trace` required, ~40–60 nodes.
   All existing 133 tests stay green.

Ordering invariant: Slice 1→2→3; each slice keeps `make test/lint/type` passing incrementally. Record in `DECISIONS.md` as new entry (e.g. 017): two-quantity design call plus verbatim principle "Section 10 exposes engine capabilities; it does not decide strategy …".

---

## Validation Plan

| Check | Command | Expected evidence |
|-------|---------|-------------------|
| Unit | `make test` (= `uv run --project backend pytest -v`) | 133 + ~14 new API tests pass. |
| API 5-turn | `test_create_and_complete_five_turn_game` | After 5th choice: `turn==TURN_LIMIT==5`, `revision==5`, `CompletionSummaryView` present (not StrategicSummary); 6th choice → 409. |
| No history | `test_no_history_in_gameview` (C3) | At turn 5 `GameView` JSON has no `history` key, no nested `TurnResolution` beyond `latest_outcome`; completion no `initial_state`/`final_state`. |
| Outcome context | `test_outcome_context_disambiguated` (C4) | After drought submit: `latest_outcome.world=="drought"` `resolved_turn==3` while top-level `world=="normal"` (aftermath). |
| Invalid choice | `test_invalid_choice_cannot_mutate` | Bad `choice_id` → 404; `GET` revision/turn unchanged. |
| Unknown game | `test_unknown_game_id_404` | `GET /games/bad` and `POST /games/bad/choices/hold` → 404 `detail:"game not found"`. |
| Stale revision | `test_stale_revision_cannot_mutate` | Second same-revision POST → 409 with `current_revision`; `GET` unchanged. |
| Concurrent | `test_concurrent_same_revision_one_wins` (C5/C6) | Real `httpx.AsyncClient` + `pytest-asyncio`, `asyncio.gather` two same-revision POSTs → one 200 one 409. |
| Turn invariant | `test_available_choices_turn_invariant` | Fixed state, turn 0..4 → identical choice sets (except established flip). |
| Two quantities | `test_available_choices_include_two_quantities` | `buy_grain:40`+`80`, `ship_grain` present even when `next_margin<0`. |
| Single helper | `test_ship_margin_single_helper` | Inline margin expression appears only in `actor.ship_margin`. |
| AC4 completeness | `test_frontend_needs_no_formula` | All decision-screen numbers present as fields incl. OutcomeView+CompletionSummaryView; no `qty*price` needed. |
| Consistency | `test_gameview_internal_consistency` | `wealth == cash+grain*price//1000` from response fields (labelled, not AC4). |
| Trace unconditional | `test_causal_trace_unconditional` | `latest_outcome.causal_trace.nodes` present (40–60 nodes measured), no `?trace`. |
| Determinism | `test_api_determinism` | Same seed+same choice_ids → identical JSON; minted `run_seed` echoed and re-seedable. |
| Purity guard | `make test -k test_engine_source_contains_no_forbidden_imports` | Fails if `fastapi`/`alembic`/`app.api` imported in engine/domain. |
| Lint/type/format | `make lint` → `make type` → `make format-check` | `All checks passed`, `0 errors`, `N files already formatted`. |
| Out-of-scope | `grep -R "sqlalchemy\|Alembic\|asyncpg\|Clerk\|openai" backend/app/api --include="*.py"` | 0 hits. |
| Payload measure | `test_causal_trace_unconditional` reports node count / JSON bytes | ~40–60 nodes; finding reported if >150. |

Manual/smoke not needed (headless API only until Section 11).

---

## Risks / Rollback

- **Risk: `choice_id:qty` invents arbitrary quantity.** Mitigated by server-chosen 2-quantity buckets in `available_choices`; unknown id → 404 before engine.
- **Risk: double `resolve_turn`.** Mitigated by single `game.submit()` delegation; test asserts `turn` +1 per POST.
- **Risk: `revision` vs `turn` confusion.** Keep distinct; tests assert both; `turn_limit` imported not literal.
- **Risk: causal_trace payload blow-up.** B2/C2 resolved: trace is unconditional, latest-only; measure node count and report if genuinely large (~40–60 expected); C3 ensures `completion_summary` does not smuggle 5 more traces.
- **Risk: torn view (C5).** Mitigated by per-session `asyncio.Lock` held by both `GET` and `POST`; without it a concurrent `POST` mid-`GET` mapper would mix pre/post values.
- **Rollback:** Delete `backend/app/api/`, `backend/app/main.py`, `actor.ship_margin` reverts to three inline copies, `CompletionSummaryView`/`OutcomeView` deleted, and `fastapi`/`uvicorn`/`httpx`/`pytest-asyncio` from deps — engine/domain unchanged so `make test` reverts to Section 9 green.

---

## Self-Grill (decision-forcing questions; answered from code/evidence)

### Q1 — Does `GameView` actually include `causal_trace`/`player_outcome.drivers`, or is that just in the engine?

**Evidence:** `engine/prototype.py:372` returns `TurnResolution{causal_trace: CausalTrace, player_outcome{drivers≤3}}`; `domain/trace.py:39` defines `CausalNode{parent_ids}`. Current in-memory game stores no view — so the plan's field list is not yet verified to be exposed.

**Answer:** Include `latest_outcome{drivers, domain_effects, causal_trace}` **unconditionally** after turn 1 (B2). Latest turn only — spec has exactly three endpoints with no query params; global §14 makes trace first-class and §9 makes the reveal signature. The "if it bloats" path was unmeasured; plan now measures node count (~40–60) and reports instead of hiding.

### Q2 — Is `test_engine_purity.py` actually checking `fastapi`, and could the new API slip an import into `engine`?

**Evidence:** `grep -rn "from.*fastapi" backend/app/engine/ backend/app/domain/` → 0 hits; `test_engine_purity.py:8` forbids `{"fastapi","sqlalchemy","httpx","asyncpg","openai","clerk"}` via AST walk — does **not** cover `alembic` or `from app.api`.

**Answer:** Extend forbidden set to include `alembic` and add reverse check for `from app.api` / `import app.api`. Converts good intentions into a test (K5, retained per review "keep as-is").

### Q3 — Could two concurrent `POST choices` with the same correct `expected_revision` both mutate? Could `GET` tear?

**Evidence:** Today `FiveTurnGame.submit` is synchronous with no lock; `sessions.py` does not exist, so no lock at all. The original plan also had `GET` without a lock ("no lock needed for read-only") — but the mapper walks `state/history/rivals`; a concurrent `choose()` mutating midway would produce a torn view mixing pre/post values (C5).

**Answer:** Each `GameSession` owns its own `asyncio.Lock` (C5). Both `choose()` and `get_game()` do `async with session.lock:`. Honest note: with no `await` between check and mutate the operation is already atomic on a single-threaded loop; the lock is defensive against a future `await` sneaking in, and for `GET` against torn reads. Per-session locks let unrelated games proceed independently (removing global serialization). Test `test_concurrent_same_revision_one_wins` uses a real `httpx.AsyncClient` + `pytest-asyncio` + `asyncio.gather` (C6) — only `async def` + `asyncio.Lock` is correctly exercised that way.

### Q4 — If the API returns a capped `actual=2` for `buy_grain:80`, does the frontend see the cap or just "bought 80"?

**Evidence:** `actor.resolve_buy` clamps `actual = min(requested, affordable, space)` with `insufficient_*`; `turn.py` emits `purchase_quantity_value` with `actual`.

**Answer:** Post `buy_grain:80` with cash for 20 → `200 OK` with trace `actual=20, reason=insufficient_cash`. Unknown `choice_id` → `404` (API concern); short-cash → clamped `200` (engine concern). No double implementation (retained per "keep as-is").

### Q5 — Does `available_choices` shrink after some choices (e.g., `secure_route` twice)?

**Evidence:** `prototype.py:307` returns 7 verbs unconditionally; `secure_route` after `established==True` would get `already_established` reason inside `resolve_secure_route`, not turn rejection.

**Answer:** Mapper regenerates `available_choices` from `route.established` + cash/inventory each response. **Revised:** gating is strictly `not established` and `cash >= cost` — never `turn==0` and never `margin>0`. New turn-invariant regression test proves "API adds no rules of its own."

### Q6 — Is `run_seed` optional or required, and can a player replay with an observed seed?

**Evidence:** `types.GameState{run_seed: str}` stores given string; `rng.rng_for` hashes `run_seed + version + …` via `blake2b`. No API generates a seed yet; `tests/test_determinism.py` passes explicit seeds.

**Answer:** `run_seed` optional on `POST /games`; if absent, server mints `uuid4().hex` via `uuid`/`secrets` and **echoes it as `GameView.run_seed`** (B5 fix — original schema omitted it). Reproducibility test posts the same 5 `choice_id`s with the echoed `run_seed` and asserts identical JSON.

### Q7 — Does any plan step build React or touch the DB?

**Evidence:** `DECISIONS.md 006`: in-memory until Section 16; BUILD_SPEC §10 OUT lists Postgres/SQLAlchemy/Alembic/auth/history/deploy; `pyproject.toml` has no `sqlalchemy`.

**Answer:** No `frontend/`, no `SQLAlchemy`/`alembic`, no `render.yaml`. Only `fastapi`+`uvicorn` (+ `httpx` for TestClient). Out-of-scope grep ensures it.

### Q8 — Where should `GameView` and mapping live so the engine never knows about HTTP status codes?

**Evidence:** `AGENTS.md §6`: `Router -> Service -> Client -> DB`, plain functions, `app/models` vs `app/schemas`. `engine/prototype.py` pure, `trace.py` uses `tuple`.

**Answer:** Keep `domain/types.py` + `trace.py` + `pressure.py` + `engine/*.py` unchanged except `actor.ship_margin` (B6). New files strictly `backend/app/api/*` + `backend/app/main.py`. No `engine`/`domain` file gains `fastapi`/`app.api` import.

### Q9 — What HTTP code for stale revision, and what if the user doesn't send `expected_revision`?

**Evidence:** Spec says "must fail", no code prescribed; `409 Conflict` conventional for optimistic concurrency; `422` for validation (Pydantic).

**Answer:** `CreateChoiceRequest{expected_revision: Annotated[int, Field(ge=0)]}` — absent → `422`; wrong value → `409` `{"expected_revision": X, "current_revision": Y}`. Game-complete on POST → **consistently `409` `{"detail":"game complete"}`** (B7 decided, not "409 or 400"). Unknown `game_id` → `404`.

### Q10 — Could `choice_id` be integer index (0,1,2) instead of `type:qty` strings?

**Evidence:** Integer IDs are ordering-fragile; string IDs are stable ELIs matching `prototype.available_commands()` strings.

**Answer:** Reject integer indexing; use stable `f"{type}" / f"{type}:{quantity}"` (retained per "keep as-is" — client copies `available_choices[*].id` verbatim).

---

## What The Grill Changed (vs original draft)

1. **Revision atomicity made explicit then tightened to per-session + GET.** Original `async with SESSION_LOCK` + `test_concurrent...` — Q3/B7. Round 2 C5 fixed the torn `GET` by giving each `GameSession` its own `asyncio.Lock` and requiring both `choose()` and `get_game()` to acquire it; global lock removed.
2. **AC4 operationalized then corrected per B3.** Original Q1 made a recomputation assertion the AC4 proof; B3 exposed it as circular and step 4 as vacuous. Now AC4 is a completeness checklist, with recomputation relabelled internal-consistency and grep deleted.
3. **AC5 guard extended beyond `fastapi`.** Surfaced `alembic` + reverse `app.api` leak (Section 8 shim pattern) — keep-as-is affirmed.
4. **Choice vs engine bound split clarified.** Unknown `choice_id` 404 (API), short-cash clamped 200 (engine) — Q4/B1 keep-as-is affirmed.
5. **Available-choices originally turn-gated + margin-gated — DELETED per B1 (BLOCKING).** Q5 originally preserved `margin>0` and harness turn windows; review proved `prototype.available_commands()` is unconditional and `resolve_turn` turn-agnostic. Now legality/affordability only, `ship_grain` even when `next_margin<0`, two quantities per verb, turn-invariant regression test. Harness as rules silently invalidated Section 9's "no dominant strategy".
6. **Rejected integer `choice_id`.** Q10 — stable strings (keep-as-is).
7. **Round 2 blockers C3/C4:** `completion_summary: StrategicSummary` → API-owned `CompletionSummaryView` (no history smuggling); `latest_outcome` conflation fixed by `OutcomeView` with `resolved_turn/title/pressure_stage/world/command_*` so top-level = next decision, `latest_outcome` = just-resolved.

## What This Revision Changed (vs plan before review)

1. **B1 (BLOCKING):** Deleted every turn-index condition (`turn<4`, `turn in (1,2)`, `turn==4`, `turn==0`) and the `river - transport - home > 0` gate on `ship_grain` from `available_choices`. Rebuilt from legality/affordability only (`cash>=cost`, `not established`, `inventory>0`, `headroom>0`). Added `test_available_choices_turn_invariant` regression and `test_available_choices_include_two_quantities` (partial+full). Changed quantity policy from single server-chosen amount to **two per verb** (partial+full) and will record in `DECISIONS.md` (e.g. 017) — design call per reviewer, keeps list ~6–8 items instead of 4–7.
2. **B2:** `latest_outcome` now carries **full `causal_trace` unconditionally, latest turn only** — deleted `debug_trace` / `?trace=1` path. "If it bloats" was unmeasured; plan now measures ~40–60 nodes and reports if genuinely large. Per C2, `?trace=1` would not have violated the spec (still same endpoint) — conclusion rests on the other three reasons (two `GameView` shapes, unresolvable reveal via `causal_node_ids` without nodes).
3. **B3:** Deleted vacuous step 4 (grep Section 11 imports). Relabelled `wealth == cash + grain*price//1000` as `test_gameview_internal_consistency` (not AC4 evidence). Replaced AC4 step with **completeness** assertions (every decision-screen number present as field; `qty*price` in test means missing field).
4. **B4/C1:** `empire_summary` stays `{farm_capacity, storage_capacity, route_established}` — but reason corrected per C1: `OperationState` **does exist** at `types.py:40` (mirrored a real type, not invented). The correct reason is dormant-type / single source of truth: `types.py:59` says it "exists as a standalone type for future Section 5 use" — not embedded in `PlayerState` to avoid duplicate capacity truth. Synthesizing `farm_1`/`granary_1` with invented `level` would create fictional canonical-looking state. Fix stated reason, keep shape.
5. **B5:** Added `run_seed: str` to `GameView` — fixes internal contradiction where K6 promised echo but K4 schema had only `game_id`.
6. **B6:** Added `actor.ship_margin(river_price, transport, home_price) -> int` — single pure helper replacing three copies (harness policy, `turn.py:1297` `arbitrage_margin`, mapper's `next_margin`).
7. **B7:** Decided lock = single global `asyncio.Lock` with `async def` handlers + honest atomicity note and MVP justification; cut `revision_history`; derived `turn_limit` from `prototype.TURN_LIMIT`; fixed game-complete to `409` consistently (`404` on unknown game_id already planned but now explicitly tested).
8. **C3 (BLOCKING):** `completion_summary: StrategicSummary` (contained `initial_state`/`final_state`/`history: tuple[TurnResolution,5]` with 5 full traces + `final_rivals`/`rival_history`) → API-owned `CompletionSummaryView{initial_wealth, final_wealth, wealth_delta_total, final_cash, final_grain, final_farm_capacity, final_storage_capacity, cash_low, peak_inventory, is_complete, final_rival_headlines: strings only}` — no `history`, no raw rival states. Test `test_no_history_in_gameview` asserts no `history` key in turn-5 `GameView`. Contradicted B2's "latest turn only".
9. **C4 (BLOCKING):** `latest_outcome` conflation fixed — added `OutcomeView{resolved_turn, title, pressure_stage, world, command_type, command_quantity}` so top-level `signal/pressure_stage/world` = next decision (`len(history)`), `OutcomeView.*` = just-resolved turn. Test `test_outcome_context_disambiguated` after drought turn checks `latest_outcome.world=="drought"` vs top-level `aftermath` and `resolved_turn==3`.
10. **C5:** `GET` now takes same **per-session** lock as `POST` (`session.lock`) — fixes torn view where mapper walks `state/history/rivals` mid-mutate. Global `SESSION_LOCK` replaced by `GameSession.lock: asyncio.Lock`; unrelated games no longer serialised.
11. **C6:** Added `httpx` + `pytest-asyncio` to dev deps (not transitive); concurrency test uses real `httpx.AsyncClient` + `ASGITransport` per `pytest-asyncio`.
12. **C7:** Confirmed `revision_history` dropped (no requirement/consumer; persistence scaffolding). `created_at` kept harmless.

## Revisions To Be Made Before Implementation (downward only)

- Do **not** add `backend/app/dependencies.py` DB wiring or `httpx.AsyncClient` lifecycle — `main.py` lifespan minimal for in-memory store.
- Do **not** offer a continuous quantity slider or 3–4 buckets per verb; exactly **two** (partial + full) per quantity verb is the decided point between §4 ("no spreadsheet tuning") and depth-of-commitment (Section 9 showed scaled buys mattered).
- Do **not** ship full 5-turn history or a history endpoint — `latest_outcome.causal_trace` is latest turn only; the other four turns are not returned.
- Do **not** reintroduce turn-index or `margin>0` gating — the harness is a measuring instrument, not game rules.

## Open Questions

- **None blocking.** One noted per B1: exact partial/full qty cut points (`max_buy//2` vs `80` cap) are mapper constants and can be tuned in Section 11 without engine change. One noted per B7: if concurrent play ever moves beyond MVP, promote the global lock to per-session locks — documented in mapper comment.

**Escalation:** Original task's "what exactly must GameView carry" is now answered deterministically in revised K4 with a field-by-field checklist and completeness test (B3). No open product-owner ambiguity remains.

---

## Review Round 1 — Change Log (B) + Round 2 — Change Log (C)

| ID | Before | After | Verdict |
|----|--------|-------|---------|
| B1 | `available_choices` gated on `turn<4`, `turn in (1,2)`, `turn==4`, `turn==0`, `margin>0`; single qty per verb; ~4–7 choices | Legality/affordability only (`cash>=cost`, `not established`, `inventory>0`, `headroom>0`); `ship_grain` even at loss; **two** qty options per verb (~6–8 choices); `ship_margin` helper; regression `test_available_choices_turn_invariant` | **BLOCKING — fixed** |
| B2 | `debug_trace` optional behind `?trace=1` ("if it bloats") | `latest_outcome.causal_trace` unconditional, latest turn only; measure ~40–60 nodes; C2: drop spec-violation claim, keep 3 reasons | Fixed (reason trimmed C2) |
| B3 | AC4 step 4 grep Section 11 imports (vacuous); `wealth==cash+grain*price//1000` as AC4 proof (circular) | Step 4 deleted; recomputation relabelled internal-consistency; AC4 is **completeness** (every screen number present as field) | Fixed |
| B4/C1 | `empire_summary.operations` claimed invented (grep wrong) | `empire_summary: {farm_capacity, storage_capacity, route_established}` — reason corrected: `OperationState` exists at `types.py:40` but dormant per `types.py:59`, not embedded in `PlayerState`; synthesizing would create second source of truth for capacity | Fixed (reason corrected C1) |
| B5 | `GameView` had `game_id` but no `run_seed` | `GameView.run_seed: str` added, distinct from `game_id` | Fixed |
| B6 | `river - transport - home` in 3 places | `actor.ship_margin()` single pure helper, called by harness + `turn.py` + mapper | Fixed |
| B7 | `asyncio.Lock` "or `threading.Lock`"; literal `turn_limit=5`; `revision_history` present; `409 or 400` on complete; no test for unknown game_id | **Per-session** `asyncio.Lock` + `async def` + honest note + `GET` also locked (C5); `turn_limit` from `TURN_LIMIT`; `revision_history` cut; **consistently `409`**; `test_unknown_game_id_404` | Fixed (lock upgraded C5) |
| C3 | `completion_summary: StrategicSummary` (with `history: tuple[TurnResolution,5]` + 5 traces + `final_rivals`/`rival_history`) — smuggled history endpoint, contradicts B2 | `CompletionSummaryView` API-owned: `{initial_wealth, final_wealth, wealth_delta_total, final_cash, final_grain, final_farm_capacity, final_storage_capacity, cash_low, peak_inventory, is_complete, final_rival_headlines: strings only}`; test `test_no_history_in_gameview` | **BLOCKING — fixed** |
| C4 | `latest_outcome` had no own context; top-level `world/pressure_stage` = next turn, `latest_outcome` = just-resolved — conflated reveal context | `OutcomeView{resolved_turn, title, pressure_stage, world, command_type, command_quantity, wealth_delta..., causal_trace}` — top-level = next decision, OutcomeView = just-resolved; test `test_outcome_context_disambiguated` drought vs aftermath | **BLOCKING — fixed** |
| C5 | `GET` without lock ("no lock needed for read-only") | `GET` + `POST` both `async with session.lock` — fixes torn view; global lock → per-session | Fixed |
| C6 | dev deps only `pytest` — `httpx`/`pytest-asyncio` missing | `httpx` + `pytest-asyncio` added explicitly; concurrency test uses `httpx.AsyncClient` + `pytest-asyncio` | Fixed |
| C7 | `revision_history` on `GameSession` | Dropped (no requirement/consumer) | Fixed |
| Keep-as-is | K3 revision-on-envelope + `409` stale/`422` missing, K5 guard, Q4 API-vs-engine split, Q10 stable string ids, `game.submit()` only, no DB/LLM/history | Untouched | Affirmed |

Implementing now per approval once C3–C6 reflected.
