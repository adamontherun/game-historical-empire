# Section 6 — Five-Turn Headless Prototype — Plan (Rev 2)

**Date:** 2026-08-09
**Branch:** `section/6-five-turn-prototype` (from `origin/main` at `21acc1a`)
**Spec Authority:** `BUILD_SPEC.md` Section 6 (Status: NOT STARTED) + global §§10–16 + `DECISIONS.md` 001–009 + `STATE.md` §5
**Related:** `backend/app/domain/types.py`, `backend/app/domain/trace.py`, `backend/app/engine/turn.py`, `backend/app/engine/rng.py`, `backend/app/engine/demo.py`, `backend/app/engine/rounding.py`
**Revision notes:** Addresses 4 blockers from review — (1) supply stock/flow semantics resolved before 5-turn loop, (2) seed-variation requirements removed, (3) signals rewritten to truthfully describe mechanics, (4) scripted strategy policies made legal and distinct.

---

## Goal

Prove the core economic decision loop without a browser: a deterministic 5-turn terminal game using grain only, Home Valley + River Town + one River Route, with the four Section 3–5 player verbs (farm expansion, granary/storage, trade access via `secure_route`/`ship_grain`, cash preservation via `hold`/`buy_grain`) plus one major action per turn, an authored 5-turn world arc (growing settlement → surplus → warning → drought → aftermath), per-turn outcome reveal with ≤3 causal drivers, and a concise strategic summary. No database, no LLM, no rivals (Section 7), no generic pressure DSL (Section 8).

---

## Success Criteria (maps to Section 6 AC 1–7 + global rules)

1. **Exactly five decisions.** A complete run consumes 5 `PlayerCommand`s, increments `state.turn` from `0 → 5`, and then reports completion. No 6th decision is accepted. Tested by constructing a `FiveTurnGame` and feeding it exactly 5 commands and asserting `is_complete == True` and a 6th `submit()` raises/returns error.

2. **Terminal-completable.** A human can finish the game from the terminal via `uv run --project backend python -m app.cli` or `uv run --project backend python backend/app/engine/prototype.py` style interactive loop, choosing from a numbered menu each turn and seeing before/after state. No browser, no DB env var required.

3. **Deterministic (revised).** Same `run_seed + ruleset_version + ordered choice list (type+quantity)` with the same authored `TURN_SPECS` → byte-identical `final GameState`, `TurnResolution` history, causal traces, and summary. Verified by running two `FiveTurnGame(seed="X", choices=[...])` instances and `assert game1.history == game2.history`. Different **choices** (not different seeds) produce potentially different results; same choices with a different seed may produce identical economics until a seeded mechanic is introduced in Section 8 — that is expected and not asserted in Section 6.

4. **Three strategies diverge.** At least three scripted policies produce meaningfully different exposures/outcomes from the **same seed** and same `TURN_SPECS`:
   - *Farm-heavy* — expand farm early, hold through drought
   - *Storage-heavy* — build granary, buy grain in surplus, hold
   - *Trade-heavy* — secure route early, ship after drought
   Measured by at least 10% spread in final wealth or inventory or cash-low among the three under one representative seed. Test `test_three_strategies_diverge`. No assertion that any one strategy dominates across multiple seeds.

5. **Drought rewards preparation without claiming balance.** Under the fixed `T4 = drought`, a prepared strategy (had storage/trade access + inventory before T4) suffers smaller wealth loss on T4 **or** has higher final wealth than an unprepared farm-expansion-heavy strategy on the same seed. Tested by `test_drought_rewards_preparation` on a single representative seed. Section 6 does **not** assert "no universal best across 5 seeds" — robust cross-seed balance belongs to Sections 8/9.

6. **Top causes understandable.** Every turn's `PlayerOutcome.drivers` (≤3, ranked by wealth-bps, derived from trace not diff) is rendered in the outcome reveal as numbered sentences. Test that each `TurnResolution.causal_trace` has a chain `world → farm_output → home_supply → home_price` and that `trade_arbitrage`/`harvest_quantity`/`price_revaluation` drivers appear when relevant, and that verbose flag still prints full DAG. Signals describing each turn's situation are **truthful about mechanics** (see KDR #3).

7. **Concise strategic summary.** After T5 the game prints/returns a `StrategicSummary{final_wealth, final_cash, final_inventory, peak_inventory, wealth_delta_total, cash_low}` in human text plus structured data (no fake rivals). Test `test_summary_contains_required_fields`.

8. **Housekeeping:** `engine`+`domain` stay pure (no `fastapi`/`sqlalchemy`/`httpx`), canonical integers only, `ruff` clean, `pyright` strict 0 errors, existing 79 tests remain green (or updated to reflect intentional supply semantics change with justification).

---

## Context And Current Facts

- `main` at `21acc1a` (Sections 1–5 COMPLETE, 79 tests green — `test_sanity` + `test_engine_purity` + `test_core_types` 8 + `test_rounding` 7 + `test_determinism` 11 + `test_turn_kernel` 15 + `test_invariants` 7 + `test_causal_trace` 12 + `test_explanation` 4 + `test_two_markets_route` 13), `ruff` + `pyright` strict pass, demo covers Home/River/Route.
- **Domain (`backend/app/domain/types.py:1`):** `Money/Quantity/PriceMilliunits/BasisPoints` constrained ints, `InventoryState{grain}`, `PlayerState{cash, inventory, farm_capacity, storage_capacity}`, `MarketState{supply, demand, base_price, current_price, responsiveness=5000, max_movement_bps=2000}`, `RouteState{transport_cost_per_unit=800, capacity=20, reliability_bps=10000, established, delay_turns=0, event_exposure}`, `TurnContext{turn, run_seed, ruleset_version}`, `WorldCondition = Literal["normal","drought"]`, `PlayerCommand` with 6 types (`expand_farm, build_granary, buy_grain, hold, secure_route, ship_grain`) + `quantity?`, `GameState{turn, run_seed, ruleset_version, player, market:Home, river_market, route}` frozen, `to_turn_context()`. No sell_grain verb; `ship_grain` is the sell-via-trade verb.
- **Engine (`backend/app/engine/turn.py:1`):** `resolve_turn(state, command, world, rng_context)` with `TURN_ORDER = "command -> production -> home_supply -> river_supply -> home_price -> river_price -> settlement -> route_settlement -> valuation"`. Integer price model `_target_price`/`_bounded_price` via `rounding.py`, drought reduces `farm_output` 40% (`DROUGHT_YIELD_REDUCTION_BPS=4000`, `YIELD_PER_CAPACITY=10`), never directly price. `buy_grain` clamped `min(requested, affordable, space)`, `secure_route` costs 400 cash, `ship_grain` clamped `min(requested, capacity, inventory_final_pre_ship, affordable_by_transport)` with `delivered = effective*reliability//10000`, revenue `delivered*river_price//1000`, cost `effective*transport_cost//1000`, `arbitrage_margin` vs resolved prices. Wealth decomposition exact `wealth_delta = cash_effect + purchase+harvest+ship + price_value`. RNG ownership validated, price deterministic.
- **Trace (`backend/app/domain/trace.py:1`):** `CausalNode{parent_ids: tuple}`, `CausalTrace{nodes: tuple, edges derived}`, `DomainEffect`, `OutcomeDriver{id,label,kind,impact_money,impact_bps,causal_node_ids:tuple}`, `PlayerOutcome{wealth_delta,inventory_delta,price_delta,drivers:tuple≤3}`, `TurnResolution{next_state, domain_effects:tuple, causal_trace, player_outcome}`. Drivers filtered `impact_money!=0`, ranked `(-impact_bps, id)`.
- **STATE.md follow-up still open (blocker for Section 6):** `market.supply` is currently persistent stock (`next_supply = supply + farm_output`) while `farm_output` also enters player `inventory`; `buy_grain`/`ship_grain` do not reduce regional supply. Over repeated turns supply monotonically accumulates and will collapse prices without consumption/spoilage. Review gate requires this to be **resolved before** the 5-turn orchestrator is built (see KDR #5 revised). Earlier plan incorrectly deferred it to tuning.
- **Section 6 spec (BUILD_SPEC.md:989):** Five-turn arc T1 growing settlement / T2 surplus / T3 warning / T4 drought / T5 aftermath, grain only, Home Valley + River Town + River Route, farm/granary/trade/cash, one major action/turn, deterministic world pressures, outcome reveal text, CLI per-turn display (turn, signal, cash, operations, inventory, both market pulses, route, choices, result, top drivers), no DB/LLM, rivals out of scope (Section 7).
- **Tooling:** `backend/pyproject.toml` single project (`pydantic>=2.7`, `pytest`, `ruff`, `pyright strict py312`), Makefile `make test/lint/type/format-check`, `uv` sync, `frontend/` placeholder (Section 11).

---

## Constraints And Non-goals

**Must satisfy:**
- Pure `backend/app/engine` + `backend/app/domain` — no `fastapi`/`sqlalchemy`/`httpx`/`asyncpg`/`openai`/`clerk`. Prototype orchestration is sync, no DB, no network.
- Integer-only canonical state; deterministic via `derive_seed`/`rng_for` (BLAKE2b JSON array), no `random` global or `hash()`.
- One major action per turn; commands validated the same way as `turn.py` (insufficient cash/storage/capacity produce trace reason codes, not exceptions — `resolve_turn` is never allowed to produce negatives).
- Reuse existing `resolve_turn`; do not fork or duplicate its price/production/valuation logic into the prototype — except the minimal kernel change required to define supply semantics (KDR #5).
- No new physics for spoilage, credit, brands, skill scarcity, transport friction beyond the one River Route, etc.
- **Every authored signal must be truthful about mechanics** — prose must describe actual state/causes present in the model, not imaginary demand rises or harvest differences that the engine does not implement (KDR #3).

**Explicitly out of scope (defer to later sections):**
- Rival AI/scoring/legibility (Section 7 — Mira/Daran). Section 6 must not invent rival state or rival capital constraints. If a "rival headline" slot appears in the turn display, it is a **static placeholder** like `"Rivals arrive with Section 7"` or a per-turn signal that mentions rivals without simulating them. Do not add `rival_state` to `GameState`.
- Generic 30-event weighted content framework / pressure DSL (Sections 8 & 15). Section 6's world schedule is a hardcoded 5-element list, not a loader or JSON DSL. Section 8 will replace/augment it.
- Balance harness / strategy sweeps (Section 9), FastAPI (`Section 10+`), DB persistence (`Section 16`), advisor LLMs (`Section 17+`).
- Optional River Town staleness mechanic — already deferred in Section 5; remains deferred.
- Multiple goods, livestock/textile hedge, processing chain depth beyond grain (Sections 13–14).

**Non-goals for Section 6:**
- No new `sell_grain` command (sell via `ship_grain` to River Town is sufficient for "selling inventory" in T5). If playtest later proves Home-only selling is needed, add it in Section 14, not here.
- No separate operation tableau UI beyond text (Section 11 does the visual empire indicator).
- No cross-seed "no dominant strategy" claim; that belongs to Sections 8/9.

---

## Key Decisions

| # | Decision | Choice | Why | Alternative rejected |
|---|----------|--------|-----|----------------------|
| 1 | **Orchestration location & layering** | New pure module `backend/app/engine/prototype.py` encapsulates `FiveTurnGame` state machine + fixed 5-turn schedule; CLI `backend/app/cli.py` is a thin `input()`/`print()` driver that imports the prototype. Both are sync and tested without the CLI. `FiveTurnGame` holds `GameState`, `history: list[TurnResolution]`, `turn_limit=5`, `current_signal()` helper; `submit(command) -> TurnResolution` advances one turn via `resolve_turn`, appends to history, increments internal turn, and returns the resolution. `is_complete` is `len(history)==5` or `state.turn==5`. No async, no FastAPI. | Keeps decision loop testable without mocking `input()`; `prototype.py` is unit-testable as pure state machine, `cli.py` is thin I/O. Follows `engine` purity rule (no FastAPI). Single-responsibility: `turn.py` knows one turn, `prototype.py` knows five. | Putting loop logic directly in `demo.py` rejected — demo is a single-turn explainer with `--world/--command` flags, not a stateful 5-turn game. Making `GameState` itself hold history rejected — GameState is frozen canonical state, not a session. Adding a `GameSession` class in `domain/types.py` rejected — persistent session belongs with DB in Section 16; Section 6 needs in-memory only. |
| 2 | **Five-turn world + signal schedule (authored, truthful prose)** | Hardcoded 5-element list `TURN_SPECS: list[TurnSpec]` indexed by 0..4, each `TurnSpec{world: WorldCondition, signal: str, title: str}`. **Revised truthful signals** (each ≤120 chars, no claim of a mechanic not in the model): **T1 normal / title "A Growing Settlement" / "The growing settlement keeps food demand high."**, **T2 normal / title "Surplus" / "Repeated harvests have left grain abundant and prices weak."**, **T3 normal / title "Warning Signs" / "Dry weather suggests the next harvest may be threatened."**, **T4 drought / title "Drought" / "Drought cuts farm output — regional supply tightens."**, **T5 normal / title "Aftermath" / "Markets adjust to the drought's aftermath."** Only T4 is `drought`, so the cause→consequence chain is inspectable. The T2 "surplus" is not a different world — it emerges from the multi-turn stock dynamics defined in KDR #5. Signals are deterministic by turn index, not RNG-drawn. | Fixes the "prose says demand rising while demand is unchanged" incoherence. Each signal now describes the **actual** economic state: T1 describes the high-demand starting state, T2 describes the observable consequence of accumulated stock, T3 describes an observable weather signal that precedes the T4 world change, T4 describes the world change itself, T5 describes adjustment. No signal asserts a per-turn demand rise or harvest difference that the engine doesn't implement. | Prior signals "settlement expanding and demand is rising" / "strong harvest creates abundant grain" rejected — imply per-turn demand/harvest deltas not in the model. Introducing `WorldCondition` variants `surplus|warning|recovery` rejected — expands enum before Section 8. RNG-driven world per turn rejected — random spam. JSON/LLM signal loader rejected — Section 15. |
| 3 | **Signal representation** | Signals are plain `str` on `TurnSpec`; `FiveTurnGame.current_signal` returns that string. Also expose `current_turn_title()`. No new `Signal` model or event struct yet. If Section 8 needs `id/stage/signal_text/world_modifiers/activation_turn/causal_source_id`, that type is introduced there. | Smallest thing that satisfies CLI requirement "current signal" and Section 8's later richer type. Keeps prototype diff small. | New `SignalState{stage, text, modifiers}` type now rejected — premature abstraction (Global §15). JSON content loader for signals rejected — same reason. |
| 4 | **Command set — reuse existing six, no new verb** | Section 6's available major actions per turn are a **filtered subset** of the six existing `PlayerCommand.type` values: all six remain legal to submit, but the CLI menu shows 4–5 sensible choices (e.g., `hold, expand_farm, build_granary, buy_grain (qty 10), secure_route, ship_grain (qty 10)`) every turn. `ship_grain` is blocked by engine with `no_route_access` if route not established; menu still shows it but annotates "(requires River Route)". `buy_grain` defaults `quantity=10`, `ship_grain` defaults `10`; advanced qty entry is optional via `buy 20` input. No `sell_grain` added; T5 "selling inventory" is `ship_grain` to River Town, which already sells at river price. | Satisfies "farm expansion, granary/storage, trade access, cash preservation" without inventing a new sell path that would need its own trace nodes and wealth math. `hold` already covers "preserve liquidity". Keeps `PlayerCommand` stable and reuses Section 5 clamping/reason codes. | Adding `sell_grain(quantity)` that sells at Home price rejected — duplicates `ship_grain` and would need to decide Home supply increase on sell. Adding `buy_distressed_asset` as a special T5 command rejected — contested opportunities belong to Section 14. Adding `borrow`/`credit` rejected — Section 13+. |
| 5 | **Supply semantics — stock with bounded stock/flow accounting (blocker fix)** | **Define `MarketState.supply` as the persistent regional stock of grain at the start of the turn's price resolution** (integer quantity, ≥0). **Home Valley transition** becomes economically coherent: `stock_next = clamp(stock + farm_output - consumption, low=0)` where `consumption = min(demand, stock + farm_output)` — i.e., each turn's regional stock is drained by up to `demand` (the population's consumption) before the next turn, with floor 0 and `effective_supply_for_pricing = max(stock_next, 1)` style guard inside `_target_price` already. Concretely the kernel change in `engine/turn.py` is a single transition line plus trace/docs: keep `farm_output` → `supply` causal edge, but replace `next_supply = stock + farm_output` with `next_supply = max(0, stock + farm_output - demand)` (or `stock + farm_output - min(demand, stock + farm_output)` which is `max(0, stock + farm_output - demand)`). **River supply** remains stable (no farm add, no drain, or optionally same drain if River demand is higher — keep stable for Section 6 simplicity, but document that stable is a modeling choice meaning River's stock is exogenous to Home farm). Player `inventory` remains private storage (harvest into inventory is separate from regional stock addition — harvest is counted in both, reflecting that the player's farm is part of regional production; the overlap is documented as intentional for Section 6 and will be refined with ownership splits in Section 14). `buy_grain`/`ship_grain` still do not affect regional stock in Section 6 (deferred). This makes supply **bounded**: surplus when `farm_output > demand` raises stock and depresses price; shortage when `farm_output < demand` (notably during `drought` where output 60 < demand 135) drains stock and raises price. It also makes T2 surplus truthfully emergent from repeating `farm_output` additions with bounded accumulation, not from start-value tuning alone. Implement **before** `prototype.py` and update `TURN_ORDER` doc and supply trace reason codes (`harvest_added_to_supply` vs `stock_drained_by_consumption`). | This is the minimal coherent fix the review requires: decide stock vs flow vs signal and make the transition match the decision. A stock drained by demand is the smallest economic model that (a) prevents monotonic collapse over 5 turns without spoilage, (b) preserves the causal chain `drought → lower output → lower stock → scarcity → upward price pressure → price` that Section 3 mandates, (c) keeps `demand` meaningful across turns, and (d) makes the T1/T2 signals truthful (T2 surplus is now the traceable consequence of `stock += farm_output - demand` over two turns). It does not require spoilage, credit, brands, or a generic DSL. | Keeping `next_supply = stock + farm_output` with no drain rejected — it is the exact accumulation bug the review flags; tuning starts around it would hide the incoherence. Resetting `supply = farm_output` each turn (pure flow) rejected — erases stock causality and makes demand irrelevant to next turn's starting condition, also breaks the invariant that supply is a stock. Interposing consumption only in `prototype.py` wrapper before `resolve_turn` rejected — the kernel is the authority; the transition must live in `turn.py` so single-turn `resolve_turn` is coherent on its own. Adding buy/sell impact on regional stock now rejected — ownership split belongs to Section 14. |
| 6 | **CLI per-turn display & input** | Each turn prints (exact headings in code comments for testability): `TURN <n>/5 — <title>`, `Signal: <signal>`, `Player: cash=<n> grain=<n> farm=<n> storage=<n>`, `Operations: farm x<level> (cap ...), granary x<level> ...` (derived from capacities so no extra OperationState), `HOME Valley: supply <n> demand <n> price <milli> (<bps move>)`, `RIVER Town: supply <n> demand <n> price <milli>`, `ROUTE: established=<bool> cost=<n> capacity=<n> reliability=<bps>`, `Available actions: [1] Hold (preserve cash)  [2] Expand farm (-500 ...) ...`, `> Choose [1-6] (or 'buy 20' / 'ship 20'):`. After commit: `6 MONTHS LATER` header, `Wealth +N (cash ... + quantity ... + price ...)`, `Inventory +/-N`, `Home price X→Y`, `River price X→Y`, `WHY?` (1–3 drivers with label + impact), optional `Full trace: --verbose`. After T5: `=== STRATEGIC SUMMARY ===` with final wealth, best/worst turn by wealth_delta, inventory/cash trajectory, and per-turn driver highlights. Also support `--seed <s>` and `--choices hold,buy_grain:10,hold,ship_grain:10,hold` for non-interactive deterministic runs. | Directly maps to CLI requirements "turn number, current signal, player cash, player operations, grain inventory, Home Valley market pulse, River Town market pulse, route status, available major actions, result after commit, top causal drivers". Keeps menu runnable with one keypress (opportunity cost core loop). Non-interactive `--choices` aids determinism testing and CI. | Full TUI via `rich`/`textual` rejected — weight and mobile-first is Section 11 browser, not terminal. Using `argparse` subcommands per turn rejected — stateful loop is clearer. Rendering tables with box-drawing that breaks copy/paste determinism tests rejected. |
| 7 | **Determinism contract (revised)** | Canonical determinism input is `(run_seed: str, ruleset_version: str="1.0", choices: list[PlayerCommand])` with fixed `TURN_SPECS`. RNG per turn is `derive_seed(run_seed, ruleset_version, turn, namespace, entity_id, ordinal)` already validated in `turn.py`. `world` is **not** user-supplied nor seed-driven — it comes from `TURN_SPECS[turn].world`. Starting state is `DEFAULT_START_STATE(seed, version)`. Replaying same choices from same start is byte-identical; different choices may diverge. Seed variation is **not asserted** to diverge in Section 6 — two seeds with same choices may yield identical economics until Section 8 introduces a seeded mechanic; tests do not require divergence. | Removes the false seed-divergence requirement the review flags. Keeps the true determinism contract `same choices → same result` and `different meaningful choices → potentially different result`. | Asserting `seed A vs seed B → different final wealth` rejected — current engine has no seed-driven economics. Adding ephemeral noise to make seeds diverge rejected — would be fake variation. |
| 8 | **Strategic summary** | After T5, produce both human text and structured `StrategicSummary` Pydantic model: `final_state: GameState`, `history: tuple[TurnResolution, ...]`, `final_wealth: int` (cash + value at final home price), `wealth_delta_total: int` (sum of turn wealth_deltas, also equals `final_wealth - initial_wealth`), `cash_low: int`, `peak_inventory: int`, `turn_summaries: tuple[TurnSummary, ...]` each `{turn, signal, command, world, wealth_delta, drivers}`, plus `signals: list[str]`. Render as `STRATEGIC SUMMARY — 5 turns, wealth 1820→2410 (+590), cash low 120, peak grain 48, T4 drought: wealth -210 (harvest fell, price rose, storage cushioned)`. Include note that rival headlines are Section 7. | Satisfies "concise strategic summary" without inventing rivals. Structured model lets harness (Section 9) reuse it. | Free-form LLM narration for summary rejected — Section 17. Complex scoring (Sharpe, diversification bonus) rejected — belongs to balance harness. |
| 9 | **File layout** | `backend/app/engine/prototype.py` (~260 lines) — `TurnSpec`, `TURN_SPECS`, `START_STATE` factory, `StrategicSummary`, `FiveTurnGame` class (sync). `backend/app/cli.py` (~150 lines) — `main()` loop, format helpers `format_market_pulse`, `format_route_status`. Alternatively `backend/app/engine/cli.py` if `app/cli.py` would imply FastAPI layer — prefer `backend/app/cli.py` as top-level CLI entry per `pyproject` convention. `backend/app/domain/types.py` and `trace.py` unchanged except docstrings. `backend/app/engine/turn.py` **is changed** for KDR #5 (supply semantics) plus supply trace docs and tests. No new domain types beyond `TurnSpec`/`Summary` inside `prototype.py` (not domain canonical state). Tests in `backend/tests/test_five_turn_prototype.py`. Keep `backend/app/engine/demo.py` unchanged except `demo.py` supply trace now reflects drain (demo still valid). | Keeps `domain` frozen; prototype types are session-scoped, not canonical persisted state. Documents the one intentional kernel change (supply) as the gate requirement. | New `backend/app/game/` package rejected — premature package for 5-turn code. Putting `FiveTurnGame` in `turn.py` rejected — turn is one-turn kernel. Adding `backend/app/engine/session.py` name rejected — "session" implies DB persistence (Section 16). |
| 10 | **Rival headlines — placeholder only** | For Section 6, `FiveTurnGame` exposes `rival_headlines: tuple[str, ...]` that is **static per turn** e.g. `("", "Mira studies storage (Section 7)", ...)` or simply `()` empty and CLI prints `"Rivals: (arriving Section 7)"`. No rival state, no rival scoring function. Plan documents that real headlines (`Mira leased storage`, `Daran bought farmland`) are Section 7's deterministic scoring (`opportunity score = expected return × preference × capital × risk × exposure`). Tests do not assert headline content beyond existence. | Honors §7 without leaking scope; Turn 3 "rivals positioning" is satisfied by signal text mentioning rivals, not by simulating them. | Adding `RivalState{cash, inventory, strategy}` now rejected — would need economics rules and legibility tests that belong to Section 7. Mock rival that buys/sells grain and mutates market supply rejected — would be a hidden economy participant. |

---

## Recommended Approach

First, fix the kernel's multi-turn supply semantics (KDR #5): change `MarketState.supply` next-value in `engine/turn.py` from `stock + farm_output` to `max(0, stock + farm_output - demand)` so supply is a bounded regional stock drained by consumption, making the five-turn accumulation economically coherent and the T2 surplus truthfully emergent. Then stay additive: the 5-turn behavior is orchestrated by a new pure module `prototype.py` that calls the corrected `resolve_turn` five times with the revised authored truthful world/signal list. The CLI is a thin `print`/`input` loop around that module; all game logic is testable without the CLI. Signals are hardcoded truthful strings per turn index, not a DSL. The prototype starts from a single `START_STATE` (cash 1000, grain 20, farm 10, storage 100, Home 100/135/5000, River 75/140/5200, route 800/20/10000) — these starts are now **supplements** to, not substitutes for, the corrected transition. Wealth decomposition, DAG validation, and price monotonic invariants remain enforced by the kernel; the prototype adds only the 5-turn session invariant and the corrected divergence/preparation tests.

---

## Work Plan

Order matters; each step unblocks the next. Checkpoint commands before branching fixes.

### 1. Confirm workspace & branch → unblocks all edits

- Verify Git writes work in authoritative checkout:
  ```bash
  git rev-parse --show-toplevel  # .../game-historical-empire
  git status --short               # clean on section/6-five-turn-prototype
  git branch --show-current        # section/6-five-turn-prototype
  git log --oneline -3
  git fetch origin && git status --short
  ```
  If Git write unexpectedly fails, stop and diagnose; do not use `/tmp` repo workaround.
- Deps: `uv sync --project backend` → 79 passed before changes.
- Files: none. Depends: none.

### 2. Kernel — define supply semantics (blocker, before prototype)

- File: `backend/app/engine/turn.py` (edit, ~15 lines + docs)
  - Update module docstring to define `MarketState.supply` as **regional stock at start of pricing for that turn**.
  - Replace the Home supply transition:
    ```python
    # Before (Section 5):
    next_supply = clamp_non_negative(supply_before_harvest + farm_output)
    # After (Section 6):
    next_supply = max(0, supply_before_harvest + farm_output - before_demand)
    # (or clamp_non_negative(supply_before_harvest + farm_output - before_demand))
    # Keep `effective_supply_for_pricing = max(next_supply, 1)` guard already inside _target_price
    ```
  - Update trace labels/reason codes to distinguish `harvest_added_to_supply` (when output dominates) vs a combined `stock_after_consumption` note; keep `parent_ids=("farm_output",)` but add `demand` as an implicit parent comment or optionally include `"demand"` conceptually — keep actual `parent_ids` as `("farm_output",)` if demand is not a node, but document consumption in label: `f"Regional supply {before} + {farm_output} - {before_demand} → {next_supply}"`.
  - Update `TURN_ORDER` docstring if needed (order unchanged, semantics clarified).
  - Re-run `pytest` on the 79 existing tests — several supply-sensitive tests (`test_turn_kernel`, `test_invariants`, `test_two_markets_route`) will need **expected-value updates** (not logic bypass) to reflect the bounded stock. Update those tests' expected supply/price numbers, preserving the same invariant assertions (no negatives, positive price, `price` monotonic vs supply, drought still reduces output not price).
  - Add a focused invariant test in `test_five_turn_prototype.py` or `test_invariants.py` that asserts `next_supply == max(0, before_supply + farm_output - before_demand)` (with river stable still).
- Depends: #1. Validation: `make lint` / `make type` / `uv run --project backend pytest -v -k "test_turn_kernel or test_invariants"` green after updates.

### 3. Prototype — `FiveTurnGame` state machine + revised authored 5-turn schedule

- File: `backend/app/engine/prototype.py` (new, ~260 lines)
  - Define `TurnSpec` (frozen Pydantic or dataclass): `world: WorldCondition`, `signal: str`, `title: str`.
  - Define `TURN_SPECS: tuple[TurnSpec, ...]` length 5 with **revised truthful signals** per KDR #2 (T1 high demand, T2 surplus emergent, T3 warning, T4 drought, T5 aftermath). Document that Section 8 will replace this with a richer pressure arc.
  - Define `DEFAULT_START_STATE(seed: str, version: str) -> GameState` factory returning the tuned start state (cash 1000, grain 20, farm 10, storage 100, Home 100/135/5200, River 75/140/5200, route 800/20/10000). Document that starts are complements to the corrected transition, not substitutes.
  - Define `TurnRecord`/`StrategicSummary` (Pydantic frozen) or keep summary as computed property.
  - Define `FiveTurnGame` (plain class, sync):
    ```python
    class FiveTurnGame:
        turn_limit: int = 5
        def __init__(self, seed: str = "seed-001", version: str = "1.0", start_state: GameState | None = None): ...
        @property def state(self) -> GameState: ...
        @property def history(self) -> tuple[TurnResolution, ...]: ...
        @property def is_complete(self) -> bool: ...
        @property def current_turn(self) -> int: ...
        def current_spec(self) -> TurnSpec: ...  # TURN_SPECS[self.state.turn] if not complete else TURN_SPECS[-1]
        def current_signal(self) -> str: ...
        def available_commands(self) -> list[str]: ...  # the 6 types
        def submit(self, command: PlayerCommand) -> TurnResolution: ...
            # validates not complete, checks rng_context, calls resolve_turn(state, command, spec.world, state.to_turn_context())
            # appends, updates state = res.next_state
        def run(self, choices: list[PlayerCommand]) -> StrategicSummary: ...
        def summary(self) -> StrategicSummary: ...
    ```
  - Invariants: `submit` after complete raises `ValueError("game complete")`; `len(choices) !=5` for `run` raises; turn increments exactly once per submit; `state.run_seed`/`ruleset_version` unchanged throughout.
  - Expose `TURN_LIMIT = 5` and `TURN_SPECS` for tests.
- Depends: #2 (kernel semantics fixed). Validation: `uv run --project backend pyright backend/app/engine/prototype.py` clean; `ruff check backend` clean.

### 4. CLI — thin interactive + non-interactive runner

- File: `backend/app/cli.py` (new, ~150 lines)
  - Helpers: `format_market_pulse(m: MarketState) -> str`, `format_player(state)`, `format_route(state)`, `format_turn_header(game)`, `format_outcome(res)`, `format_summary(summary)`, `parse_choice(input_str) -> PlayerCommand` (accepts `1`–`6`, `hold`, `expand`, `granary`, `buy`, `buy 20`, `ship`, `ship 20`, `secure`, `route`).
  - `main(argv=None)`:
    - `argparse` with `--seed`, `--choices` (comma-separated `type[:qty]`), `--verbose`, `--no-interactive` flag.
    - If `--choices` given, runs headlessly `game.run(parsed_choices)` and prints each turn's outcome + summary, exits 0.
    - Else interactive loop: while not complete, print `BEFORE` pulse, prompt, parse, `game.submit(cmd)`, print `AFTER` outcome with `WHY?` drivers, loop. On `KeyboardInterrupt`/`EOFError` exit gracefully. After loop print `STRATEGIC SUMMARY`.
  - Entry point in `pyproject.toml` optional: `[project.scripts] historical-empire = "app.cli:main"` (not required, but document).
- Depends: #3.
- Validation: manual `uv run --project backend python -m app.cli --help`, `uv run --project backend python -m app.cli --seed demo --choices hold,hold,hold,hold,hold --verbose` completes 5 turns deterministically.

### 5. Tests — prove AC 1–7 (revised) and preserve invariants

- File: `backend/tests/test_five_turn_prototype.py` (new, ~220 lines)
  - `test_five_turn_game_requires_exactly_five_decisions` — 4 submits not complete, 5th complete, 6th raises.
  - `test_can_be_completed_from_terminal_noninteractive` — `game.run([hold]*5)` produces `len(history)==5` and summary fields and `is_complete`.
  - `test_determinism_same_seed_same_choices_same_final_state` — two games same seed+choices → `history ==` and `summary ==`; additionally `test_different_choices_may_diverge` (same seed, swap one command) shows different `final_wealth` or `history[2].next_state.market.current_price` — no assertion that different seeds diverge.
  - `test_supply_semantics_is_stock_drained_by_demand` — single-turn check: `state=GameState(supply=100, demand=120, ...), farm_output=100` → `next_supply = max(0, 100+100-120)=80`; drought `farm_output=60` → `next_supply=40`; price pressure reflects scarcity. This is the gate-proving test for KDR #5.
  - `test_three_strategies_diverge` — **corrected policies** (exactly 5 each, all legal):
    ```python
    farm_heavy   = [expand_farm, expand_farm, hold, hold, hold]
    storage_heavy= [build_granary, buy_grain:20, hold, hold, hold]
    trade_heavy  = [secure_route, build_granary, hold, ship_grain:10, ship_grain:10]
    ```
    Same seed, assert pairwise `final_wealth` or `final_inventory` or `cash_low` spreads >10% or at least non-equal (at least one pair differs by >10%).
  - `test_drought_rewards_preparation` — on seed `"prepare-seed"`, compare prepared (`build_granary, buy_grain:20, hold, hold, hold`) vs unprepared (`expand_farm, expand_farm, expand_farm, hold, hold`) with T4=T drought; assert `prepared wealth on T4` loss smaller or `final_wealth_prepared > final_wealth_unprepared`. A separate prepared-for-drought that combines storage+route:
    ```python
    prepared = [build_granary, buy_grain:20, secure_route, hold, ship_grain:10]
    ```
    may be used as an explicit preparation variant.
  - `test_each_turn_has_understandable_causes` — iterate `game.history`, assert each `res.player_outcome.drivers` ≤3, each trace contains `world`, `farm_output`, `home_supply`, `home_price`, and driver labels non-empty; first turn's `current_signal` matches `TURN_SPECS[0].signal` truthfully describing high demand.
  - `test_run_ends_with_concise_strategic_summary` — `summary = game.summary()` has `final_wealth`, `wealth_delta_total`, `turn_summaries` length 5, `final_state.turn==5`, and `summary.format()` contains `"STRATEGIC SUMMARY"` and `"5 turns"`.
  - Reuse `_assert_no_negatives` pattern on `final_state`.
  - Removed: `test_no_universal_best_across_5_seeds` and any `different seed must diverge` test.
- Also update legacy expectations in `test_turn_kernel.py` / `test_two_markets_route.py` for the new bounded supply (expected supply values only, not logic).
- Depends: #2 + #3.
- Validation: `uv run --project backend pytest -v backend/tests/test_five_turn_prototype.py` plus full `make test` (target ~88+ passing: 79 existing (updated) + ≥9 new).

### 6. Demo/CLI polish & edge handling

- In `prototype.py`: ensure `FiveTurnGame.submit` validates `PlayerCommand.quantity` is ignored for non-qty types (same as `turn.py`); surface `insufficient_cash/insufficient_storage/no_route_access` via the returned trace rather than raising, so the CLI can show "Buy failed: insufficient storage" as outcome, not crash.
- In `cli.py`: handle `ship_grain` without established route gracefully (engine returns `no_route_access` driver, CLI prints `Shipment blocked — secure the River Route first.`).
- Add `if __name__ == "__main__": main()` guard.
- Depends: #4, #5.

### 7. Docs & handoff

- Update `STATE.md` template for Section 6 completion (only after gates pass): new Section 6 summary, file tree (`backend/app/engine/turn.py` supply change, `backend/app/engine/prototype.py`, `backend/app/cli.py`, `tests/test_five_turn_prototype.py`), verification block with `uv run --project backend python -m app.cli --choices hold,hold,hold,hold,hold` example, and note that `STATE.md` follow-up "supply semantics" is now **resolved** (stock drained by demand, bounded).
- No `DECISIONS.md` entry needed unless the hardcoded `TURN_SPECS` vs. generic DSL tradeoff is deemed durable; if so add `010 — Five-Turn Authored Arc & Supply-as-Stock` documenting supply-as-stock definition and that it will be replaced/augmented by pressure arc in Section 8.
- Keep `BUILD_SPEC.md` Status line `NOT STARTED` until gates pass; flip to `COMPLETE` only in the final commit.
- Depends: #6.

---

## Validation Plan

60s gate before any push (≈ 2 min):

```bash
uv sync --project backend
make test              # = uv run --project backend pytest -v  (target ~88+ passing; revise expectations for bounded supply)
make lint              # = ruff check backend
make type              # = pyright  (0 errors, strict)
make format-check      # = ruff format --check backend

# Kernel supply semantics — the gate test
uv run --project backend pytest -v -k test_supply_semantics_is_stock_drained_by_demand

# Headless prototype determinism (choices, not seeds)
uv run --project backend python -m app.cli --seed demo-seed-001 --choices hold,hold,hold,hold,hold
# Same again must match final wealth line:
uv run --project backend python -m app.cli --seed demo-seed-001 --choices hold,hold,hold,hold,hold 2>&1 | grep "final wealth"

# Three corrected distinct strategies (non-interactive)
uv run --project backend python -m app.cli --seed demo-seed-001 --choices expand_farm,expand_farm,hold,hold,hold
uv run --project backend python -m app.cli --seed demo-seed-001 --choices build_granary,buy_grain:20,hold,hold,hold
uv run --project backend python -m app.cli --seed demo-seed-001 --choices secure_route,build_granary,hold,ship_grain:10,ship_grain:10

# Prepared vs unprepared drought
uv run --project backend python -m app.cli --seed prepare-seed --choices build_granary,buy_grain:20,hold,hold,hold
uv run --project backend python -m app.cli --seed prepare-seed --choices expand_farm,expand_farm,expand_farm,hold,hold

# Verbose trace after drought turn
uv run --project backend python -m app.cli --seed demo-seed-001 --choices hold,hold,hold,hold,hold --verbose 2>&1 | grep -A2 "FULL CAUSAL"

# Single-turn demo still works with bounded supply (Section 5 regression)
uv run --project backend python backend/app/engine/demo.py --world drought --command hold
uv run --project backend python backend/app/engine/demo.py --world drought --command ship_grain --established --qty 10
```

Evidence per AC (revised):

- AC #1 — `test_five_turn_game_requires_exactly_five_decisions` green + manual `--choices` with exactly 5 succeeds, with 6 rejected.
- AC #2 — manual `python -m app.cli` interactive with `--seed` completes without DB/LLM; non-interactive `--choices` succeeds in CI.
- AC #3 — `test_determinism_same_seed_same_choices_same_final_state` green; repeating the same `--choices` CLI invocation produces identical `final wealth` line; swapping one choice changes result.
- AC #4 — `test_three_strategies_diverge` green with corrected policies; the three CLI runs above show ≥10% wealth/inventory spread.
- AC #5 — `test_drought_rewards_preparation` green; the prepared CLI run shows smaller T4 wealth loss than farm-heavy (check `T4 wealth_delta` lines). No cross-seed dominance test.
- AC #6 — `test_each_turn_has_understandable_causes` green; each turn's `WHY?` prints ≤3 drivers and signals match truthful `TURN_SPECS` prose.
- AC #7 — `test_run_ends_with_concise_strategic_summary` green; CLI ends with `STRATEGIC SUMMARY — 5 turns ...`.
- Supply gate — `test_supply_semantics_is_stock_drained_by_demand` green; `home_supply` after normal vs drought shows bounded drain, not monotonic accumulation.

Highest-risk validation: **supply semantics change** — updating `turn.py` will shift expected `supply`/`price` numbers in `test_turn_kernel`/`test_two_markets_route`/`demo` golden values. Must update those expectations to `max(0, supply+farm_output-demand)` and re-verify that drought still raises price via scarcity and that `ship_grain`/`buy_grain` invariants still hold. A second risk is that drain `supply + farm_output - demand` with initial demand 135 may drive supply to 0 under repeated drought if farm 10×6=60 < 135 — that is economically correct (scarcity) and `effective_supply=1` guard in `_target_price` keeps price positive but bounded movement may need 2–3 turns to saturate. Verify price stays within `base ± 60%` over 5 turns.

---

## Risks / Rollback

- **Risk: breaking existing 79 tests via kernel supply change.** Mitigation: change is one arithmetic line + docs; update only the expected supply/price literals in tests, keep invariant assertions (no negatives, positive price, monotonic price vs supply, drought reduces output not price). Run `pytest -k test_turn_kernel` first before full suite. Rollback: revert `turn.py` one line and restore test literals — prototype still builds on old acumulación but gate will have flagged the debt again.
- **Risk: `market.supply` drain drives supply to 0 and price target spikes, hitting `max_movement` cap repeatedly.** Mitigation: `max_movement_bps=2000` already caps per-turn move to 20%; over 5 turns even a zero-stock `effective_supply=1` yields at most ~2.5× price growth, legible. Verify `price` stays `≥1` and `≤3*base`.
- **Risk: `test_engine_purity` fails because new `cli.py` imports `rich`/`httpx`.** Mitigation: `cli.py` imports only `sys`, `argparse`, `app.domain`, `app.engine`; keep purity checker scoped to `engine`+`domain` or allowlist `cli.py` if checker is `rglob("backend/app/**/*.py")`.
- **Risk: CLI double-submit or stale revision races.** Mitigation: `FiveTurnGame.submit` is synchronous and single-owner; no concurrency in Section 6.
- **Risk: capacity/inventory/cash clamping reasons diverge between `buy_grain` and `ship_grain`.** Mitigation: keep engine's existing reason codes (`insufficient_storage`, `limited_by_capacity`, `insufficient_cash_for_transport`, `no_route_access`) and surface them as single-line CLI notes.
- **Rollback:** Changes are confined to `backend/app/engine/turn.py` (supply line + docs), new `backend/app/engine/prototype.py`, `backend/app/cli.py`, `backend/tests/test_five_turn_prototype.py`, plus `STATE.md`/`BUILD_SPEC.md` status flip. No DB, no frontend, no `render.yaml`. Reverting the branch restores Section 5.

---

## Open Questions

- None that require user input before approval. One resolved assumption: **supply is a persistent stock drained by `demand` each turn** (`next = max(0, stock + farm_output - demand)`), which is the minimal economically coherent definition that makes the 5-turn surplus/drought dynamics truthful without adding spoilage. If Section 9/14 later introduces per-commodity consumption curves or spoilage, this line will be generalized to `stock + output - demand - spoilage` but the stock definition remains.
- Assumed starting tunings (supplements to, not substitutes for, corrected transition): `GameState(player cash 1000, grain 20, farm 10, storage 100, Home supply 100/demand 135/base 5000/price 5000, River supply 75/demand 140/base 5200/price 5200, route 800/20/10000/established False)`.
- Assumed `buy_grain`/`ship_grain` default `quantity=10` when CLI user presses a bare number key; if tests show insufficient differentiation, bump to `quantity=20` for `buy_grain` in prompts.

