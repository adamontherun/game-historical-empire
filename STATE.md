# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 9 — COMPLETE (2026-08-10)

**Headless Strategy and Balance Harness — regional_output + sell_grain economy + harness (Rev 2 + sell):** Fixed dominant hold (1909 vs 548) via regional non-player output (`MarketState.regional_output`, same `DROUGHT_YIELD_REDUCTION_BPS` via `_regional_output_after_world`, supply `signal+regional_after+farm-demand`) and retuned `default_start_state` to `280/400/360/4000/400` (21.7% share, surplus 60, price 3657-5381, storage cap binds but granary +50 now matters). Even after regional, hold still won 100% (3008) because grain had no sell path — output capped at 400 and thrown away, producing more lowered price. Added `sell_grain` (mirrors `buy_grain`, `resolve_sell` in `actor.py` reusing `cost_for_quantity`, clamped to inventory, `insufficient_inventory`, same milliunits). Both player and rivals can sell (Mira 14000 / Daran 9000 `sell_grain` prefs, `_expected_return` high price >5500, `_capital_bps`/`_risk_bps`, `choose_rival_command` candidates, headlines). `turn.py` handles `sell_grain` at command phase (`inventory_after_sell` + alias `inventory_after_buy` for valuation, `sell_quantity_value` driver), `cli.py` fixes `sell`→`sell_grain` (was `ship_grain` misleading, now `5:sell_grain` `6:secure_route` `7:ship_grain`). Harness: `storage_heavy` now `granary T0, buy 20 T1-2, sell 30 T3-4` after drought spike; `random_legal` includes `sell_grain`; new gate `hold_not_top` — `cash_preserving` median must NOT be max (at least one active beats holding). With sell, storage 3055 > hold 3008, hold_not_top PASS, median ratio 1.02 PASS (3008/3055? actually max 3055/second 3008 ratio 1.02), dead PASS (prod 2073 ≥0.70*2624), price/negativity PASS. Trace now `pressure_stage->world->regional_output/farm_output->home_supply`; `TURN_ORDER` includes `regional_output`; no bare-string `resolve_turn`. Balance table (200×5=1000 games): `production 2073` `storage 3055` `trade 2624` `cash 3008` `random 2181` — `max 3055 (storage) > cash`, hold not top, ratio 1.02. Tests updated legitimately (TURN_ORDER, supply 110→340/70→156 with regional parents, rival diffs 3→5, poor rival with inventory now sells).

### What exists

```
backend/
  app/
    __init__.py
    domain/
      __init__.py            # re-exports domain + pressure
      types.py               # Money/... + MarketState{..., regional_output=0}+RouteState+PlayerCommand{..., sell_grain} frozen (sell added Section 9)
      trace.py               # CausalNode/CausalTrace/OutcomeDriver frozen (validator unchanged — pressure/regional_output/sell via existing kinds)
      pressure.py            # PressureStage + PressureState 7 fields, biconditional + causal_source_id single source
    engine/
      __init__.py            # re-exports RNG+rounding+resolve_turn/TURN_ORDER+PRESSURE_ARC + harness BatchConfig/run_batch
      rng.py                 # derive_seed/make_rng/rng_for — JSON canonical -> blake2b
      rounding.py            # mul_basis_points/div_round_half_up/clamp_non_negative
      actor.py               # Shared primitives: YIELD_PER_CAPACITY/DROUGHT_BPS/COSTS + compute_farm_output/resolve_buy/resolve_sell/resolve_storage_settlement/resolve_shipment/... (sell added)
      turn.py                # resolve_turn(state, command, pressure:PressureState, ctx) — pressure_stage->world->farm+regional->home_supply->home_price...; handles buy/sell/ship, sell_quantity_value driver, TURN_ORDER with regional_output; no shim
      pressure.py            # PRESSURE_ARC 5 hard-coded + PRESSURE_NORMAL/DROUGHT + helpers
      rivals.py              # Deterministic rivals via actor primitives, now with sell_grain (prefs 14000/9000, expected_return, capital/risk, candidates, headlines, apply via resolve_sell)
      prototype.py           # FiveTurnGame(state,history,rival_history, turn_limit=5, PRESSURE_ARC single source, TURN_SPECS derived, default_start_state Home 280/400/5000/4000 regional360 River 80/130/5200 storage400, turn==0, current_pressure, two-phase submit, available_commands includes sell_grain)
      harness.py             # Section 9: BatchConfig/SeedResult/PolicyAggregate/BatchResult, 5 policies (storage now sells), run_batch deterministic, format_markdown/to_json, gates median-ratio/dead/hold_not_top/price/negativity (hold must not be top)
      cli.py                 # CLI: interactive + --choices + --balance harness (markdown+JSON, exit 2), aliases sell->sell_grain 5:sell 6:route 7:ship
      demo.py                # Single-turn demo via PressureState
  tests/
    test_sanity.py
    test_engine_purity.py
    test_core_types.py
    test_determinism.py
    test_rounding.py
    test_turn_kernel.py         # TURN_ORDER includes regional_output
    test_invariants.py
    test_causal_trace.py        # TURN_ORDER includes regional_output
    test_explanation.py
    test_two_markets_route.py
    test_five_turn_prototype.py # supply 340/156 with regional, parents regional+farm, available_commands includes sell_grain
    test_deterministic_rivals.py # poor with inventory now sells (was hold)
    test_pressure_arc.py        # warning-isolated still equality with regional
    test_balance_harness.py     # Section 9: 8 tests — harness 200 games <5s, median-ratio + dead + hold_not_top (storage>hold), negativity, price 3657-5381, swing, determinism, no bare-string, regional truthful farm0
  pyproject.toml             # uv project: pytest + ruff + pyright strict + pydantic>=2.7
  uv.lock
  .venv/
Makefile
.gitignore
.python-version              # 3.12 (root only)
AGENTS.md / backend/AGENTS.md / frontend/AGENTS.md
DECISIONS.md (001-014)
BUILD_SPEC.md Status: Sections 1-9 COMPLETE
docs/plans/
  2026-08-09-section-1-walking-skeleton.md
  2026-08-09-section-2-core-types.md
  2026-08-09-section-3-grain-market-kernel.md
  2026-08-09-section-4-causal-explanation.md
  2026-08-09-section-5-two-markets-route.md
  2026-08-09-section-6-five-turn-prototype.md  # Rev2
  2026-08-09-section-7-deterministic-rivals.md  # Rev2
  2026-08-10-section-8-pressure-driven-event-arc.md  # Rev4
  2026-08-10-section-9-balance-harness.md  # Rev2 + sell_grain (regional + sell)
  2026-08-10-section-8-review-round-1.md
  2026-08-10-section-8-review-round-2.md
  2026-08-10-section-8-review-round-3.md
  2026-08-10-section-9-review-round-1.md
frontend/                    # placeholder for Section 11
docs/
graphify-out/                # graph.json 1041 nodes/1856 edges, GRAPH_REPORT via graphify update .
```

### Boundaries

- `backend/app/engine` and `backend/app/domain` are pure: no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk`. Enforced by AST rglob test. `pydantic` allowed. `domain/types.py` MarketState now `supply/demand/regional_output/base_price/current_price/responsiveness/max_movement_bps` and `PlayerCommand` includes `sell_grain`; `engine/actor.py` single source for `resolve_buy`/`resolve_sell` (`sell` inverse of `buy` at Home price, clamped to inventory, `insufficient_inventory`), `engine/pressure.py` hard-coded PRESSURE_ARC; `engine/turn.py` handles `buy_grain`/`sell_grain`/`ship_grain` at command phase with `inventory_after_sell` + alias, `sell_quantity_value` driver, `_regional_output_after_world` reuses `DROUGHT_BPS`, `TURN_ORDER` with `regional_output`; `engine/rivals.py` scoring now includes `sell_grain` (Mira 14000, Daran 9000, `sell` revenue at Home price, holds before drought, sells when price >5500), `engine/prototype.py` session-owned and `default_start_state` `280/400/360/4000/400` (player 21.7% share, surplus 60, price 3657-5381), `engine/harness.py` pure batch runner via `FiveTurnGame` (no bare string, now with sell in storage/random).
- Canonical state frozen; `MarketState.regional_output` ge=0 default 0; supply `signal_next = max(0, signal + regional_after + farm_output - demand)`; demand nodes in graph; River stable exogenous. `TURN_ORDER` now `pressure_stage -> world -> command -> production -> regional_output -> home_supply -> river_supply -> home_price -> river_price -> settlement -> route_settlement -> valuation`.
- FiveTurnGame session-owned: `state:GameState` + `history:5` + `_rivals` + `_rival_history:5×(Mira,Daran)`; `pressure_for_turn` + `current_pressure` None when complete; two-phase submit; determinism via choices+seed. `available_commands` now 7 verbs including `sell_grain`; CLI aliases `sell`→`sell_grain` (fixed), `5:sell` `6:route` `7:ship`.
- Wealth exact with revaluation; causal chain `pressure_stage->world->regional_output/farm_output->home_supply->home_price->...->wealth` (pressure never directly parents price); `trace.py` validator unchanged; sell adds `sell_quantity_value` negative delta correctly, `cash_effect` includes revenue.
- Harness honest: deterministic policies seed-invariant on fixed arc, seed variation from `random_legal` only (now includes sell); median-ratio gates (1.60 dominant, 0.70 dead) plus `hold_not_top` (cash not max) — with sell, storage 3055 > hold 3008, hold_not_top PASS, ratio 1.02, production 2073 ≥0.70*2624 PASS.
- Determinism choices+seed via `rng_for` (no global random, no `hash()`); no `world_modifiers`/JSON loader/weighted sampler.

### Normal verification

```bash
uv sync --project backend
make test              # = uv run --project backend pytest -v  (130 passed: 122 prior +8 balance with hold_not_top)
make lint              # = ruff check backend  (All checks passed)
make type              # = pyright  (0 errors, 0 warnings)
make format-check      # = ruff format --check backend  (32 files already formatted)
```

### Last known green

```
uv sync --project backend  → Resolved 15 packages, 0 errors
pytest -v                  → 130 passed (8 core +7 rounding +11 determinism +2 purity/sanity +15 kernel +7 invariants +13 causal_trace (TURN_ORDER with regional_output) +4 explanation+13 two_markets_route+17 five_turn_prototype (supply 340/156 with regional, available_commands 7 verbs, rival diffs 5) +16 deterministic_rivals (poor now sells) +10 pressure_arc +8 balance_harness [harness 200 games <5s, storage 3055 > hold 3008 hold_not_top PASS, median_ratio 1.02 PASS dominant <1.60, dead PASS 2073≥1836, price 3657-5381 PASS [2000,9000], swing ≤2500, determinism double-run, no bare-string, regional truthful farm0 supply 96<240])
ruff check backend         → All checks passed
ruff format --check backend→ 32 files already formatted
pyright                    → 0 errors, 0 warnings, 0 informations
demo                       → via PressureState, trace now includes regional_output and sell_quantity_value
prototype hold 5           → hold×5 wealth 3008 (supply 280→... price 4739-5381), storage_heavy 3055 > hold, rivals 5 diffs
cli balance                → --balance --seeds 200 -> 1000 games <2s: production 2073 storage 3055 trade 2624 cash 3008 random 2181 hold_not_top PASS (storage top, cash not max)
harness determinism        → same config double-run identical JSON, prefix change varies random_legal (now with sell)
graphify update .          → 1041 nodes, 1856 edges, 86 communities; graph.json/graph.html/GRAPH_REPORT updated
```

### Decisions relevant to future work

- `uv` + Python 3.12, `ruff` (line-length 100, py312) + `pyright` strict
- Beta Acid layout deferred to Section 10; engine stays import-clean
- High autonomy within Section; `/plan` before Section, approve once; stop at gate and report
- Coverage tracked not gating until Sections 3-4; heavy unit on engine/domain
- `backend/pyproject.toml` location; root `Makefile` wrappers; `backend/uv.lock` tracked
- Section 2: `pydantic` for validated integer types; JSON canonical encoding for RNG; capacities single-source
- Section 3: `TURN_ORDER` explicit (now with regional_output), drought reduces yield not price, buy/sell clamped, integer price via basis points
- Section 4: exact wealth decomposition at old vs new price (now with sell negative quantity), immutable tuples for causal DAG, allowed roots now pressure_stage+command, story drivers ranked by wealth-bps, RNG ownership validated
- Section 5: `market` stays Home alias + `river_market` + `route:RouteState`; transport_cost 800 comparable; river stable; `secure_route`/`ship_grain`/`sell_grain` with clamping; wealth with ship+sell exact; drivers include trade arbitrage and sell
- Section 6: Home supply signal `signal_next = max(0, signal+regional_after+farm_output-demand)` with regional_output; River stable; `FiveTurnGame` session-owned, TURN_SPECS derived, start Home 280/400/5000/4000 regional360 storage400, determinism choices-based
- Section 7: Session-owned rivals via `actor.py` shared primitives (now includes sell), two-phase timing, integer/bps scoring with sell prefs 14000/9000, `RivalProfile` vs `RivalState`, `RivalTurnResult` history, isolation, deterministic tie-break
- Section 8: Turn-derived pressure via `domain/pressure.py` + `engine/pressure.py` (PRESSURE_ARC 5, truthful prose), `PressureState` 7 fields biconditional + causal_source_id single source, `resolve_turn` pressure_stage root, `FiveTurnGame` pressure-derived, `trace.py` unchanged, warning-isolated
- Section 9: Regional non-player output via `MarketState.regional_output` + `_regional_output_after_world` reusing `DROUGHT_BPS`, supply `signal+regional_after+farm-demand`, `regional_output` causal node, `TURN_ORDER` with regional_output, `default_start_state` retuned `280/400/360/4000/400` (player 21.7% share, surplus 60, price 3657-5381), adds `sell_grain` (`resolve_sell` inverse of `buy`, both player+rival, `sell` alias fixed, `available_commands` 7 verbs), harness `engine/harness.py` 5 policies (storage now sells), `BatchConfig/run_batch` deterministic, `cli --balance` markdown+JSON exit 2 with `hold_not_top` (storage 3055 > hold 3008, ratio 1.02, no dominant/dead, hold not top PASS)

### Intentionally missing (do not build early)

FastAPI/GameView/revision (Section 10), React UI (Section 11) etc. No DB/SQLAlchemy, LLMs, route congestion, contested supply, generic rival framework, content loader/world_modifiers/content_version (Section 15). Balance harness is Section 9 deliverable.

### Follow-up obligations

Section 9 complete with sell: regional_output + sell_grain fixes hold dominance (storage now beats hold 3055>3008, hold_not_top PASS) and makes drought truthful via regional even with farm 0; harness proves no dominant/dead/hold-not-top and price within bounds. graphify 1041 nodes. Next is Section 10 FastAPI.

### Next milestone

**Section 10 — Minimal FastAPI Boundary** — in-memory `POST /api/v1/games`, `GET /api/v1/games/{id}`, `POST /api/v1/games/{id}/choices/{choice_id}` with `GameView` and `expected_revision` staleness, engine stays pure.
