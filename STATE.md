# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 9 — COMPLETE (2026-08-10)

**Headless Strategy and Balance Harness — regional_output economy + harness (Rev 2):** Fixed universally dominant "hold" pathology by adding non-player regional production. **`backend/app/domain/types.py` now `MarketState{..., regional_output: Quantity=0}`** (Home only, River stays 0). **`backend/app/engine/turn.py` supply `signal_next = max(0, signal + regional_after + farm_output - demand)`** where `regional_after` reuses **same `DROUGHT_YIELD_REDUCTION_BPS=4000` via `_regional_output_after_world`** (no second formula). **`backend/app/engine/prototype.py` retuned `default_start_state` to `regional_output 360 + farm 10*10=100 =460, player 21.7% (15–25%), supply 280 demand 400 (surplus ~60, roughly stable), responsiveness 4000 (was 5000), storage 400 (was 200, cap was binding)** — demand stable, price within [2000,9000], production not dead. Trace now `pressure_stage -> world -> regional_output (parent world) -> home_supply (parents regional_output,farm_output,home_demand) -> home_price` alongside `farm_output -> home_supply`; drought felt even with `farm_capacity=0` via regional (price 6000 both hit cap but supply 96 vs 240, regional 216 vs 360). `TURN_ORDER` extended to `pressure_stage -> world -> command -> production -> regional_output -> home_supply -> ... -> valuation`. **New `backend/app/engine/harness.py`** pure sync — 5 policies (`production_heavy` expand once, `storage_heavy` granary+buy20×2, `trade_heavy` route+buy10+ship, `cash_preserving` hold×5, `random_legal` uniform affordable via `rng_for`), `BatchConfig{n_seeds,seed_prefix,version}`, `run_batch` deterministic, `format_markdown`/`to_json` stable, gates: dominant `max_median/second <1.60`, dead `median≥0.70*overall` (no win_rate floor — deterministic win_rate is 0/1 by construction, seed variation from `random_legal` only), price `[2000,9000]`, negativity no <0, largest swing ≤2500, determinism double-run equality. **CLI `backend/app/cli.py --balance --seeds 200 --seed-prefix harness --json-out`** prints markdown table, writes stable JSON, exit 2 on breach (reported first, now blocking since economy passes). No bare-string `resolve_turn` — harness delegates via `FiveTurnGame` (no `world: str` overload). Balance table (200 seeds ×5 =1000 games, final tuned constants): `production 2073` `storage 2752` `trade 2624` `cash 3008` `random 2117` — `max_median 3008/second 2752 ratio 1.09 PASS`, `dead PASS` (prod 2073 ≥0.70*2624=1836), `price 3657-5381 PASS`, `negativity PASS`. Existing tests updated legitimately (TURN_ORDER + regional_output, supply 110→340/70→156, rival diffs 3→5 with new market) — no deleted/loosened invariants.

### What exists

```
backend/
  app/
    __init__.py
    domain/
      __init__.py            # re-exports domain + pressure
      types.py               # Money/... + MarketState{..., regional_output=0}+RouteState+PlayerCommand frozen (regional_output added Section 9)
      trace.py               # CausalNode/CausalTrace/OutcomeDriver frozen (validator unchanged — pressure+regional_output via delta None / production)
      pressure.py            # PressureStage + PressureState 7 fields, biconditional + causal_source_id single source
    engine/
      __init__.py            # re-exports RNG+rounding+resolve_turn/TURN_ORDER+PRESSURE_ARC + harness BatchConfig/run_batch
      rng.py                 # derive_seed/make_rng/rng_for — JSON canonical -> blake2b
      rounding.py            # mul_basis_points/div_round_half_up/clamp_non_negative
      actor.py               # Shared primitives: YIELD_PER_CAPACITY/DROUGHT_BPS/COSTS + compute_farm_output/resolve_* (single source)
      turn.py                # resolve_turn(state, command, pressure:PressureState, ctx) — pressure_stage->world->farm_output+regional_output->home_supply->home_price...; world derived; _regional_output_after_world reuses DROUGHT_BPS; TURN_ORDER includes regional_output; no shim
      pressure.py            # PRESSURE_ARC 5 hard-coded (normal→early_dry→worsening_dry→drought→aftermath) + PRESSURE_NORMAL/DROUGHT + pressure_for_world/pressure_for_turn/next_world_known
      rivals.py              # Deterministic rivals via actor primitives, integer/bps scoring, structured threat
      prototype.py           # FiveTurnGame(state,history,rival_history, turn_limit=5, PRESSURE_ARC single source, TURN_SPECS derived, default_start_state Home 280/400/5000/4000 regional360 River 80/130/5200 storage400, turn==0, current_pressure, two-phase submit)
      harness.py             # NEW Section 9: BatchConfig/SeedResult/PolicyAggregate/BatchResult, 5 policies, run_batch deterministic, format_markdown/to_json, gates median-ratio/dead/price/negativity
      cli.py                 # CLI: interactive + --choices non-interactive + --balance harness (markdown+JSON, exit 2 on breach)
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
    test_five_turn_prototype.py # supply 340/156 with regional, parents include regional_output
    test_deterministic_rivals.py
    test_pressure_arc.py        # warning-isolated still equality, now with regional supply equality
    test_balance_harness.py     # NEW Section 9: 8 tests — harness 200 games <5s, median-ratio dominant/dead, negativity, price bounds, swing, determinism double-run, no bare-string, regional truthful (farm 0 drought via regional)
  pyproject.toml             # uv project: pytest + ruff + pyright strict + pydantic>=2.7
  uv.lock
  .venv/
Makefile
.gitignore
.python-version              # 3.12 (root only)
AGENTS.md / backend/AGENTS.md / frontend/AGENTS.md
DECISIONS.md (001-013)
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
  2026-08-10-section-9-balance-harness.md  # Rev2 (regional_output fix, median-ratio gates, reported-first)
  2026-08-10-section-8-review-round-1.md
  2026-08-10-section-8-review-round-2.md
  2026-08-10-section-8-review-round-3.md
  2026-08-10-section-9-review-round-1.md
frontend/                    # placeholder for Section 11
docs/
graphify-out/                # graph.json 1180 nodes/2100 edges, GRAPH_REPORT via graphify update .
```

### Boundaries

- `backend/app/engine` and `backend/app/domain` are pure: no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk`. Enforced by AST rglob test. `pydantic` allowed. `domain/types.py` MarketState now `supply/demand/regional_output/base_price/current_price/responsiveness/max_movement_bps`; `engine/pressure.py` hard-coded PRESSURE_ARC + helpers; `engine/turn.py` keeps `_target_price/_bounded_price` + `regional_output` node + `home_supply` parents `(regional_output,farm_output,home_demand)` and `TURN_ORDER` with `regional_output`; `engine/rivals.py` scoring via `next_world_known`; `engine/prototype.py` session-owned and `default_start_state` now `supply 280/demand 400/regional 360/responsiveness 4000/storage 400` (was 100/90/5000/200) — player 21.7% share, demand ~stable (+60), price 3657-5381 within [2000,9000]; `engine/harness.py` pure batch runner via `FiveTurnGame` (no bare string).
- Canonical state frozen; `MarketState.regional_output` ge=0 default 0; supply `signal_next = max(0, signal + regional_after + farm_output - demand)` with `regional_after` via same `DROUGHT_YIELD_REDUCTION_BPS` (single formula); demand nodes in graph; River stable exogenous. `TURN_ORDER` now `pressure_stage -> world -> command -> production -> regional_output -> home_supply -> river_supply -> home_price -> river_price -> settlement -> route_settlement -> valuation`.
- FiveTurnGame session-owned: `state:GameState` + `history:5` + `_rivals` + `_rival_history:5×(Mira,Daran)`; `pressure_for_turn` + `current_pressure` None when complete; two-phase submit; determinism via choices+seed. `PRESSURE_ARC` 5 truthful signals, `StrategicSummary` + rival headlines.
- Wealth exact with revaluation; causal chain `pressure_stage->world->regional_output/farm_output->home_supply->home_price->...->wealth` (pressure never directly parents price); `trace.py` validator unchanged (regional_output kind production, delta handling via existing).
- Harness honest: deterministic policies are seed-invariant on fixed arc, seed variation from `random_legal` only via `rng_for`; median-ratio gates (1.60 dominant, 0.70 dead) generous; 200 seeds ×5 =1000 games <5s; exit 2 on breach reported, now blocking since tuned passes (2073/2624/2752/3008 ratio 1.09).
- Determinism choices+seed via `rng_for` (no global random, no `hash()`); no `world_modifiers`/JSON loader/weighted sampler.

### Normal verification

```bash
uv sync --project backend
make test              # = uv run --project backend pytest -v  (130 passed: 122 prior +8 new balance tests)
make lint              # = ruff check backend  (All checks passed)
make type              # = pyright  (0 errors, 0 warnings)
make format-check      # = ruff format --check backend  (32 files already formatted)
```

### Last known green

```
uv sync --project backend  → Resolved 15 packages, 0 errors
pytest -v                  → 130 passed (8 core +7 rounding +11 determinism +2 purity/sanity +15 kernel +7 invariants +13 causal_trace (TURN_ORDER with regional_output) +4 explanation+13 two_markets_route+17 five_turn_prototype (supply 340/156 with regional, parents regional+farm) +16 deterministic_rivals (5 diffs with new market) +10 pressure_arc +8 balance_harness [harness 200 games <5s, median_ratio 1.09 PASS dominant <1.60, dead PASS median≥0.70*overall (2073≥1836), negativity PASS, price 3657-5381 PASS [2000,9000], swing ≤2500 PASS, determinism double-run identical + sensitivity, no bare string, regional truthful farm0 drought supply 96<240 and regional 216<360])
ruff check backend         → All checks passed
ruff format --check backend→ 32 files already formatted
pyright                    → 0 errors, 0 warnings, 0 informations
demo                       → via PressureState, trace now includes regional_output parented by world, home_supply parented by regional+farm
prototype hold 5           → hold×5 wealth ~3008 with new economy (supply 280→340→... price 4739-5381), MIRA/DARAN 5 diffs
cli balance                → --balance --seeds 200 -> 1000 games <2s: production 2073 storage 2752 trade 2624 cash 3008 random 2117 ratio 1.09 PASS, price 3657-5381 PASS
harness determinism        → same config double-run identical JSON, prefix change varies random_legal
graphify update .          → 1180 nodes, 2100 edges, 73 communities; graph.json/graph.html/GRAPH_REPORT updated
```

### Decisions relevant to future work

- `uv` + Python 3.12, `ruff` (line-length 100, py312) + `pyright` strict
- Beta Acid layout deferred to Section 10; engine stays import-clean
- High autonomy within Section; `/plan` before Section, approve once; stop at gate and report
- Coverage tracked not gating until Sections 3-4; heavy unit on engine/domain
- `backend/pyproject.toml` location; root `Makefile` wrappers; `backend/uv.lock` tracked
- Section 2: `pydantic` for validated integer types; JSON canonical encoding for RNG; capacities single-source
- Section 3: `TURN_ORDER` explicit (now with regional_output), drought reduces yield not price, buy clamped, integer price via basis points
- Section 4: exact wealth decomposition at old vs new price, immutable tuples for causal DAG, allowed roots now pressure_stage+command (regional_output also root child of world), story drivers ranked by wealth-bps, RNG ownership validated, concise/verbose CLI
- Section 5: `market` stays Home alias + `river_market` + `route:RouteState`; transport_cost 800 comparable; river stable; `secure_route`/`ship_grain` with clamping; wealth with ship exact; drivers include trade arbitrage at resolved prices
- Section 6: Home supply signal `signal_next = max(0, signal+regional_after+farm_output-demand)` with regional_output; River stable; `FiveTurnGame` session-owned, TURN_SPECS derived, start Home 280/400/5000/4000 regional360 storage400, determinism choices-based
- Section 7: Session-owned rivals via `actor.py` shared primitives, two-phase timing, integer/bps scoring with structured threat, `RivalProfile` vs `RivalState`, `RivalTurnResult` history, isolation, deterministic tie-break
- Section 8: Turn-derived pressure via `domain/pressure.py` + `engine/pressure.py` (PRESSURE_ARC 5, truthful prose), `PressureState` 7 fields biconditional + causal_source_id single source, `resolve_turn` pressure_stage root, `FiveTurnGame` pressure-derived, `trace.py` unchanged, warning-isolated
- Section 9: Regional non-player output via `MarketState.regional_output` + `_regional_output_after_world` reusing `DROUGHT_YIELD_REDUCTION_BPS` (single formula), supply `signal+regional_after+farm-demand`, `regional_output` causal node (parent world) -> `home_supply` (parents regional+farm), `TURN_ORDER` with regional_output, `default_start_state` retuned `supply 280/demand 400/regional 360/responsiveness 4000/storage 400` (was 100/90/5000/200) — player 21.7% share, roughly stable (+60), price 3657-5381, harness `engine/harness.py` 5 policies, `BatchConfig/run_batch` deterministic, `cli --balance` markdown+JSON exit 2 reported (now blocking since passes: 2073/2752/2624/3008 ratio1.09), no bare string, honest seed-invariant note, 8 new tests

### Intentionally missing (do not build early)

FastAPI/GameView/revision (Section 10), React UI (Section 11) etc. No DB/SQLAlchemy, LLMs, route congestion, contested supply, generic rival framework, content loader/world_modifiers/content_version (Section 15). Balance harness is the Section 9 deliverable — no further tuning beyond median-ratio gates.

### Follow-up obligations

Section 9 complete: regional_output economy (single field + single drought primitive + retuned constants 280/400/360/4000/400) fixes dominant hold and makes drought truthful via regional even with farm 0; harness proves no dominant/dead (ratio 1.09) and price within bounds. graphify 1180 nodes. Next is Section 10 FastAPI.

### Next milestone

**Section 10 — Minimal FastAPI Boundary** — in-memory `POST /api/v1/games`, `GET /api/v1/games/{id}`, `POST /api/v1/games/{id}/choices/{choice_id}` with `GameView` and `expected_revision` staleness, engine stays pure.
