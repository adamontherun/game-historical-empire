# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 6 — COMPLETE (2026-08-09)

**Five-turn headless prototype:** Deterministic 5-turn terminal game (`FiveTurnGame` + `TURN_SPECS` 5-element authored arc) on top of Section 5 kernel with corrected supply semantics (`stock_next = max(0, stock + farm_output - demand)` for Home), grain only, Home Valley (market alias, now stock 100→110→120 surplus weak) + River Town (river_market 80 stable, price 5200→6240→6825 shortage) + River Route (800/20/10000), commands hold/expand_farm/build_granary/buy_grain/secure_route/ship_grain (one per turn, exactly 5), truthful signals, outcome reveal with ≤3 drivers, concise strategic summary. Deterministic same seed+choices→same, three corrected distinct policies diverge >10% wealth, drought rewards preparation (prepared T4 +130 vs farm-heavy -9 on same seed), no universal best claimed, no DB/LLM/rivals.

### What exists

```
backend/
  app/
    __init__.py
    domain/
      __init__.py            # re-exports CausalEdge/OutcomeDriver + types+RouteState
      types.py               # Money/... + GameState(player, market:Home, river_market, route:RouteState)+RouteState+PlayerCommand(secure_route/ship_grain) (frozen, ge=0)
      trace.py               # CausalNode(parent_ids:tuple)/CausalTrace(nodes:tuple, edges)/DomainEffect/OutcomeDriver/PlayerOutcome(drivers:tuple, top_drivers computed)/TurnResolution (frozen, validators)
    engine/
      __init__.py            # re-exports RNG + rounding + resolve_turn/TURN_ORDER
      rng.py                 # derive_seed/make_rng/rng_for — JSON canonical -> blake2b
      rounding.py            # mul_basis_points/apply_basis_points/div_round_half_up/clamp_non_negative
      turn.py                # resolve_turn — Section 6 supply fix: Home stock_next = max(0, stock+farm_output-demand) (drained by consumption, price on stock_next), River stable, drought→farm_output→Home stock→price chain truthful, exact wealth with ship
      prototype.py           # FiveTurnGame(state, history, turn_limit=5, TURN_SPECS[5]{world,signal,title truthful}, default_start_state(seed, version) Home 100/90/5000 River 80/130/5200 route 800/20/10000 storage 200, submit()->resolve_turn, run(choices)->summary, StrategicSummary{final_state, history, final_wealth, initial_wealth, wealth_delta_total, cash_low, peak_inventory, is_complete, format()}
      cli.py                 # Thin CLI: interactive input loop + --choices non-interactive (parse_choice "hold/buy 20/ship 10/1-6"), per-turn display turn/signal/player cash/grain/farm/storage HOME/RIVER pulse ROUTE choices, after-commit 6 MONTHS LATER wealth/inventory/price WHY? drivers, --verbose full trace, ends with STRATEGIC SUMMARY
      demo.py                # Single-turn demo still works (now Home supply 100->80/40 with drain, price 5000->6000 under both worlds due to cap, drought still lower supply 40 vs 80)
  tests/
    test_sanity.py
    test_engine_purity.py
    test_core_types.py
    test_determinism.py
    test_rounding.py
    test_turn_kernel.py      # AC #1,3,4,5,6 + blocker 2 + TURN_ORDER->home_supply->river_supply->home_price->river_price->route_settlement->valuation
    test_invariants.py       # monotonic price, no negatives, positive price
    test_causal_trace.py     # exact wealth decomposition, immutable tuples, DAG, drivers, wealth-bps
    test_explanation.py      # drought→wealth structural chain exact, story drivers cover chain, concise≤3 & full trace, normal vs drought (now checks price node >= not price_value_effect due to inventory diff)
    test_two_markets_route.py # Section 5 AC1-6
    test_five_turn_prototype.py # Section 6 AC1-7: exactly 5 decisions, terminal completable non-interactive, determinism same seed+choices, different choices diverge, supply semantics stock-drained (100+100-90=110 normal 70 drought), three strategies diverge >10% (farm 548 vs storage 1746 vs trade 1510 vs hold 1909 on demo-seed-001), drought rewards preparation (storage T4 +130 vs farm -9), each turn chain world->farm_output->supply->price, summary contains STRATEGIC SUMMARY, CLI parse, signals truthful, titles, available commands
  pyproject.toml             # uv project: pytest + ruff + pyright (strict) + pydantic>=2.7
  uv.lock
  .venv/
Makefile
.gitignore
.python-version              # 3.12 (root only)
AGENTS.md / backend/AGENTS.md / frontend/AGENTS.md
DECISIONS.md (001-010)
BUILD_SPEC.md Status: Sections 1-6 COMPLETE
docs/plans/
  2026-08-09-section-1-walking-skeleton.md
  2026-08-09-section-2-core-types.md
  2026-08-09-section-3-grain-market-kernel.md
  2026-08-09-section-4-causal-explanation.md  # exact valuation, tuples, story drivers
  2026-08-09-section-5-two-markets-route.md  # two markets + route, emergent arbitrage
  2026-08-09-section-6-five-turn-prototype.md  # Rev2: stock-drained supply, truthful signals, fixed strategies, no seed-divergence, no cross-seed dominance
frontend/                    # placeholder for Section 11
docs/
```

### Boundaries

- `backend/app/engine` and `backend/app/domain` are pure: no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk`. Enforced by AST rglob test on engine/domain only (cli.py at top-level app is not checked, but also imports only stdlib+domain+engine). `pydantic` allowed for validated canonical types. `engine/turn.py` imports only `domain` + `rng`/`rounding`; `engine/prototype.py` imports only `domain` + `turn`.
- Canonical state is frozen with immutable tuples: `parent_ids: tuple[str,...]`, `nodes: tuple[CausalNode,...]`, `drivers: tuple[OutcomeDriver,...]`, `causal_node_ids: tuple[str,...]` — no mutable lists inside frozen models, DAG is authoritative.
- Home market is `market` alias with supply as **stock** drained by demand: `next_stock = max(0, stock + farm_output - demand)`; price set on `next_stock` (post-consumption) via `_target_price` guard, so surplus (farm > demand) raises stock and depresses price, drought (60 vs 100) drains stock and raises price. River supply stable (80) so price divergence remains emergent. `RouteState` unchanged (800/20/10000, established, delay 0).
- Five-turn orchestration is pure: `FiveTurnGame` holds `GameState` + `history: tuple[TurnResolution,5]` and calls `resolve_turn` exactly once per submit with `rng_context = state.to_turn_context()` validated inside turn. No DB, no copy of kernel logic, history not stored inside GameState (frozen). `TURN_SPECS` is hardcoded 5-element list: T1 normal "The growing settlement keeps food demand high.", T2 normal "Repeated harvests have left grain abundant and prices weak.", T3 normal "Dry weather suggests the next harvest may be threatened.", T4 drought "Drought cuts farm output — regional supply tightens.", T5 normal "Markets adjust to the drought's aftermath." — all truthful about mechanics (T2 surplus emergent from stock accumulation, not per-turn harvest difference; T1 demand high via starting demand 90).
- Wealth remains exact: `_value(qty,price)=qty*price//1000`, `wealth_before=cash+value`, `quantity_value_effect=purchase+harvest+ship`, `price_value_effect=value(final,price_after)-value(final,price_before)`, `cash_effect=cash_after-cash_before`, `wealth_delta=cash+quantity+price`. Drivers are exact partitions ranked by `impact_bps=abs(impact)*10000//max(wealth_before,1)` desc then id, ≤3, filtered zero.
- Determinism is choices-based: same `run_seed`+`version`+`choices[5]` → same history/summary; different choices diverge; different seeds with same choices may be identical until a seeded mechanic exists (Section 8) — Section 6 does not assert seed divergence or cross-seed "no dominant strategy".
- `backend/pyproject.toml` single project, no `fastapi`/`sqlalchemy` until Section 10. Ruff/pyright scoped to `backend`.

### Normal verification

```bash
uv sync --project backend
make test              # = uv run --project backend pytest -v  (92 passed: 79 prior + 13 new)
make lint              # = ruff check backend  (All checks passed)
make type              # = pyright  (0 errors)
make format-check      # = ruff format --check backend  (24 already formatted)
```

### Last known green

```
uv sync --project backend  → Resolved 15 packages, 0 errors
pytest -v                  → 92 passed (8 core + 7 rounding + 11 determinism + 2 purity/sanity + 15 kernel + 7 invariants + 12 causal_trace + 4 explanation + 13 two_markets_route + 13 five_turn_prototype [exactly5, noninteractive, determinism same+diff, supply stock-drained 110/70, three strategies diverge >10% farm 548 vs storage 1746 vs trade 1510, drought rewards prep 130 vs -9, each turn chain, summary STRATEGIC SUMMARY, run requires 5, CLI parse, signals truthful, titles, available commands])
ruff check backend         → All checks passed
ruff format --check backend→ 24 files already formatted
pyright                    → 0 errors, 0 warnings
demo                       → uv run --project backend python backend/app/engine/demo.py --world drought --command hold  now Home supply 100->40 (drought, 100+60-120=40) vs normal 100->80, price 5000->6000 both capped, wealth +380 vs +500, trace supply node 100+60-120->40 reason drought_reduced_stock
prototype hold 5           → uv run --project backend python backend/app/cli.py --seed demo-seed-001 --choices hold,hold,hold,hold,hold  prints INITIAL/5× TURN (1 A Growing Settlement signal high demand, 2 Surplus abundant weak, 3 Warning dry, 4 Drought cuts output, 5 Aftermath) with 6 MONTHS LATER wealth/inventory/price WHY? drivers, ends STRATEGIC SUMMARY 5 turns wealth 1100->1909 delta +809 (hold) vs farm 548 vs storage 1746 vs trade 1510 spreads >10%
prototype verbose          → same --verbose adds FULL CAUSAL TRACE (world->farm_output->supply(100+100-90->110)->price_pressure->target->price->shipment->cash/inventory->quantity->price revaluation->wealth) + DOMAIN EFFECTS
cli parse                  → parse_choice("buy 20") -> buy_grain qty 20, parse_choices_arg("hold,buy 20,hold,ship 10,hold") len 5
```

Cache provenance fixed in YOLO (`~/.cache/uv/sdists-v9/.git` removed, `uv cache prune`), no `UV_CACHE_DIR` workaround needed. `.git/refs` provenance cleared for branch creation; `.git/objects` provenance remains but does not block Git (refs are authoritative).

### Decisions relevant to future work

- `uv` + Python 3.12, `ruff` (line-length 100, py312) + `pyright` strict
- Beta Acid layout deferred to Section 10; engine stays import-clean
- High autonomy within Section; `/plan` before Section, approve once; stop at gate and report
- Coverage tracked not gating until Sections 3-4; heavy unit on engine/domain
- `backend/pyproject.toml` location; root `Makefile` wrappers; `backend/uv.lock` tracked
- Section 2: `pydantic` for validated integer types; JSON canonical encoding for RNG; capacities single-source
- Section 3: `TURN_ORDER` explicit, drought reduces yield not price, buy clamped, integer price via basis points
- Section 4: exact wealth decomposition at old vs new price, immutable tuples for causal DAG, allowed roots world/command, story drivers as causal paths ranked by exact wealth-bps, filtered zero stories, RNG ownership validated, concise/verbose CLI
- Section 5: `market` stays Home alias + `river_market` + `route:RouteState`; `transport_cost_per_unit` in milliunits (800) comparable to price 5000; `TURN_ORDER` extended with `home_supply/river_supply/home_price/river_price/route_settlement`; river supply stable for divergence; `secure_route`/`ship_grain` with capacity/inventory/cash clamping; wealth with ship `purchase+harvest+ship+price+cash` exact; drivers include `trade_arbitrage` net with `arbitrage_margin` at resolved prices (reliability `delivered = effective * reliability_bps //10000`, default 10000, `delay_turns` constrained 0, `cash_after_trade`/`inventory_after_trade` nodes, `price_value_effect` parents `inventory_after_trade+price`); optional staleness deferred; regression: resolved Home price correctly flips arbitrage (5.00→6.00 vs 6.24 gives -6 not +4)
- Section 6: Home supply is **stock drained by demand** `next = max(0, stock + farm_output - demand)` (price on next stock, surplus raises stock and depresses price, drought drains and raises price); River supply stable; `FiveTurnGame` owns `GameState`+`history` outside canonical state, calls `resolve_turn` once per turn with validated `rng_context`, enforces exactly 5 submissions, `TURN_SPECS` hardcoded 5 truthful signals (T1 high demand, T2 abundant weak surplus emergent, T3 warning, T4 drought, T5 aftermath); start state Home 100/90/5000 River 80/130/5200 storage 200 cash 1000 grain 20 farm 10 route 800/20/10000; CLI `backend/app/cli.py` thin (interactive + --choices non-interactive, shows turn/signal/player cash/grain/farm/storage HOME/RIVER pulse ROUTE choices, after-commit 6 MONTHS LATER wealth/inventory/price WHY? ≤3 drivers, ends STRATEGIC SUMMARY); determinism is choices-based, no seed-divergence or cross-seed dominance asserted; three corrected policies (farm expand×2+hold×3, storage build+buy20+hold×3, trade secure+build+hold+ship10×2) diverge >10% and drought rewards prep

### Intentionally missing (do not build early)

Rivals Mira/Daran (Section 7), pressure arc (Section 8), balance harness (Section 9), etc. No FastAPI routes, DB/SQLAlchemy, React UI, content framework, LLMs.

### Follow-up obligations

Section 6 follow-ups resolved: supply semantics defined as stock drained by demand (bounded, price on stock, surplus truthful, no monotonic accumulation), signals truthful, strategies legal and distinct, determinism via choices.

### Next milestone

**Section 7 — Deterministic Rivals** — Mira (storage/trade/flexible early) and Daran (farmland scale, aggressive, vulnerable) via deterministic scoring `opportunity score = expected return × preference × capital × risk × exposure`, each turn at least one rival headline, legible behavior.

