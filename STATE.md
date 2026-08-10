# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 7 — COMPLETE (2026-08-09)

**Deterministic rivals (Rev2 — shared primitives, structured threat, integer scoring):** Mira (storage/trade/flexible, farm-averse, moderate risk, reacts early) and Daran (farmland scale, farm-hungry, aggressive, vulnerable) via **integer/bps scoring** `score = expected_return × pref_bps × capital_bps × risk_bps × exposure_bps` with deterministic `rng_for` tie-break only on exact integer equality, **session-owned** inside `FiveTurnGame` (not in canonical `GameState`, isolated supply), **shared actor primitives** extracted to `actor.py` (`compute_farm_output`, `resolve_buy`, `resolve_storage_settlement`, `resolve_shipment`, `value_for`/`cost_for_quantity`) called by both `turn.py` and `rivals.py` so costs/clamping cannot diverge, **two-phase timing** (rivals choose from pre-turn observable `ObservableContext{world_now, next_world_known, home_price_pre…}`, then player `resolve_turn` resolves markets, then rivals settle with `buy@pre_home`, `shipment@resolved_river`, `valuation@resolved_home`), **structured threat** `next_world_known` (T3 warning → drought) not prose parsing, `RivalProfile` vs `RivalState` separation with identical-state personality tests, `RivalTurnResult{before, command, after, headline, cash/quantity/price/wealth deltas}` history `tuple[tuple[Mira,Daran],5]` with derived `rival_headlines_history`, wealth `cash+quantity+price` with price revaluation, truthful headlines derived from resolved outcome, at least one headline per turn after first, legible fingerprint across contexts.

### What exists

```
backend/
  app/
    __init__.py
    domain/
      __init__.py            # re-exports + types+RouteState
      types.py               # Money/... + GameState(Home+river+route)+RouteState+PlayerCommand(6 verbs) frozen ge=0
      trace.py               # CausalNode(tuple parents)/CausalTrace/OutcomeDriver/PlayerOutcome/TurnResolution frozen
    engine/
      __init__.py            # re-exports RNG+rounding+resolve_turn/TURN_ORDER
      rng.py                 # derive_seed/make_rng/rng_for — JSON canonical -> blake2b
      rounding.py            # mul_basis_points/div_round_half_up/clamp_non_negative
      actor.py               # NEW shared primitives: YIELD_PER_CAPACITY/DROUGHT_BPS/COSTS + compute_farm_output/resolve_buy/resolve_storage_settlement/resolve_shipment/value_for/cost_for_quantity (single source, integer, re-exported by turn.py)
      turn.py                # resolve_turn — now calls actor primitives (command->production->home_supply->river_supply->home_price->river_price->settlement->route_settlement->valuation); keeps market+trace, wealth exact with ship
      rivals.py              # NEW deterministic rivals: RivalProfile(farm-averse/hungry prefs bps)/RivalState(cash/inventory/farm/storage/route, no headline)/RivalTurnResult(before/command/after/headline/cash/qty/price/wealth deltas)/ObservableContext/SettlementContext + integer/bps scoring (expected_return×pref×capital×risk×exposure, threat boost T3→drought, exact-tie rng_for) + apply_rival_command via actor primitives + truthful headlines; MIRA_START 1200/25/5/250/DARAN 1400/15/12/150
      prototype.py           # FiveTurnGame(state, history, rival_history, turn_limit=5, TURN_SPECS[5] truthful, default_start_state Home 100/90/5000 River 80/130/5200 route 800/20/10000 storage200, turn==0 enforced, _observable_for/_next_world_known_for_turn(T3→drought), two-phase submit(choose pre→resolve player→settle rivals at pre/resolved prices), run->summary, StrategicSummary{history, rival_history, final_rivals, final_wealth, cash_low, peak, format() with T Rivals lines} + _wealth)
      cli.py                 # Thin CLI: interactive + --choices non-interactive, per-turn display turn/signal/player HOME/RIVER ROUTE, after-commit 6 MONTHS LATER wealth/inventory/price WHY? drivers + MIRA/DARAN headlines (derived), --verbose adds rival details, ends STRATEGIC SUMMARY with rival lines
      demo.py                # Single-turn demo (demand 90)
  tests/
    test_sanity.py
    test_engine_purity.py
    test_core_types.py
    test_determinism.py
    test_rounding.py
    test_turn_kernel.py
    test_invariants.py
    test_causal_trace.py
    test_explanation.py
    test_two_markets_route.py
    test_five_turn_prototype.py
    test_deterministic_rivals.py # NEW Section 7 AC1-6: profiles differ under identical state (≥2 diffs, Mira storage> Daran, Daran farm> Mira), determinism same seed, capital via shared primitives (zero-cash hold, no negatives, cost parity, buy cap, ship cap), no-money-creation with price revaluation (wealth==cash+qty+price, hold 20 grain 5000→6000 qty120 price120), behavioral preparation vs concentration (Mira prep > baseline +40% on warning, Mira prep>farm, Daran farm>prep), fingerprint across 5 contexts (surplus/warning/drought/lowcash/tight), headlines derived & visible after first (len5, T2+ non-empty, truthful expand+10/cash-500 etc), execution same rules, market isolation (player supply same as raw resolve_turn 5 holds), no float, structured threat not prose, RivalState no headline, exact-tie rng
  pyproject.toml             # uv project: pytest + ruff + pyright strict + pydantic>=2.7
  uv.lock
  .venv/
Makefile
.gitignore
.python-version              # 3.12 (root only)
AGENTS.md / backend/AGENTS.md / frontend/AGENTS.md
DECISIONS.md (001-011)
BUILD_SPEC.md Status: Sections 1-7 COMPLETE
docs/plans/
  2026-08-09-section-1-walking-skeleton.md
  2026-08-09-section-2-core-types.md
  2026-08-09-section-3-grain-market-kernel.md
  2026-08-09-section-4-causal-explanation.md
  2026-08-09-section-5-two-markets-route.md
  2026-08-09-section-6-five-turn-prototype.md  # Rev2
  2026-08-09-section-7-deterministic-rivals.md  # Rev2 shared primitives, two-phase timing, bps integer, structured threat, profile vs state, full history with revaluation
frontend/                    # placeholder for Section 11
docs/
```

### Boundaries

- `backend/app/engine` and `backend/app/domain` are pure: no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk`. Enforced by AST rglob test. `pydantic` allowed. `engine/actor.py` holds shared integer settlement; `engine/turn.py` keeps `_target_price/_bounded_price`/supply signal and trace; `engine/rivals.py` owns scoring/headlines; `engine/prototype.py` owns session and `TURN_SPECS` + threat mapping. `cli.py` at top-level app is not checked but also pure stdlib+domain+engine.
- Canonical state frozen with immutable tuples; `RivalState` frozen `ge=0` without headline; `RivalProfile` frozen prefs bps; `RivalTurnResult` frozen with full deltas and wealth `cash+qty+price` (price revaluation at `home_resolved`); rival wealth never floats.
- Home supply remains signal `max(0, signal+farm_output-demand)` on `signal_next`, demand nodes in graph; River stable. Rivals **do not mutate** shared `GameState.market.supply` (isolation, verified by `test_player_market_isolation`); their production is private via `resolve_storage_settlement`. Shared constants/costs/clamping live in `actor.py` and are imported (not duplicated).
- FiveTurnGame session-owned: `state:GameState` + `history:5` + `_rivals:{mira,daran}` + `_rival_history:5×(Mira,Daran)`; calls `resolve_turn` once per submit after rival choice, validates `rng_context`, enforces `turn==0`, determinism via choices+seed. `TURN_SPECS` 5 truthful signals, threat derived as `_next_world_known_for_turn(idx)==drought` only on idx 2 (Warning → Drought), never by parsing `signal`. Headlines derived from `RivalTurnResult.headline`, not stored in `RivalState`.
- Wealth exact with revaluation: `quantity_value_effect = value(after, pre)-value(before, pre)`, `price_value_effect = value(after, resolved)-value(after, pre)`, `wealth_delta = cash+qty+price`; rival hold through 5000→6000 with 20→120 grain yields qty 500 + price 120 = 620, tested.
- Determinism choices+seed via `rng_for(..., "rival", rival_id, 0)` only on exact integer tie; no `hash()` or global `random`.

### Normal verification

```bash
uv sync --project backend
make test              # = uv run --project backend pytest -v  (109 passed: 96 prior + 13 new)
make lint              # = ruff check backend  (All checks passed)
make type              # = pyright  (0 errors)
make format-check      # = ruff format --check backend  (27 already formatted)
```

### Last known green

```
uv sync --project backend  → Resolved 15 packages, 0 errors
pytest -v                  → 109 passed (8 core + 7 rounding + 11 determinism + 2 purity/sanity + 15 kernel + 7 invariants + 12 causal_trace + 4 explanation + 13 two_markets_route + 17 five_turn_prototype + 13 deterministic_rivals [profiles differ identical state 2+ diffs Mira storage, determinism, capital via shared primitives, no-money with revaluation, behavioral warning prep vs farm, fingerprint across contexts, headlines derived visible T2+, same-rules, market isolation, no float, structured threat, no headline in state, exact-tie rng])
ruff check backend         → All checks passed
ruff format --check backend→ 27 files already formatted
pyright                    → 0 errors, 0 warnings
demo                       → normal 4545 vs drought 5714, trace supply 100+60-90→70 drought_reduced_availability
prototype hold 5           → hold,hold,hold,hold,hold prints 5× 6 MONTHS LATER + MIRA/DARAN headlines each turn, ends STRATEGIC SUMMARY with T1..5 Rivals lines and final rivals Mira 0/255/5/450 Daran 100/200/32/200 (diff 3/5 Mira granary×3 vs Daran farm×2, warning T3 Mira granary vs Daran granary but prep boost verified via scores)
prototype verbose          → adds RIVAL DETAILS per turn
cli parse                  → parse_choice("buy 20") -> buy_grain qty 20
actor primitives           → compute_farm_output/resolve_buy/resolve_storage_settlement/resolve_shipment share single source; turn.py and rivals.py both call same; costs 500/300/400/800 parity
```

Cache provenance fixed in YOLO (`~/.cache/uv/sdists-v9/.git` removed, `uv cache prune`), no `UV_CACHE_DIR` workaround needed. `.git/refs` provenance cleared for branch creation.

### Decisions relevant to future work

- `uv` + Python 3.12, `ruff` (line-length 100, py312) + `pyright` strict
- Beta Acid layout deferred to Section 10; engine stays import-clean
- High autonomy within Section; `/plan` before Section, approve once; stop at gate and report
- Coverage tracked not gating until Sections 3-4; heavy unit on engine/domain
- `backend/pyproject.toml` location; root `Makefile` wrappers; `backend/uv.lock` tracked
- Section 2: `pydantic` for validated integer types; JSON canonical encoding for RNG; capacities single-source
- Section 3: `TURN_ORDER` explicit, drought reduces yield not price, buy clamped, integer price via basis points
- Section 4: exact wealth decomposition at old vs new price, immutable tuples for causal DAG, allowed roots world/command, story drivers as causal paths ranked by exact wealth-bps, filtered zero stories, RNG ownership validated, concise/verbose CLI
- Section 5: `market` stays Home alias + `river_market` + `route:RouteState`; `transport_cost_per_unit` in milliunits (800) comparable to price 5000; `TURN_ORDER` extended with home_supply/river_supply/home_price/river_price/route_settlement; river supply stable for divergence; `secure_route`/`ship_grain` with capacity/inventory/cash clamping; wealth with ship `purchase+harvest+ship+price+cash` exact; drivers include trade arbitrage at resolved prices; optional staleness deferred; regression: resolved Home price flips arbitrage
- Section 6: Home supply signal `signal_next = max(0, signal+farm_output-demand)`; River stable; `FiveTurnGame` session-owned `state+history`, `TURN_SPECS` 5 truthful signals, start Home 100/90/5000 River 80/130/5200 storage200, determinism choices-based
- Section 7: Session-owned rivals via `actor.py` shared primitives (no duplicated economy), two-phase timing (choose pre→player resolve→settle rivals buy@pre/ship@resolvedRiver/valuation@resolvedHome), integer/bps scoring `expected×pref×capital×risk×exposure` with threat boost only on `next_world_known==drought` (T3 warning, not signal parsing), `RivalProfile` (Mira 4500/15000/13000/14500 farm-averse, Daran 16000/7000 farm-hungry) vs `RivalState` (1200/25/5/250 vs 1400/15/12/150) proven via identical-state tests, `RivalTurnResult` history 5×(Mira,Daran) with `wealth=cash+qty+price` revaluation, headlines derived from outcome, isolation (player supply unchanged), deterministic exact-tie `rng_for`

### Intentionally missing (do not build early)

Pressure arc (Section 8), balance harness (Section 9), FastAPI/GameView/revision (Section 10), React UI (Section 11) etc. No DB/SQLAlchemy, LLMs, route congestion, contested supply, generic rival framework.

### Follow-up obligations

Section 7 follow-ups resolved: shared primitives prevent divergence, two-phase timing respects buy/ship valuation, bps integer scoring with exact ties, structured threat not prose, profile vs state personality proven, full history with revaluation, behavioral not scripted headline tests, market isolation verified.

### Next milestone

**Section 8 — Pressure-Driven Event Arc** — replace hard-coded warning with small coherent pressure system (`normal→early dry→worsening→drought→aftermath`) keeping impact systemic via production/supply/price, not price hack, deterministic and inspectable.

