# Section 8 — Pressure-Driven Event Arc — Plan

**Date:** 2026-08-10
**Branch:** `section/8-pressure-driven-event-arc` (from `origin/main` at `53fb3e6`)
**Spec Authority:** `BUILD_SPEC.md` Section 8 (Status: NOT STARTED) + global §§10–16 + `DECISIONS.md` 001–011 + `STATE.md` §7
**Related:** `backend/app/domain/types.py`, `backend/app/domain/trace.py`, `backend/app/engine/turn.py`, `backend/app/engine/actor.py`, `backend/app/engine/prototype.py`, `backend/app/engine/rivals.py`, `backend/tests/test_five_turn_prototype.py`, `backend/tests/test_deterministic_rivals.py`

---

## Goal

Replace the current hard-coded `TURN_SPECS` + single-value `next_world_known` warning with a small, coherent, deterministic world-pressure system that drives one 5-turn arc:

```
normal → early dry signal → worsening dry signal → drought impact → aftermath
```

Keep impact **systemic** (drought reduces farm output → supply signal → price pressure → price, never `price *= 1.4`), keep the 5-turn headless game intact, and keep the system trivially inspectable without introducing a generic 30-event DSL, content loader, or new goods/rivals.

---

## Success Criteria (maps to Section 8 AC + global rules)

1. **At least one useful warning before impact.** Turns 2–3 surface early/worsening dry signals that a prepared player can act on. Verified by inspecting `current_signal` / pressure stage before turn 4.

2. **Drought stays systemic.** Drought changes `farm_output` via `actor.compute_farm_output` (40% reduction), then `home_supply` (`signal_next = max(0, signal+farm_output-demand)`), then `home_price` via `_target_price/_bounded_price`. No direct price mutation or `world_modifiers.price *= X`. Proved by trace path + code search for price hack absence.

3. **Different preparation → different result.** Given same seed/drought, a storage/trade-prepared policy vs a farm-heavy policy produces materially different `final_wealth`, `cash_low`, `price_value_effect`, and inventory outcomes. Existing Section 6 non-dominance idea extends: at least two of the three harness policies diverge by ≥ material delta on drought impact.

4. **Deterministic & inspectable.** Same `run_seed + ruleset_version + choices[5]` → identical pressure progression, signals, world conditions, prices, rival headlines, and `TurnResolution` trace. Pressure state is readable without reconstructing from diffs: via `GameState.pressure_stage` (or equivalent accessor), via `TurnResolution.causal_trace` nodes (`pressure_stage → world → farm_output → supply → price …`), and via `FiveTurnGame` history. `next_world_known` structured threat remains, now derived from pressure.

5. **Small, no DSL.** One hard-coded 5-element arc (≈15 lines), one new enum + one frozen model, one pure helper module. No JSON loader, no weighted sampler, no formula-in-content, no DB, no LLM. `ruff`/`pyright` clean.

6. **Housekeeping preserved:** `engine`+`domain` pure (AST test), integers only, deterministic RNG via `rng_for`/`derive_seed`, causal drivers still ≤3 ranked by exact wealth-bps, rivals still deterministic via integer scoring and structured threat, 112 existing tests remain green.

---

## Context And Current Facts

- **Spec §8 (BUILD_SPEC.md:1166):** One pressure arc with fields `id, stage, signal_text, world_modifiers, activation_turn, causal_source_id`; authored turns allowed; must stay systemic; no generic 30-event framework.

- **Domain `backend/app/domain/types.py:1`:** Frozen Pydantic canonical types. `GameState{turn, run_seed, ruleset_version, player, market:Home, river_market, route}` with `to_turn_context()`. `WorldCondition = Literal["normal","drought"]`. `PlayerCommand` 6 verbs. All `ge=0` int aliases. No pressure type yet.

- **Trace `backend/app/domain/trace.py:1`:** `CausalNode{id,label,kind,before,after,delta,reason_code,parent_ids}`, `CausalTrace` DAG validator (parents before child, roots limited to `world/command` plus zero-delta capacity/route). `PlayerOutcome.drivers` ≤3 ranked by exact wealth-bps. Trace is emitted structurally, not diffed.

- **Engine `backend/app/engine/turn.py:1`:** Explicit `TURN_ORDER = command → production → home_supply → river_supply → home_price → river_price → settlement → route_settlement → valuation`. Helpers `compute_farm_output` (40% drought), `_target_price/_bounded_price`, supply `signal_next = max(0, signal+farm_output-demand)`, wealth exact decomposition `cash + quantity_value(price_before) + price_value(price_before→price_after)`. Drought already systemic.

- **Actor `backend/app/engine/actor.py:1`:** Shared integer primitives `YIELD_PER_CAPACITY=10`, `DROUGHT_YIELD_REDUCTION_BPS=4000`, `EXPAND_FARM_COST=500`, `BUILD_GRANARY_COST=300`, `ROUTE_ESTABLISH_COST=400`, `cost_for_quantity`, `value_for`, `resolve_buy/shipment/etc.` Single source for player+rival.

- **Prototype `backend/app/engine/prototype.py:1`:** `FiveTurnGame` owns `state + history[5] + _rivals:{mira,daran} + _rival_history[5]`. `TurnSpec{world, signal, title}` frozen. `TURN_SPECS` 5 truthful signals (T1 high demand normal, T2 surplus weak normal, T3 warning normal, T4 drought, T5 aftermath normal). `default_start_state` Home 100/90/5000 River 80/130/5200 route 800/20/10000 player 1000/20/10/200. ` _next_world_known_for_turn(idx)==drought` only on idx=2 (T3→T4). Two-phase rival timing: choose from `ObservableContext{world_now, next_world_known, home_price_pre…}`, resolve player `resolve_turn`, settle rivals at `buy@pre_home`, `ship@resolved_river`, `valuation@resolved_home`. `StrategicSummary.format()` with rival lines.

- **Rivals `backend/app/engine/rivals.py:1`:** `RivalProfile` vs `RivalState`, integer/bps scoring `score = expected_return × pref_bps × capital_bps × risk_bps × exposure_bps` with `mul_basis_points`, prefs bps (Mira 4500/15000/13000/14500 farm-averse, Daran 16000/7000 farm-hungry), structured `ObservableContext.next_world_known` drives threat boost, exact-tie `rng_for`. `SettlementContext` now needed for post-resolution valuation. Headlines derived from `reason_code + buy_actual/ship_effective`.

- **Tests:** `112` passing (8 core +7 rounding +11 determinism +15 kernel +7 invariants +12 causal +4 explanation +13 two-markets +17 five-turn +16 deterministic-rivals). `make test/lint/type/format-check` are Section 1 gates.

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
- Balance harness sweeps (Section 9) beyond proving preparation vs concentration still holds.
- Persistence / FastAPI / React (Sections 10–11).
- River Town stale-info mechanic (Section 5 optional).

---

## Key Decisions

| # | Decision | Choice | Why | Alternative Rejected |
|---|----------|--------|-----|----------------------|
| 1 | **Pressure representation — where & how small** | Introduce `PressureStage = Literal["normal","early_dry","worsening_dry","drought","aftermath"]` and frozen `PressureState{ id:str, stage:PressureStage, world:WorldCondition, signal:str, title:str, activation_turn:int, causal_source_id:str }`. Add `PressureArc = tuple[PressureState,5]` hard-coded. Put the enum+model in `backend/app/domain/types.py` (or `backend/app/domain/pressure.py` re-exported via `domain/__init__.py`) and pure helpers in `backend/app/engine/pressure.py`. `id` e.g. `"northern_drought"`; `causal_source_id` e.g. `"pressure:northern_drought"` for trace root. Each entry carries its own `world` (normal vs drought) so `world` is not a second parallel schedule. | Satisfies spec's suggested fields without DSL; pressure drives both `world` and `signal/title` from one source. Frozen models keep canonical discipline. Small: one file + ~40 lines of types. | Storing pressure as loose `dict` rejected — unvalidated, not inspectable. Building a generic `Event{weight, duration, modifiers}` registry rejected — overengineering for one arc. Using raw strings (`stage` as free `str`) rejected — typo-prone, no validation. |
| 2 | **Where pressure lives at runtime** | `FiveTurnGame` owns the arc (session-owned, like rivals). Optionally add `pressure_stage: PressureStage` (default `"normal"`) and `pressure_id: str` to `GameState` for inspectability via state, with default so existing `GameState(...)` constructions stay valid. If adding to `GameState` feels like canonical churn, alternative is to expose pressure via `GameState` accessor that derives from `turn` index; recommended is **opt-in field with default** (`pressure_stage: PressureStage = "normal"`), updated each turn from the arc. Inspectability then has three layers: `state.pressure_stage`, `TurnResolution.causal_trace` pressure node, and `FiveTurnGame.current_pressure`. | Makes pressure inspectable after restart/replay without parsing history; keeps `GameState` still frozen and backward compatible (default). | Keeping pressure only in `FiveTurnGame` and not in `GameState` would make `TurnResolution.next_state` lack pressure — harder to assert AC4 from state alone, and future Sections 10/16 persistence would need to infer. Putting pressure only in trace (no state) rejected — trace is per-turn, not current-state query. |
| 3 | **Arc authoring — mapping 5 turns to 5 stages** | Hard-code `PRESSURE_ARC: tuple[PressureState,5]`: <br>0 `normal` {world normal, signal High demand… title Growing Settlement, act 0}, <br>1 `early_dry` {world normal, signal Early dry: weak harvest hints, prices soft on surplus, title Surplus / Early Dry, act 1}, <br>2 `worsening_dry` {world normal, signal Strong warning: dry weather worsens, next harvest threatened, title Warning Signs, act 2}, <br>3 `drought` {world drought, signal Drought cuts output, title Drought, act 3}, <br>4 `aftermath` {world normal, signal Markets adjust to aftermath, title Aftermath, act 4}. <br> Keep 5 turns; early/worsening are both `world=normal` with escalating prose, only the impact turn flips `world=drought`. This satisfies “early → worsening → impact” without changing turn count. | Preserves existing 5-turn contract and supply semantics; only signal text and stage worsen before impact. Keeps tests about 5 decisions valid. | Extending to 6 turns (normal, early, worsening, drought, drought2, aftermath) rejected — would break AC “exactly five decisions” and many tests. Making T2 still pure surplus with no dry hint rejected — would lose one warning, weakening AC1. Making early/worsening also `world=drought` (light drought) rejected — would duplicate impact logic and confuse systemic chain. |
| 4 | **Structured threat for rivals — derive from pressure, not prose** | Replace `_next_world_known_for_turn` ad-hoc with helper `next_world_known_for_turn(idx) -> WorldCondition|None` that returns `"drought"` when `PRESSURE_ARC[idx].stage == "worsening_dry"` (i.e., T3 warns of T4 drought) else `None`. Optionally expose `pressure_stage` in `ObservableContext` so scoring can check `pressure_stage in ("early_dry","worsening_dry")` for graded boost. Keep rivalry boost logic but driven by structured enum, not `signal.contains`. | Keeps “author cause, simulate consequences” — warning is authored stage, not parsed prose. Allows graded early vs worsening boost if desired, without generic DSL. | Parsing `signal_text` for `"dry"`/`"warning"` rejected — brittle, flagged in Section 7 review. Passing full `PressureState` into scoring with arbitrary modifiers rejected — would be DSL creep. |
| 5 | **Trace integration — pressure as causal root** | In `turn.py:resolve_turn`, emit a leading `CausalNode{id="pressure", kind="world", after=stage_hash?, parent_ids=()}` or `id="pressure_stage"` with `reason_code="pressure: northern_drought: worsening_dry"` (parent of `world`). Chain: `pressure_stage → world → farm_output → home_supply → home_price → … → wealth`. Keep `world` node child of pressure; `farm_output` parent is `world`; rest unchanged. Drivers can then reference `pressure_stage` in their `causal_node_ids`. No price node directly parented to pressure. | Guarantees AC2 systemic path is visible in trace; pressure is inspectable root. Minimal: one extra node, fits existing DAG validator (world is allowed root, pressure also allowed as new root kind). | Adding pressure as modifier that directly mutates price node rejected — violates “no direct price hack”. Skipping trace node and keeping pressure implicit rejected — loses inspectability. |
| 6 | **Signal/title ownership** | `TurnSpec` is subsumed by `PressureState` (they carry `signal,title,world`). For backward compat, keep `TurnSpec` as alias or deprecate: define `TURN_SPECS` as derived `tuple(TurnSpec(world=p.world, signal=p.signal, title=p.title) for p in PRESSURE_ARC)` so existing imports (`from prototype import TURN_SPECS`) keep working. New code reads `PRESSURE_ARC`. | Zero churn for tests that import `TURN_SPECS`; single source is `PRESSURE_ARC`. | Deleting `TurnSpec` outright would break half the test suite. Keeping two independent lists (pressure + TurnSpec) rejected — duplicate source of truth. |
| 7 | **No new costs / market math** | Reuse existing `actor.compute_farm_output` for drought effect (no new `world_modifiers` formula). `world_modifiers` field, if added to `PressureState`, is typed as `Mapping[str,int]` but unused for Section 8 (kept optional/empty). Future sections may populate e.g. `{"yield_bps": 6000}` but Section 8 leaves Python formula authoritative. | Honors “Python owns formulas, content supplies parameters” but defers parameterization until Section 15; avoids premature abstraction. | Introducing `world_modifiers: dict[str,Callable]` or executable price lambda rejected — violates Section 15. Adding a `yield_factor_bps` param already now considered but kept optional and not yet consumed, to avoid changing kernel. |

---

## Recommended Approach

Stay additive and keep the kernel as authority:

1. **Domain:** Add `PressureStage` literal + `PressureState` frozen model (and optional `PressureArc` alias) in `backend/app/domain/types.py` (or new `pressure.py` re-exported). Add optional `pressure_stage` (+ `pressure_id`) to `GameState` with defaults to remain backward compatible. Export via `domain/__init__.py`.

2. **Engine:** New `backend/app/engine/pressure.py` (≈40 lines) defining `PRESSURE_ARC: tuple[PressureState,5]` hard-coded with the 5 stages above, helper `pressure_for_turn(idx) -> PressureState`, and `next_world_known_for_idx`. No randomness, pure.

3. **Prototype:** Refactor `backend/app/engine/prototype.py` so `TURN_SPECS` is derived from `PRESSURE_ARC` (or replaced) and `FiveTurnGame` drives progression from `PRESSURE_ARC`. Turn submission reads `pressure = pressure_for_turn(idx)`, passes `pressure.world` to `resolve_turn`, updates `state` with `pressure_stage=pressure.stage`, and builds `ObservableContext` threat from pressure stage (worsening → drought). Keep two-phase rival timing unchanged, now threat-graded by pressure.

4. **Trace:** Extend `backend/app/engine/turn.py` to accept optional pressure context (or read `state.pressure_stage`) and emit the pressure root node, parenting `world`. Keep `_target_price/_bounded_price` and actor calls unchanged. Ensure wealth decomposition still exact.

5. **Rivals/CLI:** No scoring rewrite; only threat source changes from `_next_world_known_for_turn` to `pressure.next_world_known`. `cli.py` displays `state.pressure_stage` or `current_pressure.title/signal`; `StrategicSummary.format()` shows per-turn stage.

All functions remain plain, sync, deterministic.

---

## Work Plan

### 1 — Domain pressure types (no behavior change yet)
- **Surface:** `backend/app/domain/types.py` (or new `pressure.py`) + `backend/app/domain/__init__.py`
- **Do:** Add `PressureStage`, `PressureState{ id, stage, world, signal, title, activation_turn, causal_source_id, world_modifiers? }` frozen, validated. Optionally extend `GameState` with `pressure_stage: PressureStage = "normal"` and `pressure_id: str = "northern_drought"` (defaults). Add `Kind` `"pressure"` to `trace.py` allowed roots if needed.
- **Tests:** `tests/test_pressure_arc.py` (new) — validate stage enum, frozen, negative invalid, arc length 5, stages in order `normal→early_dry→worsening_dry→drought→aftermath`, world only drought on impact, causal_source stable.
- **Depends:** none.

### 2 — Pressure arc + pure helpers
- **Surface:** `backend/app/engine/pressure.py` (new) + `backend/app/engine/__init__.py` re-export if convenient
- **Do:** Hard-code `PRESSURE_ARC` tuple of 5 `PressureState` with truthful signals (ids stable, e.g. `northern_drought:t0 … t4`). Implement `pressure_for_turn(idx)`, `world_for_turn(idx)`, `next_world_known_for_turn(idx)` (worsening→drought). No RNG, no I/O.
- **Tests:** Extend `test_pressure_arc` — determinism (`pressure_for_turn(2).stage == "worsening_dry"`), `next_world_known == "drought"` only on idx 2, idempotent, inspectable `causal_source_id`.
- **Depends:** 1.

### 3 — Prototype refactor to drive from pressure (keep TURN_SPECS compat)
- **Surface:** `backend/app/engine/prototype.py`
- **Do:** Import `PRESSURE_ARC`/`pressure_for_turn`. Derive `TURN_SPECS` from `PRESSURE_ARC` for compat (or define `TURN_SPECS = tuple(TurnSpec(... for p in PRESSURE_ARC))`). Update `default_start_state` to include initial pressure. Change `FiveTurnGame.submit()` to read `pressure = pressure_for_turn(idx)` and use `pressure.world` and `pressure.signal/title`. Replace `_next_world_known_for_turn` calls with pressure-derived helper. Update `_observable_for` to populate `next_world_known` from pressure stage and optionally `pressure_stage` in `ObservableContext`. Keep `state` update with `pressure_stage`.
- **Tests:** Existing `test_five_turn_prototype.py` still passes via derived `TURN_SPECS`; new assertions — `game.state.pressure_stage` progression, `current_signal` matches arc, `current_spec` still mirrors pressure.
- **Depends:** 2.

### 4 — Trace integration (pressure → world → production chain)
- **Surface:** `backend/app/engine/turn.py` + `backend/app/domain/trace.py` (only if Kind allowlist needs `"pressure"`)
- **Do:** Emit leading pressure node (kind `pressure` or `world`) with `reason_code = f"pressure:{pressure.id}:{pressure.stage}"`, make `world` node its child. Keep all other nodes parented as before. Ensure `CausalTrace` validator accepts pressure as allowed root (add case like `kind=="pressure"` or `id=="pressure_stage"` with zero-delta handling similar to capacity). No price mutation.
- **Tests:** `tests/test_causal_trace.py` — assert chain `pressure_stage → world → farm_output → home_supply → home_price → … → wealth` exists; drought path includes `drought_reduced_yield`; no node directly links pressure to price bypassing supply; drivers still ≤3.
- **Depends:** 3.

### 5 — Rivals & settlement keep structured threat (no scoring rewrite)
- **Surface:** `backend/app/engine/rivals.py` + `prototype.py: _observable_for`
- **Do:** Confirm `ObservableContext.next_world_known` now sourced from pressure stage (not signal parse). Optionally expose `pressure_stage` on `ObservableContext` for future graded boost (early vs worsening) but keep current boost tiers. No change to `score_rival_command` constants — keep integer/bps.
- **Tests:** `tests/test_deterministic_rivals.py` — behavioral fingerprint still holds across early/worsening/drought contexts; threat boost now triggers on `stage==worsening_dry` not string check (add probe for early_dry vs worsening_dry).
- **Depends:** 3.

### 6 — CLI + summary polish
- **Surface:** `backend/app/cli.py`, `backend/app/engine/prototype.py:StrategicSummary`
- **Do:** Display current pressure stage/title/signal per turn header (e.g. `PRESSURE normal → early dry → worsening → DROUGHT → aftermath`). In `StrategicSummary.format()`, append stage per turn. Ensure outcome reveal still shows WHY drivers and rival headlines.
- **Depends:** 3.

### 7 — New Section 8 acceptance tests + harness sanity
- **Surface:** `backend/tests/test_pressure_arc.py` (or `test_pressure_driven_arc.py`) plus extensions to `test_five_turn_prototype`
- **Do:** AC1: before T4, `warning` signal + `pressure_stage in ("early_dry","worsening_dry")` visible. AC2: assert price trace parents do not include direct pressure price hack; farm_output under drought < normal for same capacity; supply reflects farm_output. AC3: run at least 3 policies (hold×5 vs build_granary×2+buy vs expand_farm×5) with same seed → diverging `final_wealth` / `price_value_effect` / inventory; drought-rewarding-preparation holds (storage-heavy holds more value on drought). AC4: two runs same seed+choices byte-equal (state, rival_history, trace). AC5: count pressure types — only 5 stages, arc hard-coded, no JSON loader, no generic sampler.
- **Depends:** 4,5.

---

## Validation Plan

```bash
# Must pass (Section 1 gates still apply)
uv sync --project backend
make test              # pytest -v -> expect ~120 passed (112 + ~8 new pressure tests)
make lint              # ruff check backend  -> All checks passed
make type              # pyright -> 0 errors, 0 warnings
make format-check      # ruff format --check backend -> formatted

# Targeted checks
uv run --project backend pytest -v backend/tests/test_pressure_arc.py
uv run --project backend pytest -v backend/tests/test_five_turn_prototype.py backend/tests/test_deterministic_rivals.py backend/tests/test_causal_trace.py

# CLI smoke (deterministic arc visible)
uv run --project backend python -m app.engine.cli --help
uv run --project backend python -m app.engine.cli --choices "hold,hold,hold,hold,hold" --seed seed-8-001
uv run --project backend python -m app.engine.cli --choices "build_granary,build_granary,buy_grain,hold,ship_grain" --seed seed-8-001 --verbose

# Quick harness sanity (AC3 divergence)
uv run --project backend python -c "
from app.engine.prototype import FiveTurnGame
from app.domain.types import PlayerCommand as C
policies = {
 'hold': [C(type='hold')]*5,
 'farm': [C(type='expand_farm')]*5,
 'store': [C(type='build_granary'),C(type='build_granary'),C(type='buy_grain',quantity=10),C(type='hold'),C(type='hold')],
}
for name, choices in policies.items():
    g=FiveTurnGame(seed='seed-8-001'); s=g.run(choices); print(name, s.final_wealth, s.cash_low, g.state.market.current_price)
"
```

**Expected evidence:**

- CLI per-turn headers show stages `normal → early_dry → worsening_dry → DROUGHT → aftermath` and signals escalate before impact; `6 MONTHS LATER` still shows wealth/inventory/price and `WHY?` drivers plus `MIRA`/`DARAN` headlines.
- Trace dump (verbose) includes chain `pressure_stage:northern_drought:worsening_dry → world:drought → farm_output:drought_reduced_yield → home_supply → home_price → … → wealth`.
- Same seed+choices second run byte-equal (`final_wealth`, `rival_history`, trace).
- Three policies produce at least two distinct `final_wealth` values with storage-heavy outperforming farm-heavy on wealth retained through drought (preparation reward) without one policy dominating all seeds.

---

## Risks / Rollback

- **Risk:** Changing `TURN_SPECS` signals (T2 surplus → early dry) breaks exact-string tests (e.g. `assert signal == "Repeated harvests have left grain abundant…"`). **Mitigation:** Derive `TURN_SPECS` from `PRESSURE_ARC` and update string assertions to stage-based checks (`stage in ("early_dry","worsening_dry")` substring) rather than exact match; keep a `SUPPLY_WEAK` hint inside early_dry prose so surplus story remains truthful.
- **Risk:** Adding `pressure_stage` to `GameState` touches every `GameState(...)` construction. **Mitigation:** Default value `"normal"` so call sites without the field keep working; pydantic frozen defaults are backward compatible.
- **Risk:** Trace DAG validator rejects new pressure root node. **Mitigation:** Whitelist `kind=="pressure"` or `id=="pressure_stage"` as allowed root in `trace.py: _validate_dag`, mirroring existing capacity/route exceptions; keep delta 0 allowed.
- **Risk:** Rivals that previously keyed on `next_world_known=="drought"` only on idx 2 still work, but graded early vs worsening boost may alter fingerprint tests. **Mitigation:** Keep existing boost tiers unchanged; new `early_dry` stage adds no extra boost initially, only `worsening_dry` triggers drought threat, preserving determinism.
- **Rollback:** Revert `prototype.py` to re-introduce hard-coded `TURN_SPECS` and ignore pressure module; `GameState` defaults ensure old snapshots load.

---

## Open Questions

- None blocking. Two implementation choices left to confirm during review and then locked in code:
  1. **GameState field vs pure derivation:** Plan recommends `pressure_stage` with default for inspectability; if reviewer prefers no GameState churn, we can keep pressure purely in `FiveTurnGame`+trace and expose via `game.current_pressure` helper. Decision is trivially reversible.
  2. **Signal prose for T2 early dry:** Keep surplus-weak narrative but tint with early dry hint (“Harvests left grain abundant — though dry hints appear”) to satisfy both surplus truth and early warning, or keep T2 as pure surplus and let T3 carry both early+worsening. Either satisfies AC1; plan proposes the tinted wording to give two escalating warnings without inventing a 6th turn.

