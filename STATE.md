# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 8 — COMPLETE (2026-08-10)

**Pressure-driven event arc (Rev 4 — turn-derived pressure, mechanism-isolated warning):** Small coherent `normal→early_dry→worsening_dry→drought→aftermath` arc via **`backend/app/domain/pressure.py` + `backend/app/engine/pressure.py`** — `PressureStage` literal + frozen `PressureState{pressure_id, stage, activation_turn, world, signal, title, causal_source_id}` (exactly 7 fields, no `world_modifiers`), validator enforces biconditional `stage=="drought" <=> world=="drought"` (F2) and `causal_source_id == f"pressure:{id}:{stage}"` single source (F3), `PRESSURE_ARC` hard-coded 5 entries (activation_turn==index) with truthful rainfall prose (T2 `"Grain remains abundant, but the rains have begun to fail."` / T3 `"The dry spell persists. Farmers warn the next harvest is at risk."`, title keeps `Surplus`), reused via `pressure_for_turn(idx)` + `next_world_known_for_turn(idx)` (only `worsening_dry→drought`, not prose parsing). `TURN_SPECS` now **derived** `tuple(TurnSpec(world=p.world, signal=p.signal, title=p.title) for p in PRESSURE_ARC)` (single source), `FiveTurnGame` **session-authored** pressure (not canonical `GameState`): `submit` reads `pressure_for_turn(idx)` → `resolve_turn(state, command, pressure, ctx)` (world derived internally), `current_pressure: PressureState|None` (`None` when `is_complete`, else `pressure_for_turn(len(history))`; `pressure_for_turn(5)` raises), `current_signal/title` mirror pressure; **systemic** impact preserved: `resolve_turn` emits leading `pressure_stage` node (`kind="pressure"`, `delta=None`, `reason_code=pressure.causal_source_id` directly, not recomputed) parent of `world` (`pressure_stage→world→farm_output→home_supply→home_price→…→wealth`), no direct pressure→price edge, reuse `actor.compute_farm_output` (40%), no new RNG/loader/weighted sampler. **Mechanism-isolated AC1/AC3 instrument (F1):** both histories share T1 `hold` (timing-isolated) and avoid `expand_farm` in either arm (market-isolated) — `prep=[hold, build_granary, buy_grain:20, hold, hold]` vs `unprep=[hold, hold, hold, hold, hold]` on `seed-8-useful`: T4 `supply 100==100`, `price 4750==4750`, `farm_output 60==60` (identical shock, proven by equality pre-condition), yet `price_value_effect 130 vs 104` (delta 26), `inventory 250 vs 200`, `wealth 130 vs 104` — fully affordable (no `insufficient_*`), threshold-free. Backward compat shim in `turn.py` accepts bare `"normal"/"drought"` string from pre-8 tests (synthesized legacy pressure). `trace.py` validator not loosened — fallback `delta is None` already admits `pressure` kind (R3). TURN_ORDER now `pressure_stage -> world -> command -> production -> home_supply -> river_supply -> home_price -> river_price -> settlement -> route_settlement -> valuation`.

### What exists

```
backend/
  app/
    __init__.py
    domain/
      __init__.py            # re-exports domain + pressure (PressureStage/PressureState)
      types.py               # Money/... + GameState(Home+river+route)+RouteState+PlayerCommand(6 verbs) frozen ge=0
      trace.py               # CausalNode(tuple parents)/CausalTrace/OutcomeDriver/PlayerOutcome/TurnResolution frozen (validator unchanged — pressure admitted via delta None fallback)
      pressure.py            # NEW Section 8: PressureStage Literal + PressureState frozen 7 fields, validator stage<=>world + causal_source_id single source, turn-derived not canonical
    engine/
      __init__.py            # re-exports RNG+rounding+resolve_turn/TURN_ORDER + PRESSURE_ARC/pressure_for_turn/next_world_known/world_for_turn
      rng.py                 # derive_seed/make_rng/rng_for — JSON canonical -> blake2b
      rounding.py            # mul_basis_points/div_round_half_up/clamp_non_negative
      actor.py               # Shared primitives: YIELD_PER_CAPACITY/DROUGHT_BPS/COSTS + compute_farm_output/resolve_buy/resolve_storage_settlement/resolve_shipment/resolve_expand_farm/resolve_build_granary/resolve_secure_route/value_for/cost_for_quantity
      turn.py                # resolve_turn(state, command, pressure:PressureState|str, rng_context) — pressure_stage root (reason_code=causal_source_id) → world→production→…→valuation; world derived, shim for legacy string; keeps market+trace+wealth exact
      pressure.py            # NEW Section 8: PRESSURE_ARC 5 hard-coded (normal→early_dry→worsening_dry→drought→aftermath, truthful rainfall prose, T2 title Surplus), pressure_for_turn/next_world_known/world_for_turn, activation_turn==index validated at import, no RNG/loader
      rivals.py              # Deterministic rivals: RivalProfile(farm-averse/hungry prefs bps)/RivalState/RivalTurnResult/ObservableContext/SettlementContext + integer/bps scoring (threat boost only on worsening_dry→drought via next_world_known_for_turn from pressure), apply_rival_command via actor primitives
      prototype.py           # FiveTurnGame(state, history, rival_history, turn_limit=5, PRESSURE_ARC single source, TURN_SPECS derived, default_start_state Home 100/90/5000 River 80/130/5200 route 800/20/10000 storage200, turn==0 enforced, current_pressure None when complete, pressure_for_turn/next_world_known_for_turn, two-phase submit(choose pre→resolve player pressure→settle rivals), run->summary, StrategicSummary+_wealth)
      cli.py                 # Thin CLI: interactive + --choices non-interactive, per-turn display turn/signal/player HOME/RIVER ROUTE, after-commit 6 MONTHS LATER wealth/inventory/price WHY? drivers + MIRA/DARAN headlines (derived), --verbose adds rival details, ends STRATEGIC SUMMARY with rival lines (pressure stage display ready)
      demo.py                # Single-turn demo (demand 90) — now builds PressureState for world param (legacy shim demo)
  tests/
    test_sanity.py
    test_engine_purity.py
    test_core_types.py
    test_determinism.py
    test_rounding.py
    test_turn_kernel.py         # TURN_ORDER updated to pressure_stage->world->...
    test_invariants.py
    test_causal_trace.py        # world now child of pressure_stage; TURN_ORDER updated; world parent_ids == ("pressure_stage",)
    test_explanation.py
    test_two_markets_route.py
    test_five_turn_prototype.py # TURN_SPECS derived, titles/signals preserved (abundant/Surplus)
    test_deterministic_rivals.py
    test_pressure_arc.py        # NEW Section 8 AC1-5: arc 5 order + signals, 7-field exact, stage/world biconditional (F2) + causal_source_id single source (F3), warning-isolated+mechanism-isolated AC1+AC3 (hold+granary+buy vs hold*5 on seed-8-useful: supply 100==100 price 4750==4750 farm 60==60 yet price_value 130 vs 104 inv 250 vs 200), drought systemic chain pressure→world→farm→supply→price (no direct edge), determinism/inspectability (current_pressure None when complete, pressure_for_turn raises), structural smallness (no json/weighted/sampler, 5 only), threat only on worsening
  pyproject.toml             # uv project: pytest + ruff + pyright strict + pydantic>=2.7
  uv.lock
  .venv/
Makefile
.gitignore
.python-version              # 3.12 (root only)
AGENTS.md / backend/AGENTS.md / frontend/AGENTS.md
DECISIONS.md (001-012)
BUILD_SPEC.md Status: Sections 1-8 COMPLETE
docs/plans/
  2026-08-09-section-1-walking-skeleton.md
  2026-08-09-section-2-core-types.md
  2026-08-09-section-3-grain-market-kernel.md
  2026-08-09-section-4-causal-explanation.md
  2026-08-09-section-5-two-markets-route.md
  2026-08-09-section-6-five-turn-prototype.md  # Rev2
  2026-08-09-section-7-deterministic-rivals.md  # Rev2 shared primitives, two-phase timing, bps integer, structured threat
  2026-08-10-section-8-pressure-driven-event-arc.md  # Rev4 mechanism-isolated (F1), biconditional (F2), single source causal_source_id (F3), pressure.py location (F4), closeout (F5)
frontend/                    # placeholder for Section 11
docs/
graphify-out/                # graph.json 965 nodes/1668 edges, GRAPH_REPORT updated via graphify update .
```

### Boundaries

- `backend/app/engine` and `backend/app/domain` are pure: no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk`. Enforced by AST rglob test. `pydantic` allowed. `domain/pressure.py` holds PressureStage/PressureState (frozen, validator stage<=>world + causal_source_id); `engine/pressure.py` holds hard-coded PRESSURE_ARC (5, truthful prose, activation_turn==index) + pressure_for_turn/next_world_known/world_for_turn (no RNG/loader); `engine/turn.py` keeps `_target_price/_bounded_price`/supply signal + trace + pressure_stage root (reason_code=pressure.causal_source_id, parent of world); `engine/rivals.py` owns scoring/headlines via `next_world_known_for_turn` from pressure stage; `engine/prototype.py` owns session and PRESSURE_ARC-derived TURN_SPECS + current_pressure (None when complete).
- Canonical state frozen with immutable tuples; `PressureState` frozen 7 fields, `activation_turn 0..4`, validator `stage=="drought" <=> world=="drought"` (early_dry+drought and worsening_dry+drought and drought+normal all raise); `causal_source_id` default `f"pressure:{id}:{stage}"` and explicit mismatch raises; no `world_modifiers`; pressure is **turn-derived/session-authored** (R1/F2) — not in `GameState`, deterministically `pressure_for_turn(state.turn)`, so `GameState` remains canonical without duplication.
- Home supply remains signal `max(0, signal+farm_output-demand)` on `signal_next`, demand nodes in graph; River stable. `TURN_ORDER` now `pressure_stage -> world -> command -> production -> home_supply -> river_supply -> home_price -> river_price -> settlement -> route_settlement -> valuation` (updated in turn.py and tests). Rivals **do not mutate** shared `GameState.market.supply` (isolation); their production is private via `resolve_storage_settlement`. Shared constants/costs/clamping live in `actor.py`.
- FiveTurnGame session-owned: `state:GameState` + `history:5` + `_rivals:{mira,daran}` + `_rival_history:5×(Mira,Daran)`; calls `resolve_turn` once per submit with `pressure_for_turn(idx)`, validates `rng_context`, enforces `turn==0`, determinism via choices+seed. `PRESSURE_ARC` 5 truthful signals (T2 `"Grain remains abundant, but the rains have begun to fail."` keeps `abundant` substring + title `Surplus`; T3 worsening, T4 drought, T5 aftermath), `current_pressure` mirrors `current_spec` (`None` when complete, else `pressure_for_turn(len(history))`), threat derived as `next_world_known_for_turn(idx)==drought` only on `worsening_dry` (idx 2), never by parsing `signal`. Causal trace pressure chain `pressure_stage (reason_code=causal_source_id, kind=pressure, delta None, parent_ids ()) -> world (parent pressure_stage) -> farm_output (drought_reduced_yield, parent world) -> supply -> price (no direct pressure→price edge) -> … -> wealth`; `trace.py` validator not modified — pressure admitted via delta None fallback (R3).
- Wealth exact with revaluation: `quantity_value_effect = value(after, pre)-value(before, pre)`, `price_value_effect = value(after, resolved)-value(after, pre)`, `wealth_delta = cash+qty+price`; mechanism-isolated AC1/AC3 proves same market shock (T4 supply 100==100 price 4750==4750 farm 60==60) yet different exposure (price_value 130 vs 104, inv 250 vs 200, wealth 130 vs 104 on seed-8-useful, threshold-free, affordable).
- Determinism choices+seed via `rng_for` and `pressure_for_turn(idx)` (no global random, no `hash()`); no `world_modifiers`/JSON loader/weighted sampler/DSL.

### Normal verification

```bash
uv sync --project backend
make test              # = uv run --project backend pytest -v  (122 passed: 112 prior +10 new pressure tests)
make lint              # = ruff check backend  (All checks passed)
make type              # = pyright  (0 errors, 0 warnings)
make format-check      # = ruff format --check backend  (30 files already formatted)
```

### Last known green

```
uv sync --project backend  → Resolved 15 packages, 0 errors
pytest -v                  → 122 passed (8 core +7 rounding +11 determinism +2 purity/sanity +15 kernel +7 invariants +13 causal_trace (world child of pressure_stage, TURN_ORDER pressure_stage->world->... ) +4 explanation+13 two_markets_route+17 five_turn_prototype+16 deterministic_rivals +10 pressure_arc [arc 5 order + signals observational, 7-field exact, stage/world biconditional (early_dry+drought/worsening+drought/drought+normal raise) + causal_source_id single source, warning-isolated+mechanism-isolated AC1+AC3 (hold+granary+buy vs hold*5 on seed-8-useful: supply 100==100 price 4750==4750 farm 60==60 yet price_value 130 vs 104 inv 250 vs 200 wealth 130 vs 104 affordable threshold-free), drought systemic pressure→world→farm→supply→price no direct edge + reason_code==causal_source_id, determinism/inspectability current_pressure None when complete + pressure_for_turn raises, structural smallness no json/weighted/sampler, threat only on worsening])
ruff check backend         → All checks passed
ruff format --check backend→ 30 files already formatted
pyright                    → 0 errors, 0 warnings, 0 informations
demo                       → now via PressureState (legacy shim): normal/drought both via pressure, trace pressure_stage root
prototype hold 5           → hold×5 prints 5× 6 MONTHS LATER + MIRA/DARAN headlines each turn, ends STRATEGIC SUMMARY with 5/5 diffs + pressure_stage root in each trace (pressure_stage:pressure:legacy:normal / pressure:northern_drought:*)
cli parse                  → parse_choice("buy 20") -> buy_grain qty 20; backend/app/cli.py --choices "hold,build_granary,buy_grain,hold,hold" vs "hold,hold,hold,hold,hold" shows mechanism-isolated warning usefulness
actor primitives           → compute_farm_output/resolve_buy/... single source; turn.py and rivals.py both call same; costs 500/300/400/800 parity
graphify update .          → 965 nodes, 1668 edges, 73 communities; graph.json/graph.html/GRAPH_REPORT updated
```

Cache provenance fixed in YOLO (`~/.cache/uv/sdists-v9/.git` removed, `uv cache prune`), no `UV_CACHE_DIR` workaround needed.

### Decisions relevant to future work

- `uv` + Python 3.12, `ruff` (line-length 100, py312) + `pyright` strict
- Beta Acid layout deferred to Section 10; engine stays import-clean
- High autonomy within Section; `/plan` before Section, approve once; stop at gate and report
- Coverage tracked not gating until Sections 3-4; heavy unit on engine/domain
- `backend/pyproject.toml` location; root `Makefile` wrappers; `backend/uv.lock` tracked
- Section 2: `pydantic` for validated integer types; JSON canonical encoding for RNG; capacities single-source
- Section 3: `TURN_ORDER` explicit (now pressure_stage->world->command->production->home_supply->river_supply->home_price->river_price->settlement->route_settlement->valuation), drought reduces yield not price, buy clamped, integer price via basis points
- Section 4: exact wealth decomposition at old vs new price, immutable tuples for causal DAG, allowed roots now pressure_stage+command (world child of pressure_stage), story drivers as causal paths ranked by exact wealth-bps, filtered zero stories, RNG ownership validated, concise/verbose CLI
- Section 5: `market` stays Home alias + `river_market` + `route:RouteState`; `transport_cost_per_unit` in milliunits (800) comparable to price 5000; `TURN_ORDER` extended with home_supply/river_supply/home_price/river_price/route_settlement; river supply stable for divergence; `secure_route`/`ship_grain` with capacity/inventory/cash clamping; wealth with ship `purchase+harvest+ship+price+cash` exact; drivers include trade arbitrage at resolved prices; optional staleness deferred; regression: resolved Home price flips arbitrage
- Section 6: Home supply signal `signal_next = max(0, signal+farm_output-demand)`; River stable; `FiveTurnGame` session-owned `state+history`, `TURN_SPECS` 5 truthful signals, start Home 100/90/5000 River 80/130/5200 storage200, determinism choices-based
- Section 7: Session-owned rivals via `actor.py` shared primitives (no duplicated economy), two-phase timing (choose pre→player resolve→settle rivals buy@pre/ship@resolvedRiver/valuation@resolvedHome), integer/bps scoring `expected×pref×capital×risk×exposure` with threat boost only on `next_world_known==drought` (T3 warning, not signal parsing; now via pressure stage), `RivalProfile` (Mira 4500/15000/13000/14500 farm-averse, Daran 16000/7000 farm-hungry) vs `RivalState` (1200/25/5/250 vs 1400/15/12/150) proven via identical-state tests, `RivalTurnResult` history 5×(Mira,Daran) with `wealth=cash+qty+price` revaluation, headlines derived from outcome, isolation (player supply unchanged), deterministic exact-tie `rng_for`
- Section 8: Turn-derived pressure via `domain/pressure.py` + `engine/pressure.py` (PRESSURE_ARC 5, truthful rainfall prose, T2 title Surplus kept, activation_turn==index, no world_modifiers/loader/DSL), `PressureState` frozen 7 fields with validator `stage=="drought" <=> world=="drought"` + `causal_source_id` single source, `resolve_turn` pressure_stage root (reason_code=causal_source_id, delta None, parent of world; no direct pressure→price edge, systemic via farm_output→supply→price), `FiveTurnGame` pressure-derived TURN_SPECS + `current_pressure` None when complete, `trace.py` validator unchanged (pressure admitted via delta None fallback), mechanism+warning-isolated AC1/AC3 (hold+granary+buy vs hold*5 on seed-8-useful proves identical T4 market 100==100/4750==4750/60==60 yet different exposure 130 vs 104/250 vs 200), structural smallness (5 only, no json/weighted/sampler), determinism/inspectability via pressure_for_turn

### Intentionally missing (do not build early)

Balance harness (Section 9 — multi-seed sweeps, win rates), FastAPI/GameView/revision (Section 10), React UI (Section 11) etc. No DB/SQLAlchemy, LLMs, route congestion, contested supply, generic rival framework, content loader/world_modifiers/content_version (Section 15).

### Follow-up obligations

Section 8 follow-ups resolved: turn-derived pressure (R1/F2) not canonical GameState, biconditional validator, single-source causal_source_id (F3), domain/pressure.py location (F4), mechanism-isolated warning instrument (F1) with equality pre-condition (supply/price/farm_output identical) + threshold-free exposure difference, structural smallness, closeout per F5. graphify 965 nodes.

### Next milestone

**Section 9 — Headless Strategy and Balance Harness** — scripted harness over many seeds (production-heavy/storage-heavy/trade-heavy/cash-preserving/random), no universally dominant strategy, price bounds, deterministic batch.
