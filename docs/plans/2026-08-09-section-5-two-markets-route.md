# Section 5 — Two Markets and One Trade Route — Plan

**Date:** 2026-08-09
**Branch:** `section/5-two-markets-route` (from `origin/main` at `600bb7a`)
**Spec Authority:** `BUILD_SPEC.md` Section 5 (Status: NOT STARTED) + global §§10–15 + `DECISIONS.md` 001–009 + `STATE.md` §4 + `STATE.md` follow-up "market.supply semantics"
**Related:** `backend/app/domain/types.py`, `backend/app/domain/trace.py`, `backend/app/engine/turn.py`, `backend/app/engine/rng.py`, `backend/app/engine/rounding.py`, `backend/app/engine/demo.py`

---

## Goal

Add spatial economics without a geographic map: two market nodes (Home Valley, River Town) with independently resolved supplies/prices from the same grain good, one River Route with transport cost / carrying capacity / reliability / settlement delay, and a player command that creates trade access. The turn kernel must still resolve deterministically, keep all canonical state integer, emit a structural causal trace that explains price divergence and transport economics, and allow the player to remain in Home Valley.

---

## Success Criteria (maps to Section 5 AC 1–6 + global rules)

1. **Different prices for the same good.** Home Valley and River Town can hold different `current_price` values after the same turn, derived from distinct supply/demand inputs through the existing integer-safe `imbalance → normalized_imbalance → pressure → target → bounded movement` market model (not a scripted offset). Tested by constructing a `GameState` where `home_market.supply/demand != river_market.supply/demand` and asserting `next_state.home_market.current_price != next_state.river_market.current_price` for at least one deterministic seed/world. Home price still travels through `farm_output → supply → price_pressure → price` per §3 invariant.

2. **Transport cost can erase arbitrage.** Even when `river_price > home_price`, `profit = qty * river_price // 1000 - qty * home_price // 1000 - qty * transport_cost_per_unit` can be ≤0. The free price difference is not the decision — net after `transport_cost_per_unit` is. Tested with transport cost intentionally set to exceed the price gap.

3. **Capacity constrains volume.** `ship_grain` with `quantity` larger than `route.capacity` (or larger than `inventory` or `affordable after cost`) is clamped or rejected by one explicit rule, the trace records the limiting reason (`limited_by_capacity` / `insufficient_inventory` / `insufficient_cash`), and final inventory/cash respect the capped quantity. Same clamping philosophy as `buy_grain` in Section 3.

4. **Emergent arbitrage, not scripted reward.** By varying market conditions (e.g. Home surplus `supply > demand` vs River shortage `demand >> supply`, or drought lowering Home supply while River demand stays high), a profitable ship opportunity appears without any `if arbitrage_flag: bonus` script. The profit is a consequence of two independent price resolves plus transport arithmetic. Demonstrated in a test that sweeps two supply/demand configurations with the same route/costs and shows opposite profitability.

5. **Home-only turn remains valid.** Every existing command (`hold`, `expand_farm`, `build_granary`, `buy_grain`) still completes a turn correctly without touching River Town or the route, whether `route.established` is false or true. No required River field. Command `hold` with `trade_access == False` yields identical Home-side effects to Section 4.

6. **Deterministic.** Same `state + command + world + seed` → same `next_state + trace + effects + outcome`. Uses only `derive_seed` / `rng_for` substreams for reliability jitter (if any), never global `random` or `hash()`. New RNG namespaces are `trade` and `route` with entity ids `river_route`.

7. **Housekeeping (global gates still pass):** `engine` + `domain` remain pure (no `fastapi`/`sqlalchemy`/`httpx`), integer canonical state, `ruff` clean, `pyright` strict passes, existing Section 3–4 ACs still hold for the Home market chain, `demo.py` can illustrate both markets.

---

## Context And Current Facts

- `main` at `600bb7a` (squashed through Section 4). `STATE.md` marks Sections 1–4 COMPLETE - 66 tests green (8 core + 7 rounding + 11 determinism + 2 purity/sanity + 15 kernel + 7 invariants + 12 causal_trace + 4 explanation), `ruff` + `pyright` strict pass, `demo` prints concise `WHY?` (≤3 story drivers) + `--verbose` full DAG.
- **Current domain (`backend/app/domain/types.py:1`):** `Money/Quantity/PriceMilliunits/BasisPoints` via `Annotated[int, Field(ge=0, strict=True)]` (BasisPoints unrestricted), `InventoryState{grain}`, `OperationState{id,kind,capacity,level}`, `PlayerState{cash, inventory, farm_capacity, storage_capacity}`, `MarketState{supply,demand,base_price,current_price,responsiveness=5000,max_movement_bps=2000}`, `TurnContext{turn,run_seed,ruleset_version}`, `WorldCondition = Literal["normal","drought"]`, `PlayerCommand{type: expand_farm|build_granary|buy_grain|hold, quantity?}`, `GameState{turn,run_seed,ruleset_version,player,market}` frozen, `to_turn_context()`. No River Town, no route.
- **Current engine (`backend/app/engine/turn.py:1`):** `resolve_turn(state, command, world, rng_context)` with explicit `TURN_ORDER = "command -> production -> supply -> price -> settlement -> valuation"` and strict chain `world/farm_capacity -> farm_output -> supply -> price_pressure -> target_price -> price -> inventory( capped by storage_capacity) -> purchase/harvest/quantity_value -> price_value -> wealth`. Integer-safe market math in `rounding.py`. Drought reduces `farm_output` (40% bps reduction), never directly touches price. Buy clamped via `min(requested, affordable, space)`. Wealth decomposition exact (`value(qty,price)=qty*price//1000`, `purchase+harvest+price+cash == wealth_delta`). RNG ownership validated (`rng_context == state.to_turn_context()`), `rng_for(..., "turn","price_jitter",0).random()` consumed without driving price.
- **Current trace (`backend/app/domain/trace.py:1`):** `CausalNode{id,label,kind,before,after,delta,reason_code,parent_ids: tuple}`, `CausalTrace{nodes: tuple, edges: derived, DAG validator}` (allowed empty roots `world`/`command`, `farm_capacity`/`storage_capacity` only when `delta==0`, valuation nodes require parents, parents before children, unique ids, `delta==after-before` when all present), `DomainEffect{metric,before,after,delta,reason_code}`, `OutcomeDriver{id,label,kind,impact_money,impact_bps,reason_code,causal_node_ids: tuple}`, `PlayerOutcome{wealth_delta,inventory_delta,price_delta,drivers: tuple max 3, top_drivers computed}`.
- **Section 4 follow-up resolved; Section 6 follow-up still open:** `STATE.md` follow-up "market.supply semantics: stock vs per-turn flow vs aggregate signal. Current `next_supply = supply + farm_output` is persistent stock while farm_output also enters player inventory and buy_grain does not reduce regional supply — coherent for one turn but will monotonically accumulate over repeated turns. Design stock/flow accounting before headless balance harness." Section 5 should not silently redesign multi-turn stock semantics. For Section 5 the minimal coherent choice is: keep per-market persistent stock (`supply += farm_output`) for both markets, do not make buy/ship reduce regional supply yet. Document the carry-forward accumulation as known Section 6 debt and keep `STATE.md` follow-up open. Do not invent consumption/spoilage to "fix" stocks now.
- **Tooling:** `backend/pyproject.toml` single project (`pydantic>=2.7`, `pytest>=9`, `ruff`, `pyright strict python 3.12`), Makefile wrappers `make test/lint/type/format-check`, `uv` sync.
- **Section 5 spec (BUILD_SPEC.md:921):** Two markets with given characters, one route with cost/capacity/reliability/delay/event exposure, player command creates trade access, no map placement, optional one-turn staleness is **explicitly skippable** if it expands scope.

---

## Constraints And Non-goals

**Must satisfy:**
- Pure `backend/app/engine` + `backend/app/domain` — no `fastapi`/`sqlalchemy`/`httpx`/`asyncpg`/`openai`/`clerk`.
- Integer-only canonical state; deterministic via `derive_seed`/`rng_for` (BLAKE2b JSON array), no `random` global or `hash()`. New substreams use existing derivation.
- Deterministic rounding via `rounding.py`; no floats in canonical path.
- Keep `frontend/` untouched (Section 11), no DB/API/auth/deployment, no generic event DSL (Section 8), no rivals (Section 7).
- Existing Section 3–4 acceptances still pass: Home Valley chain remains `world -> farm_output -> supply -> price`, drought still reduces yield not price, wealth decomposition stays exact, trace DAG still validated, driver ranking still `(-impact_bps, id)`.

**Explicitly out of scope (BUILD_SPEC §5):**
- Geographic map, building placement, generic business schema registry, JSON content loader.
- Full 5-turn arc (Section 6), rival scoring (Section 7), pressure arc / event framework (Section 8), balance harness (Section 9), FastAPI boundary (Section 10+).
- Generic transport logistics beyond one route; spoilage, skill scarcity, credit, brands, network effects.
- Optional River Town staleness mechanic — **do not build** if it adds surface. This plan explicitly defers it (§KDR 10).

**Non-goals for this section:**
- No extra goods beyond grain; no extra markets beyond Home Valley + River Town; no extra trait: spoilage, seasonality, credit, brands, etc.
- No per-unit market inventory ownership split (player inventory remains single `grain` value; trade is a conversion/shipment valued at the other market's price, not a second physical silo).
- No persistence or API; `GameState` is still in-memory.

---

## Key Decisions

| # | Decision | Choice | Why | Alternative rejected |
|---|----------|--------|-----|----------------------|
| 1 | **State shape — additive, backward-compatible** | Keep `GameState.market` as **Home Valley alias** and add `river_market: MarketState` + `route: RouteState`. Backwards-compat: `market` stays the canonical Home field so existing `GameState(market=...)` construction keeps compiling; add `river_market` with sensible defaults and `route` with defaults. Internally, engine resolves `home_market` via `state.market` (Home) and `river_market` via `state.river_market`. New helper `_home_market(state)` is trivial accessor. Provide a `@model_validator` or `@computed_field` only if needed for alias clarity, but do not rename `market` yet — renaming would churn all Section 3–4 tests for no AC value. Document that `market` ≡ Home Valley until Section 6 renames it. | Smallest churn; all 66 existing tests keep passing after adding defaults. For Section 6 the rename to `home_market` can be done with alias. | Renaming `market` → `home_market` now rejected — forces mechanical test churn across ~10 files and risks drift before Section 6 needs it. Separate `Markets{home, river}` wrapper rejected — deeper nesting for one extra market. Keeping single market and overloading `supply`/`demand` as tuple rejected — hides divergence and breaks price chain traceability. |
| 2 | **RiverTown market characterisation via explicit MarketState fields** | `river_market: MarketState` defaults: `supply=80, demand=130, base_price=5200, current_price=5200, responsiveness=5000, max_movement_bps=2000` . Home defaults stay `supply=100, demand=120, base_price=5000, current_price=5000` as in demo/tests. This already yields different equilibrium prices under same `world` because `imbalance = demand - supply` differs. River also uses same `_target_price` / `_bounded_price` helpers, so divergence is emergent from supply/demand, not a scripted bonus. Drought still affects **Home Valley supply only** (Home farm output added to Home supply); River supply is not incremented by Home harvest. If drought globally reduces yields, Section 5 keeps it Home-local to preserve spec line "more exposed to local weather" vs River's demand-driven tightness. River supply left stable unless a Section 8 pressure later mutates it. | Satisfies "Home Valley relatively high grain supply after harvest, more exposed to local weather" vs "River Town growing population, stronger food demand, higher potential price during shortages". No new formula needed; reuses proven kernel. River supply deliberately not coupled to Home farm output so prices can diverge even when Home has surplus. | Adding a special `drought_factor` per market rejected — generalises too early. Adding consumption/demand shocks to both markets now rejected — belongs to Sections 6/8. Forcing River price = Home price + constant rejected — violates AC #1 emergent divergence and AC #4 "conditions rather than scripted reward". |
| 3 | **Route model — minimal concrete struct, four required properties + optional delay** | New type `RouteState` (frozen): `transport_cost_per_unit: Money = 800` (Money per grain, integer, ≥0), `capacity: Quantity = 20`, `reliability_bps: BasisPoints = 9000` (≥0 ≤10000), `established: bool = False`, `establish_cost: Money = 400` (sibling const in engine), optional `delay_turns: int = 0` (validated ≥0, kept 0 for Section 5), `event_exposure: str = "river_risk"` placeholder not yet wired to an event system (Section 8 will use it). Also `GameState.river_market` + `GameState.route`. Route lives in `domain/types.py`, not engine. | Directly maps spec line "transport cost, carrying capacity, reliability, optional travel or settlement delay if useful, event exposure" to typed fields. Defaults chosen so a 10-unit shipment Home 5000 → River 5200 minus transport 800 yields net +? Example: `river_value = qty * river_price //1000`, `home_value = qty * home_price //1000`, transport `qty * 800` (Money not milli, so `qty * cost` not `//1000`), profit can tip positive/negative by market gap and quantity, satisfying AC #2. Capacity 20 constrains 50-unit request to 20. `delay_turns=0` keeps settlement same-turn; non-zero would add inventory-in-transit state which expands scope — defer. | Simpler `route: bool` flag rejected — loses cost/capacity/reliability testability and violates spec properties. Separate `RouteCapacity`/`RouteCost` micro-types rejected — over-typed. Storing route globally not in GameState rejected — violates determinism/serialisability. Adding full logistics graph with nodes/edges rejected — map creep. |
| 4 | **Commands — extend PlayerCommand discriminated union minimally** | `PlayerCommand` gains two new types: `secure_route` (no quantity) and `ship_grain` (`quantity: Quantity | None`). Keep existing `expand_farm`, `build_granary`, `buy_grain`, `hold`. `secure_route`: if `route.established == False` and `cash >= establish_cost` → `cash -= establish_cost`, `route.established = True`; else insufficient_cash reason, no mutation other than trace. `ship_grain`: requires `route.established == True`; `requested = quantity ?? 10`; `effective = min(requested, route.capacity, player.inventory.grain, affordable_by_transport_cost?)` plus reliability stochastic loss applied **after** capacity clamp (expected delivered = effective * reliability_bps // 10000 but Section 5 may keep `reliability` as pure trace until Section 8 needs loss — see KDR 5). Selling: `revenue = delivered * river_market.current_price // 1000`; `cost = effective * route.transport_cost_per_unit` (Money per unit) ; profit to cash. Trace records `ship_grain` as quantity-value move at river price vs home value. Keep clamping philosophy identical to `buy_grain`. | Satisfies "Support a player command or operation that creates trade access" without inventing route-placement UI. `ship_grain` is the minimal arbitrage verb: it can be profitable only when River price gap exceeds transport cost and capacity allows volume. Reuses buy_grain clamp pattern so invariants/tests stay legible. | Adding generic `trade(qty, from_market, to_market)` with source/sink args rejected — implies N markets before spec needs it. Adding `establish_route` as OperationState kind rejected — OperationState is farm/granary-only today; widening it now would couple route to capacity-level system prematurely. Making trade access implicit (no command) rejected — violates spec operation requirement. |
| 5 | **Reliability implementation — deterministic but non-destructive for Section 5** | `reliability_bps` participates deterministically but **does not destroy inventory randomly in Section 5's happy-path assertion**. Instead: reserve a RNG substream `rng_for(seed, version, turn, "route", "river_route", 0).random()`; derive `loss_bps = 10_000 - reliability_bps` as maximum loss exposure; emit `reliability_loss` causal node and a `reliability_effect` domain effect that is **0 for capacity 9000+ until Section 8**. Loss materialises only if explicitly tested with `reliability_bps < 9000` or via throwaway `rng.random() < (1 - reliability)`. This keeps profits deterministic for AC #4 tests while proving the field is wired and consumed, and preserves the spec "reliability" without adding stochastic bankruptcy in the headless prototype. | Lets AC #2/3/4 be tested deterministically without flakiness; reserves the field for Section 8 pressure arc where event exposure will matter. Keeping RNG consumed ensures different reliability values don't accidentally produce identical RNG traces. | Full per-unit binomial reliability (flip per grain) rejected — over-complex and flaky for Section 5 AC tests. Ignoring reliability entirely rejected — spec lists it as required route property. Making reliability alter price directly rejected — violates "author cause" rule. |
| 6 | **Causal trace extension — Home and River price subgraphs under same trace** | Keep single `CausalTrace` with extended node ids: Home: `home_supply`, `home_price_pressure`, `home_target_price`, `home_price`; River counterparts `river_supply`, `river_price_pressure`, `river_target_price`, `river_price`; route nodes `route_capacity`, `route_cost`, `route_reliability`, `shipment`, `trade_profit`. For backward compat, keep legacy ids `supply`/`price` etc as **aliases to Home** (so existing tests checking `id=="supply"` still pass; emit `supply` as home alias alongside `home_supply` or emit both with same before/after). Wealth valuation nodes stay single: `trade_quantity_value` (revenue value) vs `transport_cost_effect` vs `home_quantity_value`. Add `trade` kind literal. Validator: new nodes require parents; `route_*` nodes may have empty parents only when `delta==0` and `!established`. Edges derived from `parent_ids`. | Preserves DAG validators and keeps existing kernel tests green while making River divergence inspectable. Single trace lets Section 6/7 outcome reveal show WHY price divergence drove profit. | Splitting into `home_trace`/`river_trace` rejected — fragments causality. New flat `effects` list without nodes rejected — violates "causal trace emitted structurally". Requiring two separate TurnResolutions rejected — doubles API surface before Section 10. |
| 7 | **Valuation & wealth decomposition with two markets** | Inventory spot value remains `value(qty, home_price)` for `wealth_before/after` baseline (Home valuation). Trade adds two new effects: `trade_revenue = delivered * river_price // 1000` as `trade_revenue_effect`, `transport_cost = effective * transport_cost_per_unit` (Money, not milli) as `transport_cost_effect`, net `trade_profit = trade_revenue - transport_cost - value_sold_at_home?` careful to keep sum exact. Simpler exact form: when `ship_grain effective` is sold/ removed from inventory, `quantity_value_effect` already accounts for inventory reduction at home price, and `trade_revenue_effect` credits cash at river price. So wealth delta stays exact: `cash_effect` includes `+trade_revenue - transport_cost`, `purchase_quantity_value`/`harvest_quantity_value` as before, `trade_quantity_value` is folded into `harvest/quantity` via inventory_final. Prove `wealth_delta == cash_effect + purchase + harvest + price_value_effect` still holds (trade revenue is inside `cash_effect`). No new wealth root. | Keeps Section 4 invariant `wealth_delta == cash + purchase + harvest + price` exactly — Section 4 tests already check this, so Section 5 must not break it. Trade profit is just a cash source whose trace shows route cost parents. | Introducing `wealth_river` or dual-wealth rejected — would double-count stored grain. Making trade revenue a separate wealth term outside cash_effect rejected — breaks Section 4 decomposition law. |
| 8 | **Turn order with two markets** | Extend `TURN_ORDER` string to `"command -> production -> home_supply -> river_supply -> home_price -> river_price -> settlement -> route_settlement -> valuation"`. In code, order is linear: (1) command (including secure_route/ship), (2) production (farm_output using post-command farm_capacity + world), (3) home supply (`supply + farm_output`), (4) river supply (unchanged or slightly perturbed), (5) home price (`_target_price`/`_bounded_price` on home supply/demand), (6) river price (same helpers on river supply/demand), (7) settlement (inventory capped by storage, inventory_after_buy etc), (8) route settlement (ship clamping, cash credit, inventory deduction), (9) valuation (exact split, price revaluation at home price per Section 4, plus trade effects). | Keeps "Author the cause, simulate consequences" and makes River price divergence observable in trace. Home chain matches Section 3 order so kernel tests stay valid. | Interleaving command after production rejected — would change Section 3 semantics. Resolving both prices in one loop with shared pressure rejected — obscures divergence. |
| 9 | **Optional staleness explicitly deferred** | Document "River Town market information stale by one turn until reliable trade access" as **not implemented** in Section 5. Its fields (`trade_access`, `last_seen_river_price`) would span two turns, bring snapshot diff and replay concerns, and expand the section. Defer to Section 8/11 with note in `DECISIONS.md` if needed. Tests will not check for staleness. | Spec says "Do not implement this optional mechanic if it expands the section substantially." It does, so skipping keeps scope minimal. | Implementing last-turn River price peek illusion rejected — needs GameState history or peek window. |
| 10 | **File layout** | Types: `domain/types.py` — add `RouteState`, extend `GameState` with `river_market: MarketState` + `route: RouteState`, extend `PlayerCommand.type` literal; add `TURN_ORDER` update in engine. Trace: `domain/trace.py` — extend `Kind` literal with `route`, `trade`, `river_*` kinds. Engine: `engine/turn.py` — add Home/River resolves, route logic, DAG extensions, driver extension. Demo: `engine/demo.py` — add `--show-river` / market args, print both markets and route status. No new modules. | Keeps layout consistent with Sections 2–4 (types + trace + turn + demo). No new generic framework. | New `markets.py` or `route_engine.py` modules rejected — premature abstraction before two use cases. |

---

## Recommended Approach

Stay additive and single-good (grain only). Treat Home Valley as the existing `market` and River Town as a second `MarketState` with independent supply/demand that reuses the same integer-safe price kernel. The route is a frozen `RouteState` carried in `GameState` with cost/capacity/reliability/established and a lightweight "secure route" command to unlock it; `ship_grain` then moves inventory to River Town at river price minus per-unit transport cost, capacity-limited and optionally reliability-adjusted via a deterministic RNG draw that defaults to zero loss. All new causal nodes are appended to the existing `CausalTrace` so Section 3–4 DAG validators still hold; legacy Home ids (`supply`, `price`) are kept as aliases so old tests remain green. Demo prints both market pulses and route status, and shows emergent arbitrage by toggling supply/demand configs.

---

## Work Plan

Order matters; each step unblocks the next. Checkpoints verify `ruff`/`pyright`/`pytest` before batching fixes.

### 1. Confirm workspace & branch → unblocks all edits

- Verify Git writes work in authoritative checkout:
  ```bash
  git rev-parse --show-toplevel  # .../game-historical-empire
  git status --short               # clean on section/5-two-markets-route
  git branch --show-current        # section/5-two-markets-route
  ```
  If Git write unexpectedly fails, stop and diagnose; do not use `/tmp` repo workaround.
- Deps: `uv sync --project backend` → 66 passed before changes.
- Files: none. Depends: none.

### 2. Domain — add River Town and River Route types, keep Home alias

- File: `backend/app/domain/types.py`
  - Add `RouteState(BaseModel, frozen=True)`: `transport_cost_per_unit: Money = 800` (`ge=0`), `capacity: Quantity = 20` (`ge=0`), `reliability_bps: BasisPoints` with `ge=0, le=10000, default 9000`, `established: bool = False`, `establish_cost: Money = 400` (or sibling constant in engine — keep in type for validation), `delay_turns: int = 0` (`ge=0`), `event_exposure: str = "river_risk"`.
  - Extend `GameState` with:
    ```python
    river_market: MarketState = Field(default_factory=lambda: MarketState(supply=80, demand=130, base_price=5200, current_price=5200))
    route: RouteState = Field(default_factory=RouteState)
    ```
    Keep `market: MarketState` as Home Valley alias (do not rename). Add `model_validator` note documenting that `market is Home Valley`. Add `TURN_ORDER` comment update to list both markets.
  - Extend `PlayerCommand.type` literal to include `"secure_route"` and `"ship_grain"`; `quantity` stays optional (used by `buy_grain` and `ship_grain`, ignored otherwise).
  - Add helper `RiverTownDefaults` constants exported for tests.
- File: `backend/app/domain/__init__.py` — re-export `RouteState`.
- Depends: #1. Validation: `uv run --project backend pyright` and `ruff check backend` clean. Quick manual: `uv run python -c "from app.domain.types import GameState; s=GameState(...); print(s.market, s.river_market, s.route)"`.

### 3. Trace — add route/trade/river kinds, keep DAG validators compatible

- File: `backend/app/domain/trace.py`
  - Extend `Kind` literal with `route`, `trade`, `river_supply`, `river_price` (or reuse `supply`/`price` with prefixed ids). Add `river_*` kinds if ids are prefixed.
  - Harden validator: `route_capacity`, `route_cost`, `route_reliability`, `shipment`, `trade_profit` require parents except when `delta==0` and `!established`. Keep `world`/`command` as allowed roots regardless of delta. Ensure `supply`/`price` aliases still pass.
  - Document expected subgraph for Section 5 in docstring.
- Depends: #2. Validation: `pyright` + `ruff` clean.

### 4. Engine — resolve two prices + route settlement, keep Home chain exact

- File: `backend/app/engine/turn.py`
  - Top: add constants `RIVER_DEFAULTS`, `ROUTE_ESTABLISH_COST = 400`, `ROUTE_DEFAULT_CAPACITY`, etc. Keep `TURN_ORDER` updated.
  - Extend `resolve_turn`:
    1. **Command pre-phase:** branch on `command.type`:
       - `secure_route`: handle cash clamp before other commands — same pattern as `expand_farm`.
       - `ship_grain`: compute `requested = command.quantity ?? 10`, `available_by_cap = route.capacity`, `available_by_inventory = inventory_before_settlement` (inventory at command time), `available_by_cash = INF` or transport cost? Ship cost is per unit, so affordable = cash // transport_cost_per_unit if cost>0 else requested; clamp to `min(requested, cap, inventory, affordable)`; record reason `limited_by_capacity`/`insufficient_inventory`/`insufficient_cash_for_transport` etc. Do not mutate cash/inventory yet for ship — defer to route settlement but emit `command` and `shipment_planned` nodes with `parent_ids=("command",)`.
       - Existing commands unchanged.
    2. **Production:** unchanged (farm_output parents `world`, `farm_capacity`).
    3. **Home supply:** `home_supply = before_home_supply + farm_output` (clamped) — node `supply` (alias) + `home_supply`.
    4. **River supply:** `river_supply = before_river_supply` (leave stable; optionally plus 10% of farm_output scaled? but keep stable for Section 5 simplicity) — node `river_supply` parents `()` or `world` with `delta==0` allowed as root if unchanged, or parents `("world",)` if needed; choose `parent_ids=("world",)` only if drought affects River mildly, but easiest: keep River supply unchanged with `parent_ids=()` and validator allowed for zero-delta capacity-like node? Better: make River supply child of `world` with 0 delta to keep Home/River parallel — simplest: `river_supply` `parent_ids=("world",)` with `delta` 0 then validator happy. Pick one and document.
    5. **Home price:** `_target_price`/`_bounded_price` on `home_supply`/`demand` → `home_price` alias `price`.
    6. **River price:** same helpers on `river_supply`/`river_demand` → `river_price`.
    7. **Settlement:** Home inventory capped by storage as before (`inventory` node parents `farm_output`, `storage_capacity`, `inventory_after_buy`). Emit `river_market` not affecting player inventory directly.
    8. **Route settlement:** if `command.type == "ship_grain"` and `route.established`:
       - `effective = clamped` prior; `reliability` draw: `rng = rng_for(state.run_seed, state.ruleset_version, state.turn, "route", "river_route", 0); loss_rng = rng.random()` ; `delivered = effective * reliability_bps // 10000` or `effective` if loss not materialised — keep `delivered == effective` for default 9000+ but consume RNG. Emit `shipment` node (`before=effective, after=delivered`), `route_cost` node (`delta = -effective * transport_cost_per_unit`), `route_capacity`, `route_reliability` nodes. Credit cash: `cash_after_route = cash + delivered * river_price // 1000 - effective * transport_cost_per_unit`. Deduct inventory: `inventory_final_after_ship = inventory_final - effective` (clamped ≥0). Add domain effects `shipment`, `trade_revenue`, `transport_cost`, `inventory_after_ship`.
       - If not established, emit `ship_rejected_no_access` node and do not move grain.
    9. **Valuation:** keep Section 4 exact split: `value(qty, home_price)` baseline, so `purchase_quantity_value`/`harvest_quantity_value`/`price_value_effect` stay at Home price. `cash_effect` now includes trade revenue minus transport cost when ship occurs. Assert `wealth_delta == cash_effect + purchase + harvest + price_value_effect` still holds.
    10. Convert all new `parent_ids` to tuples; final `CausalTrace(nodes=tuple(nodes))`; keep legacy `supply`/`price` aliases for backwards compat checks.
    11. Extend story drivers: candidates remain `command_cost`, `purchase_quantity`, `harvest_quantity`, `price_revaluation`, plus new `trade_profit` (`impact_money = trade_revenue - transport_cost - value_sold_at_home` or simply `trade_revenue - transport_cost` slice of `cash_effect`, ranked exact). Generate all candidates, filter `impact_money==0`, rank by `impact_bps = abs(impact)*10000//max(wealth_before,1)` desc then `id` asc, slice `[:3]` → `tuple`. Ensure Home-only turns produce ≤3 drivers without trade.
    12. Keep RNG ownership validation + price determinism.
  - Update module docstring to describe two markets + route.
- Depends: #3.
- Validation: `make test` / `make lint` / `make type` checkpoints. Manual: run `test_turn_kernel` subset expecting `supply` node still present.

### 5. CLI — show both market pulses and route status

- File: `backend/app/engine/demo.py`
  - Sample state: construct `GameState` with explicit `river_market` and `route`; keep existing defaults for Home.
  - CLI args: add `--secure-route` flag, `--ship QTY`, `--river-supply/--river-demand/--route-capacity/--transport-cost` overrides for ad-hoc arbitrage demos; or simpler: `--command secure_route|ship_grain|...` and reuse `--qty` / `--world`.
  - Print sections: `BEFORE STATE` now shows `HOME market ...` and `RIVER market ...` and `ROUTE: established=<bool> cost/unit=<n> cap=<n> reliability=<bps>`. After resolution, print both prices and trade profit when present. Keep concise `WHY?` (≤3 drivers) including `trade_profit` when material; `--verbose` adds `FULL CAUSAL TRACE` with river nodes + `DOMAIN EFFECTS` + `EDGES`. Keep contrast block.
- Depends: #4.

### 6. Tests — prove AC 1–6 and preserve Section 3–4 invariants

- File: `backend/tests/test_two_markets_route.py` (new)
  - `test_two_markets_can_have_different_prices` — construct state with `home supply=120 demand=100` vs `river supply=80 demand=140` (same base), resolve `hold` under `normal`, assert `home_price != river_price` (or use drought to widen gap). Also assert Home chain parents intact.
  - `test_transport_cost_can_erase_arbitrage` — same divergent prices case, create two states differing only in `route.transport_cost_per_unit` (high vs low), `ship_grain qty=10` with `established=True`, show high-cost profit ≤0 and low-cost profit >0. Validate `trade_revenue` + `transport_cost` trace nodes present.
  - `test_route_capacity_constrains_volume` — request `qty=50` with `route.capacity=20`, inventory large, assert `shipment` or `inventory_after_ship` delta == 20, `reason_code` indicates `limited_by_capacity`, cash/inventory respect clamped quantity.
  - `test_profitable_arbitrage_emerges_from_conditions_not_script` — two scenarios: (A) Home surplus / River shortage → profitable ship; (B) Home shortage / River surplus → unprofitable. Same route, same command, different market conditions → opposite signs. This proves condition-driven profit.
  - `test_can_remain_in_home_valley` — every old command plus `secure_route` untouched: `hold` with `route.established=False` completes, `next_state` valid, no inventory moved, DAG valid, `len(drivers) ≤3`.
  - `test_determinism_with_route` — same `state + ship_grain + world + seed` twice → `==`. Swapping seed changes at least one derived seed but still deterministic per seed.
- File extensions to existing suites (minimal):
  - `tests/test_core_types.py` or `test_turn_kernel.py` — extend `_base_state` helper to include `river_market`/`route` defaults so no legacy construction breaks.
  - Possibly `tests/test_engine_purity.py` still passes (no new imports).
- Depends: #4. Validation: `uv run --project backend pytest -v backend/tests/test_two_markets_route.py` plus full suite. Coverage not gating but report `pytest --cov`.

### 7. Docs & handoff

- Update `STATE.md` template for Section 5 completion (but only after gates pass): new Section 5 summary, file tree, verification block.
- No `DECISIONS.md` entry needed unless staleness deferral or alias choice is deemed durable; if so add `010 — Two Markets / Route Shape` documenting alias vs rename deferral.
- Depends: #6. Validation: `BUILD_SPEC.md` Status line flipped only after all AC gates pass; `STATE.md` reflects last known green with two-market verification commands.

---

## Validation Plan

60s gate before any push:

```bash
uv sync --project backend
make test              # = uv run --project backend pytest -v  (target 72+ passing: 66 existing + ≥6 new)
make lint              # = ruff check backend
make type              # = pyright  (0 errors, strict)
make format-check      # = ruff format --check backend
uv run --project backend python backend/app/engine/demo.py --world normal --command hold
uv run --project backend python backend/app/engine/demo.py --world drought --command ship_grain --qty 10  # or --command ship_grain with established fixture
uv run --project backend python backend/app/engine/demo.py --world drought --command ship_grain --qty 50 --verbose
```

Evidence per AC:

- AC #1 — `test_two_markets_can_have_different_prices` green + demo shows `HOME price=... RIVER price=...` diverging.
- AC #2 — `test_transport_cost_can_erase_arbitrage` green; also ad-hoc demo with `--transport-cost 5000` vs `200` toggling profit sign.
- AC #3 — `test_route_capacity_constrains_volume` green; domain effect `shipment` delta == capacity.
- AC #4 — `test_profitable_arbitrage_emerges_from_conditions_not_script` green; trace parents show `river_price` divergence, no scripted bonus string in `turn.py`.
- AC #5 — `test_can_remain_in_home_valley` green + `hold` demo without route stays valid.
- AC #6 — `test_determinism_with_route` green + repetition of `resolve_turn` twice identical + `rng_for` consumption still present.

Highest-risk validation: **AC #2 vs AC #4 interaction** — a too-high default transport cost makes all arbitrage unprofitable and the "emergent" test flaky; a too-low cost makes AC #2 false. Defaults must be tuned so `river_price - home_price` under Home-surplus/River-shortage config exceeds `transport_cost_per_unit`, but `transport_cost_per_unit` can be raised in a second fixture to exceed the gap. Pre-plan recommendation: `transport_cost_per_unit=800` with Home price ~4200, River ~5600 → gap 1400 milli (1.4 Money) vs transport 0.8 Money leaves profit; raising to 2000 erases it.

---

## Risks / Rollback

- **Risk: breaking existing `GameState` construction.** New required fields `river_market`/`route` could make `GameState(market=...)` construction in `tests/test_turn_kernel.py:22`, `test_causal_trace.py:33`, `test_invariants.py` etc. fail with `missing field`. Mitigation: give both fields `default_factory` so old construction keeps working; add regression test constructing with old shape. Rollback: revert `types.py` defaults and re-run legacy tests.
- **Risk: DAG validator failure from new route nodes with empty parents.** `route_capacity`/`route_reliability` with `delta >0` but `parent_ids == ()` would fail validator. Mitigation: make those nodes children of `command` when established, or children of `world` when not; gate with `delta==0` allowed roots rule.
- **Risk: wealth decomposition drift.** Adding trade cash credit outside `cash_effect` would break exact `cash + purchase + harvest + price == wealth` invariant and fail `test_wealth_decomposition_exact`. Mitigation: keep trade revenue inside `cash_effect` as in KDR #7; assert exact sum after implementation.
- **Risk: flaky reliability RNG affecting price.** RNG for reliability must not shift Home/River prices. Mitigation: consume a separate substream `"route"/"river_route"` ordinal 0, do not feed jitter into price helpers.
- **Risk: capacity clamp ambiguity (inventory vs capacity vs cash).** Need one explicit priority order to avoid double-clamping bugs. Mitigation: priority `min(requested, capacity, inventory, affordable_by_transport)` documented and matched to `reason_code` choice (mirrors `buy_grain`'s `insufficient_cash` vs `insufficient_storage` branching). Tests cover each limit separately.
- **Rollback:** Changes are confined to `backend/app/domain/types.py`, `backend/app/domain/trace.py`, `backend/app/engine/turn.py`, `backend/app/engine/demo.py`, plus new `backend/tests/test_two_markets_route.py`. No DB, no frontend, no `render.yaml`. Reverting the branch restores Section 4.

---

## Open Questions

- None that require user input before planning. One resolved assumption documented: **optional River Town staleness is out of scope** per spec — no fields `last_seen_river_price` or peek window are added. Trade access is `route.established` boolean, not a timed settlement with in-transit inventory. `STATE.md` market.supply stock-vs-flow follow-up stays **open** and is explicitly **not** fixed in Section 5.
- Assumed default tuning (to be validated by implementation harness and adjusted within the section): `river_market base 5200 / supply 80 / demand 130` and `route.transport_cost_per_unit 800, capacity 20, reliability 9000, establish_cost 400`. These are not spec-mandated values; they are chosen so AC #1/#2/#4 can each be demonstrated without a balance harness and can be corrected during implementation if tests show gap/cost mismatch.
- Assumed `ship_grain` inventory deduction is whole units moved (no partial loss modelled beyond reliability). Mill-unit transport cost handled as Money per unit (not milli) to keep integer profit arithmetic simple; if tests show fractional profit rounding mismatches, fall back to `transport_cost_per_unit` as `PriceMilliunits` with `//1000`.

