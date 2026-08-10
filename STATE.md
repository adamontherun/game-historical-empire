# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 5 — COMPLETE (2026-08-09)

**Two markets + River Route:** Home Valley (`market` alias) + River Town (`river_market`) with independent supply/demand → different prices from same grain, one River Route (`route: RouteState` with `transport_cost_per_unit: PriceMilliunits=800, capacity=20, reliability_bps=9000, established, delay_turns, event_exposure`), commands `secure_route` (cost 400 to establish) and `ship_grain` (quantity, clamped by `min(requested, capacity, inventory, affordable_by_transport)`), deterministic arbitrage — transport cost can erase apparent gap, capacity constrains, profit emerges from market conditions not script, Home-only turns still valid, `TURN_ORDER` extended, exact wealth with ship: `cash_effect + purchase+harvest+ship + price == wealth_delta`.

### What exists

```
backend/
  app/
    __init__.py
    domain/
      __init__.py            # re-exports CausalEdge/OutcomeDriver + types+RouteState
      types.py               # Money/... + GameState(player, market:Home, river_market, route:RouteState)+RouteState+PlayerCommand(secure_route/ship_grain) (frozen, ge=0)
      trace.py               # CausalNode(parent_ids:tuple)/CausalTrace(nodes:tuple, edges)/DomainEffect/OutcomeDriver/PlayerOutcome(drivers:tuple, top_drivers computed)/TurnResolution (frozen, validators: unique ids, parents before children, allowed roots world/command, farm_capacity/storage_capacity/route_* only when delta==0, delta==after-before, + river/route/trade kinds)
    engine/
      __init__.py            # re-exports RNG + rounding + resolve_turn/TURN_ORDER
      rng.py                 # derive_seed/make_rng/rng_for — JSON canonical -> blake2b
      rounding.py            # mul_basis_points/apply_basis_points/div_round_half_up/clamp_non_negative
      turn.py                # resolve_turn — command->production->home_supply->river_supply->home_price->river_price->settlement->route_settlement->valuation, two prices via _target_price/_bounded_price, river_supply stable, drought→farm_output→home_supply→home_price only, exact valuation with ship (_value: qty*price//1000), wealth nodes (purchase_quantity_value/harvest_quantity_value/ship_quantity_value/quantity_value_effect/price_value_effect/cash_effect/wealth, route nodes shipment/trade_revenue/transport_cost), story drivers (command_cost [split trade_cash], purchase_quantity, harvest_quantity, trade_arbitrage [net ship_quantity+revenue-cost], price_revaluation) filtered & ranked by exact wealth-bps, RNG validated (turn + route substreams), storage_capacity + route_capacity stable nodes, inventory parents (farm_output, storage_capacity, inventory_after_buy)
      demo.py                # CLI demo: before (HOME/RIVER/ROUTE)/command/world/WHY? (≤3 story drivers including trade_arbitrage) + after + contrast; --verbose adds FULL CAUSAL TRACE + DOMAIN EFFECTS + EDGES; --established flag for ship demo
  tests/
    test_sanity.py
    test_engine_purity.py
    test_core_types.py
    test_determinism.py
    test_rounding.py
    test_turn_kernel.py      # AC #1,3,4,5,6 + blocker 2 + TURN_ORDER->home_supply->river_supply->home_price->river_price->route_settlement->valuation + tuple parents
    test_invariants.py       # monotonic price, no negatives, positive price
    test_causal_trace.py     # exact wealth decomposition, immutable tuples, DAG allowed roots, wealth graph parents, driver determinism & wealth-bps, story paths filtered, RNG mismatch, storage-capped
    test_explanation.py      # drought→wealth structural chain exact, story drivers cover chain, concise≤3 & full trace, normal vs drought
    test_two_markets_route.py # Section 5 AC1-6: different prices, transport cost erases profit, capacity caps, emergent arbitrage, home-only, determinism, secure_route/ship blocked, wealth exact with ship, TURN_ORDER
  pyproject.toml             # uv project: pytest + ruff + pyright (strict) + pydantic>=2.7
  uv.lock
  .venv/
Makefile
.gitignore
.python-version              # 3.12 (root only)
AGENTS.md / backend/AGENTS.md / frontend/AGENTS.md
DECISIONS.md (001-009)
BUILD_SPEC.md Status: Sections 1-5 COMPLETE
docs/plans/
  2026-08-09-section-1-walking-skeleton.md
  2026-08-09-section-2-core-types.md
  2026-08-09-section-3-grain-market-kernel.md
  2026-08-09-section-4-causal-explanation.md  # exact valuation, tuples, story drivers
  2026-08-09-section-5-two-markets-route.md  # two markets + route, emergent arbitrage
frontend/                    # placeholder for Section 11
docs/
```

### Boundaries

- `backend/app/engine` and `backend/app/domain` are pure: no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk`. Enforced by AST rglob test. `pydantic` allowed for validated canonical types. `engine/turn.py` imports only `domain` + `rng`/`rounding`.
- Canonical state is frozen with immutable tuples: `parent_ids: tuple[str,...]`, `nodes: tuple[CausalNode,...]`, `drivers: tuple[OutcomeDriver,...]`, `causal_node_ids: tuple[str,...]` — no mutable lists inside frozen models, DAG is authoritative.
- Home market kept as `market` alias for backward compat; `river_market: MarketState` defaults `supply=80, demand=130, base=5200, price=5200`; river supply stable (not incremented by home harvest) so price divergence is emergent from `demand - supply` via same `_target_price/_bounded_price`. `RouteState` carries required properties `transport_cost_per_unit: PriceMilliunits=800, capacity=20, reliability_bps=9000, established=False, delay_turns=0, event_exposure="river_risk"`; `secure_route` costs 400 cash to set `established=True`; `ship_grain` is `min(requested, capacity, inventory_final_pre_ship, affordable_by_transport)` with reasons `limited_by_capacity/insufficient_inventory/insufficient_cash_for_transport/no_route_access`, revenue `delivered*river_price//1000`, cost `effective*transport_cost//1000`, delivered==effective unless reliability<9000.
- Wealth is structural, not post-hoc math: `value(qty,price)=qty*price//1000`, `wealth_before=cash_before+value(before)`, `purchase_quantity_value=value(after_buy,price_before)-value(before,price_before)`, `harvest_quantity_value=value(after_harvest,price_before)-value(after_buy,price_before)`, `ship_quantity_value=value(final,price_before)-value(after_harvest,price_before)`, `quantity_value_effect=purchase+harvest+ship`, `price_value_effect=value(final,price_after)-value(final,price_before)`, `cash_effect=cash_after-cash_before` (includes `secure_route` cost and `ship_revenue - ship_cost`), `wealth_delta=cash+purchase+harvest+ship+price` exactly, with nodes `purchase_quantity_value` parents `(command,inventory_after_buy)` (no price), `harvest_quantity_value` parents `(farm_output,storage_capacity,inventory)` (no price), `ship_quantity_value` parents `(shipment,inventory)` (no price), `quantity_value_effect` parents `(purchase,harvest[,ship])`, `price_value_effect` parents `(inventory,price)` alone carries changed-price, `wealth` parents `(cash_effect,quantity_value_effect,price_value_effect)`, route nodes `shipment` parents `(command,route_capacity,inventory)` etc.
- Story drivers are exact partitions: candidates `command_cost` (now `cash_effect - trade_cash`), `purchase_quantity`, `harvest_quantity`, `trade_arbitrage` (`ship_quantity_value + trade_cash` net), `price_revaluation` filtered where `impact_money==0`, ranked by `impact_bps=abs(impact_money)*10000//max(wealth_before,1)` desc then `id` asc, `≤3` returned. No double-count, sum of non-zero drivers equals subset of `wealth_delta` but exact decomposition holds via effects; `quantity_value_effect` = `purchase+harvest+ship`.
- Validator: unique ids, parents before children, no cycles, allowed roots `world`/`command` regardless of delta, `farm_capacity`/`storage_capacity`/`route_*` empty only when `delta==0`, river nodes follow same, all valuation nodes require parents, `delta==after-before` enforced, `edges` derived.
- Deterministic RNG: `rng_context` validated `== state.to_turn_context()` else `ValueError`; `derive_seed` via JSON array + blake2b, no global random/hash, price remains deterministic; route substream `rng_for(..., "route","river_route",0)` consumed.
- TURN_ORDER now `"command -> production -> home_supply -> river_supply -> home_price -> river_price -> settlement -> route_settlement -> valuation"` — explicit and tested.
- `backend/pyproject.toml` single project, no `fastapi`/`sqlalchemy` until Section 10. Ruff/pyright scoped to `backend`.

### Normal verification

```bash
uv sync --project backend
make test              # = uv run --project backend pytest -v  (76 passed)
make lint              # = ruff check backend  (All checks passed)
make type              # = pyright  (0 errors)
make format-check      # = ruff format --check backend  (21 already formatted)
make format            # actually formats backend/
```

### Last known green

```
uv sync --project backend  → Resolved 15 packages, 0 errors
pytest -v                  → 76 passed (8 core + 7 rounding + 11 determinism + 2 purity/sanity + 15 kernel + 7 invariants + 12 causal_trace + 4 explanation + 10 two_markets_route)
ruff check backend         → All checks passed
ruff format --check backend→ 21 files already formatted
pyright                    → 0 errors, 0 warnings
demo                       → uv run --project backend python backend/app/engine/demo.py --world drought --command hold  prints BEFORE (HOME/RIVER/ROUTE) /COMMAND/WORLD/PLAYER OUTCOME/WHY? (harvest_quantity + price_revaluation)/AFTER (HOME 4000, RIVER 6240 diverging); ship_grain --established shows trade_arbitrage driver
demo verbose               → same --verbose adds FULL CAUSAL TRACE (world→farm_output→home_supply→river_supply→home_price→river_price→shipment→quantity→price revaluation→wealth, route nodes explicit) + DOMAIN EFFECTS (purchase, harvest, ship, quantity, price, cash, wealth, shipment, trade_revenue, transport_cost) + EDGES
demo secure_route          → uv run --project backend python backend/app/engine/demo.py --command secure_route shows cash -400 and route established True
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
- Section 5: `market` stays Home alias + `river_market` + `route:RouteState`; `transport_cost_per_unit` in milliunits (800) comparable to price 5000; `TURN_ORDER` extended with `home_supply/river_supply/home_price/river_price/route_settlement`; river supply stable for divergence; `secure_route`/`ship_grain` with capacity/inventory/cash clamping; wealth with ship `purchase+harvest+ship+price+cash` exact; drivers include `trade_arbitrage` net; optional staleness deferred

### Intentionally missing (do not build early)

Headless 5-turn prototype (Section 6), rivals Mira/Daran (Section 7), pressure arc (Section 8), balance harness (Section 9), etc. No FastAPI routes, DB/SQLAlchemy, React UI, content framework, LLMs.

### Follow-up obligations

Must resolve before **Section 6** (multi-turn prototype):
- Define `market.supply` semantics: stock vs per-turn flow vs aggregate signal. Current `next_supply = supply + farm_output` is persistent stock while `farm_output` also enters player `inventory` and `buy_grain` does not reduce regional supply — coherent for one turn but will monotonically accumulate over repeated turns. Design stock/flow accounting before headless balance harness (tuning 5000/2000 is fine to defer to that harness). Same for `river_supply` (stable in Section 5, will need pressure-driven updates in Section 8).

Section 5 follow-ups are now resolved: two markets with different prices, transport cost erases arbitrage, capacity constrains, emergent profit, home-only valid, deterministic, trade access via secure_route, exact wealth with ship.

### Next milestone

**Section 6 — Five-Turn Headless Prototype** — grain only, Home Valley + River Town + River Route, farm/granary/trade/cash, one major action per turn, deterministic world pressures, outcome reveal text, 5 decisions, no DB/LLM.
