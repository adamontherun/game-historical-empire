# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 10 — COMPLETE + Audit Round 2 fixes (2026-08-10) — R1/R2/R3

**Minimal FastAPI Boundary — in-memory sessions, three endpoints, presentation-correct GameView:** Exposes `FiveTurnGame` via `POST /api/v1/games`, `GET /api/v1/games/{id}`, `POST /api/v1/games/{id}/choices/{choice_id}` with `expected_revision` optimistic concurrency (per-session `asyncio.Lock` on `GameSession`, both GET and POST take lock; `choose` holds `await sleep(0)` inside lock per DECISIONS 021 to keep lock load-bearing until DB I/O lands (B3a falsifiable), `get_game` lock without yield; stale `409`, missing `422`, complete `409`, unknown id/choice `404`). `GameView` echoes `run_seed`+`ruleset_version`/`game_id`/`revision`/`turn`/`turn_limit=TURN_LIMIT`, `signal/pressure_stage/world` = next decision and `OutcomeView{resolved_turn,title,pressure_stage,world,command_type,command_quantity,drivers,domain_effects,causal_trace}` = just-resolved (C4); top-level aftermath vs outcome drought disambiguated. `causal_trace` unconditional latest-only (~40-60 nodes) inside `latest_outcome` (B2/C2), `CompletionSummaryView` API-owned end-screen values only (`initial_wealth/final_wealth/wealth_delta_total/final_cash/final_grain/final_farm_capacity/final_storage_capacity/cash_low/peak_inventory/is_complete/final_rival_headlines` strings — no `history`/`initial_state`/`final_state`/`RivalState`, C3). `empire_summary` is exactly `{farm_capacity, storage_capacity, route_established}` — dormant `OperationState` at `types.py:40` not embedded per `types.py:40` (C1 fixed). `available_choices` is legality+affordability only (`cash>=cost`, `not established`, `inventory>0`, `space>0`, no turn gating or `margin>0`, B1), two quantities per verb (partial+full, ~6-8 items; e.g. `buy_grain:55/110` unclamped `min(space, affordable)` no harness 80 cap per DECISIONS 022, `ship 10/20` even when `next_margin<0` via `actor.ship_margin` reliability-aware `river*reliability-transport-home` S0a used by harness+turn+mapper, B6/C3; S5 harvest via `compute_farm_output`). Engine stays pure via `test_engine_purity` forbidding `fastapi/alembic` and `from app.api` imports; `game.submit()` is sole mutation path.

### What exists

```
backend/
  app/
    main.py                    # create_app() -> FastAPI, mounts /api/v1 router
    api/
      __init__.py
      sessions.py              # GameSession{game_id, run_seed, revision, game, created_at, lock: asyncio.Lock, commands}, SESSION_STORE (eviction deferred until Section 16)
      schemas.py               # CreateGameRequest/ChoiceRequest, ChoiceView, PlayerSummary, EmpireSummary{3 fields}, MarketView, RouteStatus{next_margin}, RivalHeadlines, OutcomeView{resolved context + causal_trace}, CompletionSummaryView{no history}, GameView{run_seed, ruleset_version, turn_limit=TURN_LIMIT}
      mappers.py               # choices_for legality/affordability +2 qty: buy min(space,affordable)=55/110 no harness cap (R2/DECISIONS 022), ship pre-harvest, no turn/margin gate + to_game_view + choice_map_for + ship_margin/value_for helpers
      service.py               # create_game/get_game(with lock, no yield)/choose(with lock+sleep per DECISIONS 021, falsifiable) 404/409/422 game.submit() only
      router.py                # POST /api/v1/games, GET /api/v1/games/{id}, POST /.../choices/{choice_id}
    domain/
      types.py                 # OperationState dormant, RouteState delay 0, regional_output 360
      trace.py                 # CausalNode delta strict, OutcomeDriver top-3 residual doc (S4), top_drivers string view
      pressure.py              # PressureState 7 fields, causal_source_id single source
    engine/
      prototype.py             # TURN_LIMIT=5, default_start_state retuned 280/410/360/4000/130 (S7 value_for, demand tightness 5928 baseline)
      actor.py                 # ship_margin reliability-aware, cost/affordable inverse doc (N9), resolve_buy/sell
      harness.py               # policy_trade_heavy ship_margin reliability-aware, BatchConfig validation S0b, _wealth removed
      turn.py                  # S3 inventory_after_command, _bounded_price, arbitrage quantity-weighted
      rivals.py                # B4 partial-fill headlines, S5 harvest via compute_farm_output
      rng.py
      rounding.py
      cli.py                   # model_validate
    tests/
      test_api.py                # 15 tests: AC1 5-turn, AC2 invalid, AC3 stale, AC4 completeness, determinism, turn-invariant, two quantities (55/110 no cap R2), engine-agreement unclamped 110 (R2), ship_margin helper, causal unconditional, no-history, outcome disambiguated, concurrent lock (B3a falsifiable via DECISIONS 021), unknown 404, ruleset_version
      test_engine_purity.py      # forbids alembic + from app.api reverse dep
      test_balance_harness.py    # B3d swing falsifiable + price envelope
      test_five_turn_prototype.py
      test_deterministic_rivals.py
      test_invariants.py         # B3b strict movement
      test_two_markets_route.py  # B3c cash equality already_established
      test_causal_trace.py
      test_turn_kernel.py        # B3b price_bounded_movement
  pyrightconfig.json           # strict app + standard tests (38 files) via executionEnvironments
docs/plans/2026-08-10-section-10-fastapi-boundary.md  # plan revised for B1-B7 + C1-C7
docs/plans/2026-08-10-audit-sections-1-10-review-round-1.md  # consolidated audit round1
docs/plans/2026-08-10-audit-sections-1-10-review-round-2.md  # consolidated audit round2 (R1/R2/R3)
docs/plans/2026-08-10-audit-muse-findings.md  # independent audit
```

### Boundaries

- In-memory sessions only; no Postgres/SQLAlchemy/Alembic/auth/LLM/history endpoint/cloud deploy; no frontend scaffolding.
- `GameView` is presentation — frontend never recomputes cost/margin/wealth; `actor.ship_margin` reliability-aware + `actor.value_for`/`cost_for_quantity`/`affordable_quantity` single helpers, `actor.compute_farm_output` for harvest estimates.
- Per-session `asyncio.Lock` held by both GET and POST; `choose` holds `await sleep(0)` inside lock per DECISIONS 021 to keep lock load-bearing until DB I/O (Section 16) — removal makes `test_concurrent_same_revision_one_wins` fail `[200,200]` vs `[200,409]`; `get_game` lock without yield (no falsifying test, kept minimal); unrelated games independent. Revision is envelope `revision` distinct from `GameState.turn`; `turn_limit` derived from `prototype.TURN_LIMIT`.
- `available_choices` transport projection via `actor.affordable_quantity`/`value_for` and `actor.compute_farm_output` (B2/S5/S7), not recommendation engine — `buy_grain` is `min(space, affordable)=55/110` at start state with **no harness 80 cap** per DECISIONS 022 (harness keeps its own 80 as strategy); player may make economically bad choices (DECISIONS 017 principle verbatim). `ship_margin` includes reliability `(river*reliability//10000)-transport-home` (S0a). Removing `_bounded_price` cap fails `test_price_bounded_movement` (2505000 vs 1000), second `secure_route` double-charge fails `test_secure_route_creates_trade_access`, `largest_swing=0` fails `test_largest_swing_bounded` non-zero guard.
- Pure engine boundary: `engine`+`domain` import no `fastapi`/`alembic`/`app.api`; tested via `test_engine_purity`.
- `Makefile type` is `cd backend && uv run pyright` with `pyrightconfig.json` `include=["app","tests"]` `executionEnvironments` `app strict` / `tests standard` (38 files, 0 errors, proved via injection in `app/engine/rounding.py` and `tests/test_sanity.py` both failing) — DECISIONS 018 revised; `backend/pyproject.toml` also `include=["app","tests"]` for consistency.

### Normal verification

```bash
make test              # 149 passed
make lint              # All checks passed!
make type              # 0 errors, 0 warnings, 0 informations (pyrightconfig.json strict app + standard tests, 38 files)
make format-check      # 39 files already formatted
```

### Last known green

```
pytest 149 passed in 1.93s
ruff check All checks passed!
pyright 0 errors, 0 warnings, 0 informations — 38 files analyzed (strict app + standard tests via executionEnvironments)
ruff format --check 39 files already formatted
```

### Decisions relevant

- DECISIONS 017: two-quantity verb (partial+full), per-session lock, trace/latest-only, CompletionSummaryView (no history), OutcomeView disambiguation, OperationState dormant reason, ship_margin single helper, no-strategy-gatekeeping principle verbatim.
- DECISIONS 018 revised (R1): pyright scope `include=["app","tests"]` executionEnvironments app strict / tests standard (38 files, injection-proven).
- DECISIONS 021 (R3): per-session lock yield point — `choose` `await sleep(0)` inside lock load-bearing until DB I/O, `get_game` without yield.
- DECISIONS 022 (R2): buy cap removal — `choices_for` `min(space, affordable)` 55/110, harness 80 kept as strategy only.
- DECISIONS 016: matched controls, price-taking, hold rank 4/4 etc. unchanged.

### Intentionally missing

History endpoint, SQLAlchemy/Alembic/Postgres, auth, LLM, frontend (Section 11).

### Next milestone

Section 11 Mobile-First React Playable.
