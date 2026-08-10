# Section 8 — Pressure-Driven Event Arc — Plan (Rev 2 — incorporates R1–R8)

**Date:** 2026-08-10 (revised 2026-08-10 after review round 1)
**Branch:** `section/8-pressure-driven-event-arc` (from `origin/main` at `53fb3e6`)
**Spec Authority:** `BUILD_SPEC.md` Section 8 (Status: NOT STARTED) + global §§10–16 + `DECISIONS.md` 001–011 + `STATE.md` §7
**Related:** `backend/app/domain/types.py`, `backend/app/domain/trace.py`, `backend/app/engine/turn.py`, `backend/app/engine/actor.py`, `backend/app/engine/prototype.py`, `backend/app/engine/rivals.py`, `backend/app/cli.py`, `backend/tests/test_five_turn_prototype.py`, `backend/tests/test_deterministic_rivals.py`
**Review input:** `docs/plans/2026-08-10-section-8-review-round-1.md` (R1–R8, all blocking except R7/R8 housekeeping — all addressed)

---

## Goal

Replace the current hard-coded `TURN_SPECS` + single-value `next_world_known` warning with a small, coherent, deterministic world-pressure system that drives one 5-turn arc:

```
normal → early_dry → worsening_dry → drought → aftermath
```

Keep impact **systemic** (drought reduces farm output → supply signal → price pressure → price, never `price *= 1.4`), keep the 5-turn headless game intact, and keep the system trivially inspectable without introducing a generic 30-event DSL, content loader, or new goods/rivals.

---

## Success Criteria (maps to Section 8 AC + global rules)

1. **At least one useful warning before impact (AC1, proven via R5/R6 instrument).** Turns 2–3 surface early (`early_dry`) and worsening (`worsening_dry`) dry signals that a prepared player can act on. Usefulness is proven operationally: two legal T1–T3 preparation histories diverge materially on the T4 drought outcome (see R5 test below). Stage inspectable via `pressure_for_turn(idx)` / `game.current_pressure` / trace.

2. **Drought stays systemic (AC2).** Drought changes `farm_output` via `actor.compute_farm_output` (40% reduction `DROUGHT_YIELD_REDUCTION_BPS=4000`), then `home_supply` (`signal_next = max(0, signal+farm_output-demand)`), then `home_price` via `_target_price/_bounded_price`. No direct price mutation or `world_modifiers.price *= X`. Proved by trace parent chain and absence of price-hack code.

3. **Different preparation → different result (AC3, R5).** Same authored drought + same seed, different legal preparation during the warning stages → materially different T4 drought exposure/consequence (inventory retained, wealth decomposition, cash exposure, price revaluation). No assertion about which strategy "wins" overall; no multi-seed win-rate sweep (deferred to Section 9).

4. **Deterministic & inspectable (AC4).** Same `run_seed + ruleset_version + choices[5]` → identical pressure progression, signals, world conditions, prices, rival headlines, and `TurnResolution` trace. Pressure state readable via `pressure_for_turn(state.turn)` and `FiveTurnGame.current_pressure` and via `TurnResolution.causal_trace` pressure node. No new canonical field in `GameState`.

5. **Small, no DSL (AC5).** One hard-coded 5-element arc (~15 lines), one new enum + one frozen model (`PressureStage` + `PressureState`), one pure helper module (`engine/pressure.py`). No JSON loader, no weighted sampler, no formula-in-content, no DB, no LLM. `ruff`/`pyright` clean.

6. **Housekeeping preserved.** `engine`+`domain` pure (AST test), integers only, deterministic RNG via `rng_for`/`derive_seed`, causal drivers still ≤3 ranked by exact wealth-bps, rivals still deterministic via integer scoring and structured threat, 112 existing tests remain green (none relaxed).

---

## Context And Current Facts (verified against code)

- **Spec §8 (`BUILD_SPEC.md:1166`):** One pressure arc with *possible* fields `id, stage, signal_text, world_modifiers, activation_turn, causal_source_id`; authored turns allowed; must stay systemic; no generic 30-event framework. `world_modifiers` is optional per spec language — review correctly notes it is not required (R2).

- **Domain `backend/app/domain/types.py:1`:** Frozen Pydantic canonical types. `GameState{turn, run_seed, ruleset_version, player, market:Home, river_market, route}` with `to_turn_context()`. `WorldCondition = Literal["normal","drought"]`. `PlayerCommand` 6 verbs. All `ge=0` int aliases. No pressure type yet. `GameState` currently has no pressure field — adding one would duplicate information deterministically implied by `turn` + arc (R1).

- **Trace `backend/app/domain/trace.py:1`:** `CausalNode{id,label,kind,before,after,delta,reason_code,parent_ids}`, `CausalTrace` DAG validator (parents before child, `allowed_empty_roots = {"world","command"}` at line ~102, then capacity/demand/route exceptions at 109–141, then strict kind check at 149–165, then fallback at 170–173). `Kind` literal does not contain `"pressure"` but `CausalNode.kind` is typed `str` (line 47), so any kind string is accepted structurally. Validator fallback logic: a node with `kind` not in the must-have-parents list at 149–165 and with `delta is None` is allowed as parentless root without being in `allowed_empty_roots` (see verification below). `PlayerOutcome.drivers` ≤3 ranked by exact wealth-bps. Trace is emitted structurally, not diffed.

- **Engine `backend/app/engine/turn.py:1`:** Explicit `TURN_ORDER = command → production → home_supply → river_supply → home_price → river_price → settlement → route_settlement → valuation`. Helpers `compute_farm_output` (40% drought), `_target_price/_bounded_price`, supply `signal_next = max(0, signal+farm_output-demand)`, wealth exact decomposition `cash + quantity_value(price_before) + price_value(price_before→price_after)`. Drought already systemic. Current signature `resolve_turn(state, command, world: WorldCondition, rng_context)` — will change to `resolve_turn(state, command, pressure: PressureState, rng_context)` (R1).

- **Actor `backend/app/engine/actor.py:1`:** Shared integer primitives `YIELD_PER_CAPACITY=10`, `DROUGHT_YIELD_REDUCTION_BPS=4000`, `EXPAND_FARM_COST=500`, `BUILD_GRANARY_COST=300`, `ROUTE_ESTABLISH_COST=400`, `cost_for_quantity`, `value_for`, `resolve_buy/shipment/etc.` Single source for player+rival.

- **Prototype `backend/app/engine/prototype.py:1`:** `FiveTurnGame` owns `state + history[5] + _rivals:{mira,daran} + _rival_history[5]`. `TurnSpec{world, signal, title}` frozen. `TURN_SPECS` 5 truthful signals (T1 high demand normal, T2 surplus weak normal, T3 warning normal, T4 drought, T5 aftermath normal). `default_start_state` Home 100/90/5000 River 80/130/5200 route 800/20/10000 player 1000/20/10/200. `_next_world_known_for_turn(idx)==drought` only on idx=2 (T3→T4). Two-phase rival timing: choose from `ObservableContext{world_now, next_world_known, home_price_pre…}`, resolve player `resolve_turn`, settle rivals at `buy@pre_home`, `ship@resolved_river`, `valuation@resolved_home`. `StrategicSummary.format()` with rival lines.

- **Rivals `backend/app/engine/rivals.py:1`:** `RivalProfile` vs `RivalState`, integer/bps scoring `score = expected_return × pref_bps × capital_bps × risk_bps × exposure_bps` with `mul_basis_points`, prefs bps (Mira 4500/15000/13000/14500 farm-averse, Daran 16000/7000 farm-hungry), structured `ObservableContext.next_world_known` drives threat boost, exact-tie `rng_for`.

- **CLI `backend/app/cli.py:1`:** Entry point is `backend/app/cli.py` (not `backend/app/engine/cli.py` — verified `ls` shows only the former exists). Invocation is `uv run --project backend python backend/app/cli.py ...` (R7). Supports `--choices` non-interactive and `--verbose`.

- **Tests:** `112` passing (8 core +7 rounding +11 determinism +15 kernel +7 invariants +12 causal +4 explanation +13 two-markets +17 five-turn +16 deterministic-rivals). `make test/lint/type/format-check` are Section 1 gates. Citations `test_five_turn_prototype.py:153` (`test_no_single_policy_dominates_all_metrics`) and `:368` (`test_turn_specs_length_and_titles` asserts `titles[1]=="Surplus"`) verified correct.

---

## Verification of Review Claims (required by task)

Each cited location was checked directly rather than trusted:

- **`trace.py:149-165` and `170-173`:** Confirmed. The block at 149–165 enumerates `kind in ("production","supply","demand","price","inventory","quantity_value_effect","purchase_quantity_value","harvest_quantity_value","price_value_effect","wealth","route","trade","river_supply","river_price")` must have parents. Kind `"pressure"` is not in that set, so it does not trigger that gate. The subsequent fallback at 170–173 — `if node.delta is not None and node.delta != 0: raise; continue` — admits any remaining node with `delta is None` (or 0) as a root without being in `allowed_empty_roots`. A node `kind="pressure", delta=None, parent_ids=()` therefore validates as-is. **Review R3 is correct.** No validator change needed; do not add `"pressure"` to `allowed_empty_roots`.

- **`test_five_turn_prototype.py:153`:** Confirmed. Line 153 is `def test_no_single_policy_dominates_all_metrics()` — the test that already shows three policies diverging in final wealth/peak inventory without any pressure system. **Review R5 is correct:** that divergence alone cannot prove the pressure arc does anything.

- **`test_five_turn_prototype.py:368`:** Confirmed. Line 368 is `def test_turn_specs_length_and_titles()` asserting `titles[1] == "Surplus"`. Renaming T2 to `"Surplus / Early Dry"` would break this existing assertion. **Review R4 is correct:** keep title `"Surplus"`.

- **`backend/app/cli.py`:** Confirmed via `ls`. Only `backend/app/cli.py` exists; `backend/app/engine/cli.py` does not. The draft's `python -m app.engine.cli` is wrong. **Review R7 is correct.** Also confirmed the draft's smoke policy `build_granary,build_granary,buy_grain,hold,ship_grain` ships without `secure_route` and thus always blocks — weaker smoke than intended.

No review claim was found to be wrong. All eight items are adopted as stated.

---

## Constraints And Non-goals

**Must satisfy:**
- Pure `engine`+`domain`: no `fastapi`/`sqlalchemy`/`httpx`/`openai`. `pydantic` only.
- Integer canonical state; no `random` global, no `hash()`, no floats.
- Deterministic via `run_seed + ruleset_version + turn + namespace + entity_id + ordinal` → `blake2b` (`rng.py:1`).
- Causal trace first-class, drivers derived from trace, ≤3, ranked by exact wealth-bps.
- Rivals remain session-owned, isolated supply, integer scoring, structured threat.
- Keep change minimal: refactor existing `TURN_SPECS` into pressure, do not rewrite turn kernel.

**Explicitly out of scope (defer):**
- Generic weighted content framework / JSON content loader / `content_version` (Section 15).
- Additional goods, rivals, credit, spoilage, brands, automation, multi-day delays.
- Balance harness sweeps and win-rate analysis (Section 9) beyond the single preparation-vs-drought proof.
- Persistence / FastAPI / React (Sections 10–11).
- River Town stale-info mechanic (Section 5 optional).

---

## Key Decisions (all settled — no open choices remain)

| # | Decision | Choice (revised per R1–R8) | Why | Alternative Rejected |
|---|----------|-----------------------------|-----|----------------------|
| 1 | **Pressure representation — where & how small (R1,R2)** | Introduce `PressureStage = Literal["normal","early_dry","worsening_dry","drought","aftermath"]` and frozen `PressureState{ pressure_id: str, stage: PressureStage, activation_turn: int, world: WorldCondition, signal: str, title: str, causal_source_id: str }` — **exactly 7 fields, no `world_modifiers`**. Put the enum+model in `backend/app/domain/types.py` (or `backend/app/domain/pressure.py` re-exported via `domain/__init__.py`) and pure helpers in `backend/app/engine/pressure.py`. `pressure_id` e.g. `"northern_drought"` stable; `causal_source_id` e.g. `"pressure:northern_drought"` for trace root. Each entry carries its own `world` (normal vs drought) so pressure drives both `world` and `signal/title` from one source. Validate `activation_turn == index in PRESSURE_ARC`. Frozen models keep canonical discipline. | Satisfies spec's suggested fields without DSL; pressure drives both world and prose from one source. Small: one model + one helper file. `world_modifiers` omitted per R2 — speculative scaffolding forbidden by BUILD_SPEC §31. No `GameState` pressure field per R1 — pressure is fully derived from `turn` + `PRESSURE_ARC`, so storing it would create a second source of truth allowing invalid `pressure_stage != world` combos. | Storing pressure as loose `dict` rejected — unvalidated. Generic `Event{weight, duration, modifiers}` registry rejected — overengineering for one arc. Raw string stage rejected — typo-prone. Adding `pressure_stage` to `GameState` rejected (R1) — would duplicate `turn`-derived fact. Adding `world_modifiers: Mapping` "typed but unused" rejected (R2) — speculative. |
| 2 | **Single source of truth for `world` (R1)** | Change `resolve_turn` signature to `resolve_turn(state, command, pressure: PressureState, rng_context) -> TurnResolution` and derive `world = pressure.world` internally. `FiveTurnGame.submit` calls `pressure = pressure_for_turn(idx)` then `resolve_turn(state, command, pressure, ctx)`. Legacy `world`-only calls removed; tests updated to pass pressure objects. | Eliminates the three-representation hazard (`PRESSURE_ARC` vs `GameState.pressure_stage` vs bare `world` arg) where `early_dry` could pair with `world=drought`. One fact, one place. Inspectability via `pressure_for_turn(state.turn)` and `game.current_pressure` and trace is sufficient (R1). | Keeping `resolve_turn(state, command, world)` alongside pressure rejected — permits inconsistent states. Adding `GameState.pressure_stage` to make pressure inspectable via state rejected — `pressure_for_turn(state.turn)` already inspectable without canonical duplication. |
| 3 | **Arc authoring — mapping 5 turns to 5 stages** | Hard-code `PRESSURE_ARC: tuple[PressureState,5]`: <br>0 `normal` {world normal, signal "The growing settlement keeps food demand high.", title "A Growing Settlement", activation 0}, <br>1 `early_dry` {world normal, signal **"Grain remains abundant, but the rains have begun to fail."**, title **"Surplus"** (unchanged, R4), activation 1}, <br>2 `worsening_dry` {world normal, signal **"The dry spell persists. Farmers warn the next harvest is at risk."**, title "Warning Signs", activation 2}, <br>3 `drought` {world drought, signal "Drought cuts farm output — regional supply tightens.", title "Drought", activation 3}, <br>4 `aftermath` {world normal, signal "Markets adjust to the drought's aftermath.", title "Aftermath", activation 4}. <br>T2/T3 prose is observational about **rainfall**, not about output — production in T2/T3 is still normal (R4). Only T4 flips `world=drought`, so only T4 actually changes `farm_output`. | Preserves 5-turn contract; two escalating warnings before impact with mechanically truthful prose (no claim that T2 harvest weakened). Keeps `test_turn_specs_length_and_titles` green by retaining T2 title `Surplus`. | Extending to 6 turns rejected — breaks "exactly five decisions". T2 pure surplus with no hint rejected — would leave only one warning, weakening AC1. Making early/worsening also `world=drought` (light drought) rejected — would duplicate impact logic and confuse systemic chain. Tinted wording "weak harvest hints" rejected (R4) — implies output already fell, which it did not. |
| 4 | **Structured threat for rivals — derive from pressure, not prose (keep-as-is + R1)** | Replace `_next_world_known_for_turn` with `next_world_known_for_turn(idx) -> WorldCondition \| None` that returns `"drought"` iff `PRESSURE_ARC[idx].stage == "worsening_dry"` (i.e., T3 warns of T4), else `None`. Implemented in `pressure.py` and re-exported. `FiveTurnGame._observable_for` builds `ObservableContext` with `next_world_known` from that helper (and `world_now = pressure.world`). No prose parsing. Optional `pressure_stage` on `ObservableContext` not needed for Section 8 — keep existing `next_world_known`-only boost tiers unchanged so fingerprint tests stay stable. | Keeps "author cause, simulate consequences" — warning is authored stage, not parsed prose. No behavior change for rivals in Section 8 beyond sourcing the same drought warning from pressure. | Parsing `signal_text` for `"dry"`/`"warning"` rejected — brittle. Passing full `PressureState` into scoring with arbitrary modifiers rejected — DSL creep. Adding `early_dry`→graded boost now rejected — would alter determinism without requirement; keep boost only on `worsening_dry`. |
| 5 | **Trace integration — pressure as causal root (R3)** | In `turn.py:resolve_turn`, emit leading `CausalNode(id="pressure_stage", kind="pressure", label=<title-matched, e.g. "Worsening dry conditions">, before=None, after=None, delta=None, reason_code=f"pressure:{pressure.pressure_id}:{pressure.stage}", parent_ids=())` then make `world` node its child (`parent_ids=("pressure_stage",)`). Chain: `pressure_stage → world → farm_output → home_supply → home_price → … → wealth`. **No** `after=stage_hash`, no numeric delta — there is no economic numeric delta for "worsening_dry" (R3). **Do not** modify `trace.py` `_validate_dag` — the node validates via existing fallback `delta is None` path (verified). No price node directly parented to pressure. | Guarantees AC2 systemic path is visible in trace; pressure is inspectable root. Minimal: one extra node, fits existing DAG validator without loosening invariants. | Adding pressure with `after=stage_hash` rejected (R3) — invents a numeric. Adding `"pressure"` to `allowed_empty_roots` or otherwise loosening validator rejected (R3) — unnecessary and weakens invariant. Skipping trace node rejected — loses inspectability. Direct pressure→price edge rejected — violates "no direct price hack". |
| 6 | **Signal/title ownership** | `TurnSpec` is subsumed by `PressureState` (they carry `signal,title,world`). For backward compat, keep `TurnSpec` as alias: define `TURN_SPECS = tuple(TurnSpec(world=p.world, signal=p.signal, title=p.title) for p in PRESSURE_ARC)` in `prototype.py`, so existing imports (`from prototype import TURN_SPECS`) keep working. New code reads `PRESSURE_ARC`. Single source is `PRESSURE_ARC`; `TURN_SPECS` is derived, not authored. | Zero churn for tests that import `TURN_SPECS`; single source of truth. | Deleting `TurnSpec` outright would break half the test suite. Keeping two independent lists rejected — duplicate source. |
| 7 | **No new costs / market math** | Reuse existing `actor.compute_farm_output` for drought effect (no new formula). No `world_modifiers` map consumed. Python formula stays authoritative. Section 15 parameterization deferred. | Honors "Python owns formulas, content supplies parameters" without premature abstraction. | Introducing executable price lambda or yield factor param now rejected — would change kernel without need. |

All seven decisions are locked. No "Open Questions" remain.

---

## Recommended Approach

Stay additive and keep the kernel as authority. Implement in dependency order so each step is testable:

1. **Domain:** Add `PressureStage` + `PressureState` (7 fields, frozen) in `backend/app/domain/types.py` (or new `pressure.py` re-exported). Export via `domain/__init__.py`.

2. **Engine:** New `backend/app/engine/pressure.py` (≈40 lines) defining `PRESSURE_ARC: tuple[PressureState,5]` hard-coded with the 5 stages above (exact prose per R4, `activation_turn == index`), helper `pressure_for_turn(idx) -> PressureState`, and `next_world_known_for_turn(idx)`. No RNG, pure, validated.

3. **Prototype:** Refactor `backend/app/engine/prototype.py` so `TURN_SPECS` is derived from `PRESSURE_ARC` and `FiveTurnGame` drives progression from `PRESSURE_ARC`. Change `submit()` to `pressure = pressure_for_turn(idx)` → `resolve_turn(state, command, pressure, ctx)`. Build `ObservableContext` threat from `pressure.stage == "worsening_dry"` via `next_world_known_for_turn`. Remove `_next_world_known_for_turn`. Add `current_pressure` accessor.

4. **Turn kernel:** Extend `backend/app/engine/turn.py` to accept `PressureState` (derive `world`), emit the `pressure_stage` root node as specified in Decision 5, parent `world` to it. Keep `_target_price/_bounded_price` and actor calls unchanged. Ensure wealth decomposition still exact.

5. **Rivals/CLI:** No scoring rewrite; only threat source changes. `backend/app/cli.py` displays `game.current_pressure.title/signal/stage` per turn header; `StrategicSummary.format()` appends stage per turn. Keep two-phase rival timing unchanged.

All functions remain plain, sync, deterministic.

---

## Work Plan

### 1 — Domain pressure types (no behavior change yet)
- **Surface:** `backend/app/domain/types.py` (+ optional `backend/app/domain/pressure.py`) + `backend/app/domain/__init__.py`
- **Do:** Add `PressureStage` literal and `PressureState` frozen model with exactly `pressure_id, stage, activation_turn, world, signal, title, causal_source_id`; `activation_turn` validated `0..4`; `causal_source_id` default `f"pressure:{pressure_id}:{stage}"` if not supplied.
- **Tests (new, `backend/tests/test_pressure_arc.py`):** Enum validation, frozen, `activation_turn` matches index, 5 stages in order `normal→early_dry→worsening_dry→drought→aftermath`, world only `drought` on impact, `causal_source_id` stable, invalid stage rejected.
- **Depends:** none.

### 2 — Pressure arc + pure helpers
- **Surface:** `backend/app/engine/pressure.py` (new) + `backend/app/engine/__init__.py` re-export if convenient
- **Do:** Hard-code `PRESSURE_ARC` tuple of 5 `PressureState` with truthful signals per R4 (ids stable `"northern_drought"`). Implement `pressure_for_turn(idx)`, `world_for_turn(idx)`, `next_world_known_for_turn(idx)` (worsening→drought only). Validate at import that `p.activation_turn == index` for all p. No RNG, no I/O.
- **Tests (extend `test_pressure_arc`):** Determinism (`pressure_for_turn(2).stage == "worsening_dry"`), `next_world_known == "drought"` only on idx 2, idempotent, `pressure_id` stable across calls, out-of-range index raises.
- **Depends:** 1.

### 3 — Prototype refactor to drive from pressure (keep TURN_SPECS compat)
- **Surface:** `backend/app/engine/prototype.py`
- **Do:** Import `PRESSURE_ARC`/`pressure_for_turn`/`next_world_known_for_turn`. Derive `TURN_SPECS` from `PRESSURE_ARC` for compat. Remove `_next_world_known_for_turn`. Change `submit()` to read `pressure = pressure_for_turn(idx)` and pass `pressure` to `resolve_turn`. Update `_observable_for` to populate `next_world_known` from `next_world_known_for_turn(idx)` (not signal parse). Add `current_pressure` property returning `pressure_for_turn(len(self._history))` when not complete.
- **Tests:** Existing `test_five_turn_prototype.py` still passes via derived `TURN_SPECS`; new assertions — `game.current_pressure.stage` progression `normal→early_dry→worsening_dry→drought→aftermath`, `current_signal` matches arc, `current_spec` still mirrors pressure.
- **Depends:** 2.

### 4 — Turn kernel signature + trace integration (pressure → world chain)
- **Surface:** `backend/app/engine/turn.py` (+ no change to `backend/app/domain/trace.py` per R3)
- **Do:** Change `resolve_turn(state, command, pressure: PressureState, rng_context)` — derive `world = pressure.world` at top. Emit leading `pressure_stage` node with `kind="pressure"`, `delta=None`, `reason_code=f"pressure:{pressure.pressure_id}:{pressure.stage}"`, `label` from `pressure.title`-derived string (e.g. stage title). Make `world` node `parent_ids=("pressure_stage",)`. Keep all other nodes parented as before. Update docstring and `TURN_ORDER` comment to `pressure_stage -> world -> production -> ...` if documented. No price mutation.
- **Tests:** `backend/tests/test_causal_trace.py` — assert chain `pressure_stage → world → farm_output → home_supply → home_price → … → wealth` exists for all turns; drought path includes `drought_reduced_yield`; **no edge from `pressure_stage` directly to any price node** (price reachable only via `farm_output`/`supply`); drivers still ≤3. Verify `trace.py` validator not modified.
- **Depends:** 3.

### 5 — Rivals & settlement keep structured threat (no scoring rewrite)
- **Surface:** `backend/app/engine/rivals.py` + `prototype.py: _observable_for`
- **Do:** Confirm `ObservableContext.next_world_known` now sourced from `next_world_known_for_turn` (pressure stage) — same observable value as before (drought only on T3). Keep integer/bps scoring constants unchanged.
- **Tests:** `backend/tests/test_deterministic_rivals.py` — behavioral fingerprint still holds across early/worsening/drought contexts; early_dry (T2) does **not** trigger drought threat, worsening_dry (T3) **does**; add probe `pressure_for_turn(1).stage=="early_dry"` → `next_world_known is None` vs `pressure_for_turn(2).stage=="worsening_dry"` → `"drought"`.
- **Depends:** 3.

### 6 — CLI + summary polish
- **Surface:** `backend/app/cli.py`, `backend/app/engine/prototype.py:StrategicSummary`
- **Do:** Display current pressure stage/title/signal per turn header (e.g. `PRESSURE normal → early dry → worsening → DROUGHT → aftermath`) and include stage in non-interactive run output. In `StrategicSummary.format()`, append stage per turn (`T2 Surplus [early_dry]`). Ensure outcome reveal still shows `WHY?` drivers and rival headlines.
- **Depends:** 3.

### 7 — New Section 8 acceptance tests (exact specification per R5/R6)
- **Surface:** `backend/tests/test_pressure_arc.py` (or `test_pressure_driven_arc.py`) — new file; no existing test assertions relaxed
- **Do:** Implement exactly the tests enumerated in the Validation Plan below. They prove AC1+AC3 via one instrument (R5/R6), AC2 systemic chain, AC4 determinism/inspectability, and AC5 smallness.
- **Depends:** 4, 5.

---

## Validation Plan

```bash
# Must pass (Section 1 gates still apply)
uv sync --project backend
make test              # = uv run --project backend pytest -v  → ~120 passed (112 + ~8 new pressure tests)
make lint              # = ruff check backend  → All checks passed
make type              # = pyright  → 0 errors, 0 warnings
make format-check      # = ruff format --check backend  → 27 files already formatted (count increments by new files)

# Targeted checks
uv run --project backend pytest -v backend/tests/test_pressure_arc.py
uv run --project backend pytest -v backend/tests/test_five_turn_prototype.py backend/tests/test_deterministic_rivals.py backend/tests/test_causal_trace.py

# CLI smoke — use the real path backend/app/cli.py (R7), and a policy that actually ships (R7)
uv run --project backend python backend/app/cli.py --help
uv run --project backend python backend/app/cli.py --choices "hold,hold,hold,hold,hold" --seed seed-8-001
uv run --project backend python backend/app/cli.py --choices "build_granary,secure_route,buy_grain,hold,ship_grain" --seed seed-8-001 --verbose
uv run --project backend python backend/app/cli.py --choices "build_granary,buy_grain,hold,hold,hold" --seed seed-8-001 --verbose

# Quick harness sanity — preparation divergence is on T4, not final wealth (R5)
uv run --project backend python -c "
from app.engine.prototype import FiveTurnGame
from app.domain.types import PlayerCommand as C
# Two histories differing only in warning-stage preparation (T2-T3), same seed
prep = [C(type='build_granary'), C(type='buy_grain', quantity=20), C(type='hold'), C(type='hold'), C(type='hold')]
unprep = [C(type='expand_farm'), C(type='expand_farm'), C(type='expand_farm'), C(type='hold'), C(type='hold')]
for name, choices in [('prep', prep), ('unprep', unprep)]:
    g=FiveTurnGame(seed='seed-8-001')
    g.run(choices)
    t4 = g.history[3]  # drought impact turn
    print(name, 'T4 wealth', t4.player_outcome.wealth_delta, 'inv', t4.next_state.player.inventory.grain, 'price', t4.next_state.market.current_price)
"
```

### Exact new/changed tests (what each proves)

No existing assertions are edited or relaxed. All new tests live in `backend/tests/test_pressure_arc.py` (plus one extension in `test_causal_trace.py` and one probe in `test_deterministic_rivals.py`).

| Test | File | What it proves | How it isolates pressure |
|------|------|----------------|--------------------------|
| `test_pressure_arc_is_five_stages_in_order` | `test_pressure_arc.py` | Arc is exactly 5 stages, order `normal→early_dry→worsening_dry→drought→aftermath`, `activation_turn == index`, only `drought` stage has `world=="drought"` | Direct assertion on `PRESSURE_ARC` — no 30-event DSL, no `world_modifiers` field exists |
| `test_pressure_signals_observational_not_output` | `test_pressure_arc.py` | T2/T3 prose describes rainfall, not harvest output; production in T2/T3 is still normal | Checks `PRESSURE_ARC[1].signal == "Grain remains abundant, but the rains have begun to fail."` and `PRESSURE_ARC[2].signal == "The dry spell persists. Farmers warn the next harvest is at risk."`; also asserts `PRESSURE_ARC[1].world=="normal"` and `PRESSURE_ARC[2].world=="normal"` |
| `test_warning_is_useful_preparation_changes_drought_outcome` (**AC1+AC3, R5/R6**) | `test_pressure_arc.py` | Warning is **useful** — acting on it changes the T4 drought consequence | Same seed `seed-8-useful`, two histories differing only in T1–T3 preparation during `early_dry`/`worsening_dry` warnings: <br>• Prepared: `[build_granary, buy_grain:20, hold, hold, hold]` <br>• Unprepared: `[expand_farm, expand_farm, expand_farm, hold, hold]` <br>Run both via `FiveTurnGame`, compare **T4 `TurnResolution`** (index 3, the drought turn): assert at least two of `{inventory after T4, wealth decomposition (quantity_value_effect / price_value_effect / cash delta), T4 wealth_delta, price revaluation}` differ by material delta (>0, and at least one exceeds a threshold like ≥50 money or ≥5 grain). **Does not** assert which total final wealth wins, does not sweep seeds, does not assert win rate (Section 9 territory). This is the sole instrument for AC1 and AC3. |
| `test_drought_still_systemic_via_production_and_supply` (**AC2**) | `test_pressure_arc.py` | Drought reaches price only through production→supply→price, no direct price hack | For same state/capacity, `pressure=drought` farm_output < `pressure=normal` farm_output via `compute_farm_output`; trace for T4 has `pressure_stage` → `world` → `farm_output` → `supply` → `price` chain; **assert no edge `(pressure_stage, price)` or `(pressure_stage, home_price)` exists** — price parents must include `supply`/`farm_output` |
| `test_pressure_chain_determinism_and_inspectability` (**AC4**) | `test_pressure_arc.py` | Arc is deterministic and inspectable without DB | Same `seed+choices[5]` twice → byte-equal `state`, `rival_history`, and `history[*].causal_trace`; `pressure_for_turn(state.turn)` and `game.current_pressure` match `PRESSURE_ARC[turn]`; trace for each turn contains `pressure_stage` node with `reason_code == f"pressure:{pressure_id}:{stage}"` |
| `test_no_generic_dsl_smallness` (**AC5**) | `test_pressure_arc.py` | System is small, no generic framework | `len(PRESSURE_ARC)==5`, no JSON loader import, `PressureState` has exactly 7 fields (assert via `model_fields` keys), `backend/app/engine/pressure.py` is <60 lines (checked via file read), no weighted sampler |
| `test_pressure_to_world_is_only_via_stage` | `test_causal_trace.py` (extension) | Validates causal topology invariant | Already-covers `pressure_stage` → `world` edge; fail if any price node's `parent_ids` contains `pressure_stage` directly |
| `test_threat_only_on_worsening_not_early` | `test_deterministic_rivals.py` (probe) | Structured threat is stage-derived, graded correctly | `next_world_known_for_turn(1) is None` (early_dry does not threaten), `next_world_known_for_turn(2) == "drought"` (worsening does) — proves prose not parsed |

**Expected evidence after implementation:**
- CLI per-turn headers show stages `normal → early_dry → worsening_dry → DROUGHT → aftermath` and signals escalate before impact; `6 MONTHS LATER` still shows wealth/inventory/price and `WHY?` drivers plus `MIRA`/`DARAN` headlines.
- Trace dump (verbose) includes chain `pressure_stage:pressure:northern_drought:worsening_dry → world:drought → farm_output:drought_reduced_yield → home_supply → home_price → … → wealth`.
- Same seed+choices second run byte-equal (`final_wealth`, `rival_history`, trace).
- `test_warning_is_useful_preparation_changes_drought_outcome` passes (T4 deltas diverge); `test_no_single_policy_dominates_all_metrics` still passes but is no longer the instrument for Section 8 — the new test is.
- No existing test file edited to relax an assertion (verified by diff).

---

## Risks / Rollback

- **Risk:** Changing `TURN_SPECS` signals (T2 surplus wording) breaks substring checks like `assert "abundant" in TURN_SPECS[1].signal.lower()` (`test_five_turn_prototype.py:365`). **Mitigation:** R4 wording retains `"Grain remains abundant"` as prefix, so `"abundant"` substring still passes. Keep title `"Surplus"` exactly so `test_turn_specs_length_and_titles` stays green. Verify with `grep -n abundant backend/tests/*.py` before merge.

- **Risk:** Changing `resolve_turn` signature breaks existing call sites (`prototype.py`, `test_*`, `demo.py`). **Mitigation:** Update all call sites in same commit to pass `PressureState` instead of `world`. `world` is a field on the pressure object, so the kernel change is one line (`world = pressure.world`). No churn in `GameState`.

- **Risk:** Adding `kind="pressure"` trace node could be mistaken for needing a validator change. **Mitigation:** Do not change `trace.py` — verified the fallback admits `delta=None` parentless nodes. Add a regression that would fail if someone later tightens the validator.

- **Risk:** Rivals that previously keyed on `next_world_known=="drought"` only on idx 2 still work, but adding `early_dry` stage could be confused with threat. **Mitigation:** Keep existing boost tiers unchanged; only `worsening_dry` triggers drought threat, `early_dry` is `None` (new test proves it).

- **Rollback:** Revert `prototype.py` to re-introduce hard-coded `TURN_SPECS` and ignore `pressure` module; remove `pressure_stage` node emission from `turn.py`; restore `resolve_turn(state, command, world, ctx)` signature. No `GameState` migration needed because no field was added.

---

## Decisions Settled (R8)

This plan is decision-complete. The two choices previously listed under "Open Questions" are resolved:

1. **GameState field vs pure derivation:** Resolved per R1 — no `GameState.pressure_stage` field. Pressure is derived from `turn` via `pressure_for_turn` and surfaced via `game.current_pressure` + trace.

2. **Signal prose for T2 early dry:** Resolved per R4 — `"Grain remains abundant, but the rains have begun to fail."` (observational rainfall, not output), title remains `"Surplus"`.

No unresolved implementation choices remain.

---

## Keep as-is (from review, preserved)

- One hard-coded five-stage arc; no DSL, no JSON loader, no weighted sampler.
- Five turns, not six — protects "exactly five decisions."
- `TURN_SPECS` derived from `PRESSURE_ARC` for temporary compatibility, with `PRESSURE_ARC` stated explicitly as the single source.
- Only T4 actually changes production; T5 aftermath emerges from carried economic state.
- Structured threat derived from `stage == "worsening_dry"`, never from parsing prose.
- Reuse `actor.compute_farm_output`; no new RNG or event sampler.

---

## What Changed Versus the Draft (summary for reviewers)

| Area | Draft | Rev 2 (this plan) | Review item |
|------|-------|-------------------|-------------|
| `GameState.pressure_stage` field | Added with default `"normal"` | **Removed** — no canonical field; pressure derived from `turn` | R1 BLOCKING |
| `resolve_turn` signature | `resolve_turn(state, command, world, ctx)` unchanged | `resolve_turn(state, command, pressure: PressureState, ctx)` deriving `world` internally | R1 BLOCKING |
| `world_modifiers` on `PressureState` | `Mapping[str,int]` typed but unused | **Deleted** — 7 fields exactly | R2 BLOCKING |
| `PressureState` field count | 8 with optional modifiers | 7 exactly, `activation_turn == index` validated | R2 |
| Trace pressure node | `after=stage_hash?` contemplated | `before/after/delta = None`, `kind="pressure"`, no hash | R3 BLOCKING |
| `trace.py` validator | Proposed adding `"pressure"` to `allowed_empty_roots` | **No change** — existing fallback already admits it (verified at 149–165/170–173) | R3 BLOCKING |
| T2 prose | "weak harvest hints" (implies output fell) | **"Grain remains abundant, but the rains have begun to fail."** (rainfall, not output) | R4 BLOCKING |
| T2 title | "Surplus / Early Dry" | **"Surplus"** (unchanged, preserves `test_turn_specs_length_and_titles:368`) | R4 BLOCKING |
| AC3 evidence | 3 policies → different `final_wealth` (already passes today) | **T4 drought result** between two T1–T3 preparation histories → differing inventory/wealth-decomposition/cash exposure | R5 BLOCKING |
| AC1 evidence | Inspect `current_signal` before T4 | **Folded into R5 test** — warning proven useful by preparation → T4 divergence | R6 |
| CLI commands | `python -m app.engine.cli` + non-shipping smoke policy | `uv run --project backend python backend/app/cli.py` + `build_granary,secure_route,buy_grain,hold,ship_grain` | R7 |
| Open Questions | Two unresolved choices | **Removed** — both settled (R1+R4) | R8 |
| Scope | — | No strategy-win-rate or multi-seed sweep; Section 9 deferred | R5 keep-as-is |

Nothing in the "keep as-is" list was dropped. No turn-kernel rewrite, no new abstraction beyond the one `pressure.py` helper, no Section 9/15 material.
