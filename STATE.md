# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 10 — COMPLETE (2026-08-10)

**Minimal FastAPI Boundary — in-memory sessions, three endpoints, presentation-correct GameView:** Exposes `FiveTurnGame` via `POST /api/v1/games`, `GET /api/v1/games/{id}`, `POST /api/v1/games/{id}/choices/{choice_id}` with `expected_revision` optimistic concurrency (per-session `asyncio.Lock` on `GameSession`, both GET and POST take it; stale `409`, missing `422`, complete `409`, unknown id/choice `404`). `GameView` echoes `run_seed`/`game_id`/`revision`/`turn`/`turn_limit=TURN_LIMIT`, `signal/pressure_stage/world` = next decision and `OutcomeView{resolved_turn,title,pressure_stage,world,command_type,command_quantity,drivers,domain_effects,causal_trace}` = just-resolved (C4); top-level aftermath vs outcome drought disambiguated. `causal_trace` unconditional latest-only (~40-60 nodes) inside `latest_outcome` (B2/C2), `CompletionSummaryView` API-owned end-screen values only (`initial_wealth/final_wealth/wealth_delta_total/final_cash/final_grain/final_farm_capacity/final_storage_capacity/cash_low/peak_inventory/is_complete/final_rival_headlines` strings — no `history`/`initial_state`/`final_state`/`RivalState`, C3). `empire_summary` is exactly `{farm_capacity, storage_capacity, route_established}` — dormant `OperationState` at `types.py:40` not embedded per `types.py:59` (C1) to avoid second source of truth. `available_choices` is legality+affordability only (`cash>=cost`, `not established`, `inventory>0`, `headroom>0`, no turn gating or `margin>0`, B1), two quantities per verb (partial+full, ~6-8 items; e.g. `buy_grain:30/60`, `ship` even when `next_margin<0` via `actor.ship_margin` single helper `river-transport-home` used by harness+turn+mapper, B6/C3). Engine stays pure via `test_engine_purity` forbidding `fastapi/alembic` and `from app.api` imports; `game.submit()` is sole mutation path.

### What exists

```
backend/
  app/
    main.py                    # create_app() -> FastAPI, mounts /api/v1 router
    api/
      __init__.py
      sessions.py              # GameSession{game_id, run_seed, revision, game, created_at, lock: asyncio.Lock, commands}, SESSION_STORE
      schemas.py               # CreateGameRequest/ChoiceRequest, ChoiceView, PlayerSummary, EmpireSummary{3 fields}, MarketView, RouteStatus{next_margin}, RivalHeadlines, OutcomeView{resolved context + causal_trace}, CompletionSummaryView{no history}, GameView{run_seed, turn_limit=TURN_LIMIT}
      mappers.py               # choices_for (legality/affordability +2 qty, no turn/margin gate) + to_game_view + choice_map_for + ship_margin
      service.py               # create_game/get_game/choose — per-session lock, 404/409/422, game.submit() only
      router.py                # POST /api/v1/games, GET /api/v1/games/{id}, POST /.../choices/{choice_id}
    domain/
      types.py                 # unchanged; OperationState dormant
      trace.py                 # unchanged
    engine/
      prototype.py             # TURN_LIMIT=5, default_start_state unchanged
      actor.py                 # + ship_margin(river, transport, home) single helper
      harness.py               # policy_trade_heavy now calls ship_margin
      turn.py                  # unchanged behavior (arbitrage quantity-weighted)
      rivals.py
      cli.py
  tests/
    test_api.py                # 14 tests: AC1 5-turn, AC2 invalid, AC3 stale, AC4 completeness+consistency, determinism, turn-invariant (B1), two quantities, ship_margin helper, causal unconditional (~40-60), no-history (C3), outcome disambiguated (C4), concurrent per-session lock, unknown 404
    test_engine_purity.py      # now forbids alembic + from app.api reverse dep
    test_balance_harness.py
    test_five_turn_prototype.py
    test_deterministic_rivals.py
docs/plans/2026-08-10-section-10-fastapi-boundary.md  # plan revised for B1-B7 + C1-C7
```

### Boundaries

- In-memory sessions only; no Postgres/SQLAlchemy/Alembic/auth/LLM/history endpoint/cloud deploy; no frontend scaffolding.
- `GameView` is presentation — frontend never recomputes cost/margin/wealth; `actor.ship_margin` is single engine helper, `actor.cost_for_quantity` for choice cost.
- Per-session `asyncio.Lock` held by both GET and POST prevents torn views; unrelated games independent. Revision is envelope `revision` distinct from `GameState.turn`; `turn_limit` derived from `prototype.TURN_LIMIT`.
- `available_choices` transport projection, not recommendation engine — harness policies never influence authorization; player may make economically bad choices (DECISIONS 017 principle verbatim).
- Pure engine boundary: `engine`+`domain` import no `fastapi`/`alembic`/`app.api`; tested.

### Normal verification

```bash
make test              # 148 passed (133 existing + 15 new)
make lint              # All checks passed!
make type              # 0 errors, 0 warnings
make format-check      # 40 files already formatted
```

### Last known green

```
pytest 148 passed in 2.87s
ruff check All checks passed!
pyright 0 errors, 0 warnings
```

### Decisions relevant

- DECISIONS 017: two-quantity verb (partial+full), per-session lock, trace/latest-only, CompletionSummaryView (no history), OutcomeView disambiguation, OperationState dormant reason, ship_margin single helper, no-strategy-gatekeeping principle verbatim.
- DECISIONS 016: matched controls, price-taking, hold rank 4/4 etc. unchanged.

### Intentionally missing

History endpoint, SQLAlchemy/Alembic/Postgres, auth, LLM, frontend (Section 11).

### Next milestone

Section 11 Mobile-First React Playable.
