# Section 8 — Pressure-Driven Event Arc — Plan (Rev 4 — incorporates R1–R8 + grill Q1–Q7 + review round 2 F1–F5)

**Date:** 2026-08-10 (revised after R1, grill, and review round 2 F1–F5)
**Branch:** `section/8-pressure-driven-event-arc` (from `origin/main` at `53fb3e6`)
**Spec Authority:** `BUILD_SPEC.md` Section 8 (Status: NOT STARTED) + global §§10–16 + `DECISIONS.md` 001–011 + `STATE.md` §7
**Related:** `backend/app/domain/types.py`, `backend/app/domain/pressure.py` (new), `backend/app/domain/trace.py`, `backend/app/engine/pressure.py` (new), `backend/app/engine/turn.py`, `backend/app/engine/actor.py`, `backend/app/engine/prototype.py`, `backend/app/engine/rivals.py`, `backend/app/cli.py`, `backend/app/engine/demo.py`, `backend/tests/test_five_turn_prototype.py`, `backend/tests/test_deterministic_rivals.py`
**Review input:** `docs/plans/2026-08-10-section-8-review-round-1.md` (R1–R8) + grill Q1–Q7 + `docs/plans/2026-08-10-section-8-review-round-2.md` (F1–F5)

---

## Goal

Replace the current hard-coded `TURN_SPECS` + single-value `next_world_known` warning with a small, coherent, deterministic world-pressure system that drives one 5-turn arc:

```
normal → early_dry → worsening_dry → drought → aftermath
```

Keep impact **systemic** (drought reduces farm output → supply signal → price pressure → price, never `price *= 1.4`), keep the 5-turn headless game intact, and keep the system trivially inspectable without introducing a generic 30-event DSL, content loader, or new goods/rivals.

---

## Success Criteria (maps to Section 8 AC + global rules)

1. **At least one useful warning before impact (AC1).** Turns 2–3 surface early (`early_dry`) and worsening (`worsening_dry`) dry signals that a prepared player can act on. Usefulness is proven operationally by the single AC1+AC3 instrument below — two histories identical through T1 (normal) diverging only during warning stages (T2–T3), with a pre-condition proving they face an *identical* T4 market shock, yet produce different T4 outcomes.

2. **Drought stays systemic (AC2).** Drought changes `farm_output` via `actor.compute_farm_output` (40% reduction), then `home_supply` (`signal_next = max(0, signal+farm_output-demand)`), then `home_price` via `_target_price/_bounded_price`. No direct price mutation. Proved by trace parent chain `pressure_stage → world → farm_output → supply → price`.

3. **Different preparation → different result (AC3).** Same authored drought + same seed, different legal warning-stage preparation → materially different T4 drought exposure. Proven by the same threshold-free instrument as AC1: identical T4 market conditions yet different `price_value_effect` / `wealth_delta` / inventory. No multi-seed sweep, no win-rate (Section 9).

4. **Deterministic & inspectable (AC4).** Same `run_seed + ruleset_version + choices[5]` → identical pressure progression, signals, world conditions, prices, rival headlines, and trace. Inspectable via `pressure_for_turn(idx)` / `game.current_pressure` (None when complete) / trace pressure node. No new canonical field in `GameState`.

5. **Small, no DSL (AC5).** One hard-coded 5-element `PRESSURE_ARC`, one enum + one frozen model (`PressureStage` + `PressureState` in `domain/pressure.py`), one pure helper module `engine/pressure.py`. Structural smallness checks (no JSON loader, no sampler) — not a line-count threshold.

6. **Housekeeping preserved.** `engine`+`domain` pure, integers only, deterministic RNG, drivers ≤3, rivals deterministic via integer scoring + structured threat. `trace.py` validator not loosened. 112 existing tests remain green (none relaxed; only `resolve_turn` call sites mechanically updated to pass `PressureState`).

---

## Context And Current Facts (verified against code)

- **Spec §8:** One pressure arc with *possible* fields `id, stage, signal_text, world_modifiers, activation_turn, causal_source_id`; authored turns allowed; must stay systemic; no generic framework. `world_modifiers` is optional — correctly omitted per R2/F2.

- **Domain `backend/app/domain/types.py`:** `GameState{turn, run_seed, ruleset_version, player, market:Home, river_market, route}`; `WorldCondition = Literal["normal","drought"]`; no pressure field yet.

- **Trace `backend/app/domain/trace.py:47,102,149-165,170-173`:** `CausalNode.kind: str`, `allowed_empty_roots = {"world","command"}` (102), must-have-parents list 149–165 excludes `"pressure"`, fallback at 170–173 admits `delta is None` root. A pressure node `kind="pressure", delta=None, parent_ids=()` validates as-is. No validator change needed (R3). **Constraint for this turn:** do not modify `_validate_dag`.

- **Actor `backend/app/engine/actor.py:14-21,52-65`:** `YIELD_PER_CAPACITY=10`, `DROUGHT_YIELD_REDUCTION_BPS=4000`, `EXPAND_FARM_COST=500` (+10 cap), `BUILD_GRANARY_COST=300` (+50 cap), `ROUTE_ESTABLISH_COST=400`, `cost_for_quantity = qty*price//1000`. `compute_farm_output(farm_capacity, world)` returns `farm_capacity*10` or `*6` under drought. `home_supply` formula in `turn.py` is `signal_next = max(0, signal+farm_output-demand)` — verified that only `farm_output` (hence `farm_capacity` via `expand_farm`) drives supply; `buy_grain`/`build_granary` do not (F1).

- **Prototype `backend/app/engine/prototype.py`:** `FiveTurnGame` owns `state + history[5] + rivals`; `TURN_SPECS` 5 signals; `current_spec()` returns `None` when `is_complete`; `default_start_state` cash 1000, grain 20, farm 10, storage 200, prices 5000/5200. `_next_world_known_for_turn(2)=="drought"` only. `submit` currently calls `resolve_turn(state, command, spec.world, ctx)`.

- **Turn `backend/app/engine/turn.py:122`:** Current `resolve_turn(state, command, world, rng_context)` — will become `resolve_turn(state, command, pressure: PressureState, rng_context)` deriving `world = pressure.world`.

- **CLI `backend/app/cli.py`:** Entry point is `backend/app/cli.py` (not `backend/app/engine/cli.py`). Invocation `uv run --project backend python backend/app/cli.py ...`.

- **Tests:** 112 passing; citations `test_five_turn_prototype.py:153` and `:368` verified.

---

## Verification of Review Claims

**Round 1 (R1–R8):** All four cited locations checked directly — `trace.py:149-165/170-173`, `test_five_turn_prototype.py:153` and `:368`, `backend/app/cli.py` ls — all correct. No claim wrong.

**Round 2 (F1–F5):**

- **F1 mechanism confound:** Verified. `turn.py` supply: `signal_next = max(0, signal+farm_output-demand)`; `farm_output` from `actor.compute_farm_output(farm_capacity, world)`; only `expand_farm` changes `farm_capacity`. Therefore `expand_farm` histories enter T4 with different supply/price than non-farm histories. Computed: `prep=[hold,granary,buy]` vs `unprep=[hold,farm,farm]` gave T4 supply `100 vs 520`, price_value `+130 vs -18` (supply-driven price divergence). **Claim correct — instrument must avoid `expand_farm` in either arm.**

- **F1 equality proof:** Also verified that `buy_grain`/`build_granary` do not feed `home_supply` formula — so histories avoiding `expand_farm` have provably identical T4 market. Computed for the fixed histories `prep=[hold,granary,buy:20,hold,hold]` vs `unprep=[hold,hold,hold,hold,hold]` on `seed-8-useful`: T4 `farm_output 60==60`, `supply 100==100`, `price 4750==4750`, yet `price_value_effect 130 vs 104` (inventory 250 vs 200) — equality holds, inequality holds. **F1 fix validated.**

- **F2 `stage`/`world` combinatoric:** Verified `PressureState` without validator indeed accepts `early_dry`+`drought` (Pydantic would not reject without custom validator). **Claim correct.**

- **F3 `causal_source_id` vs trace recompute:** Verified Rev 3 Decision 1 had `causal_source_id` default formula and Decision 5 recomputed same formula in `turn.py`. **Claim correct — single source violation.**

- **F4 file location hedging:** Rev 3 left `"types.py (or pressure.py)"`. **Claim correct — not decision-complete.**

- **F5 closeout sequence:** Rev 3 listed gates but not the repo's required closeout steps (STATE.md, DECISIONS.md, BUILD_SPEC status, graphify). **Claim correct.**

---

## Key Decisions (all settled — no open choices remain)

| # | Decision | Choice (revised per R1–R8 + Q1–Q7 + F1–F5) | Why | Alternative Rejected |
|---|----------|---------------------------------------------|-----|----------------------|
| 1 | **Pressure representation — where & how small (R1,R2,F2,F4)** | Introduce `PressureStage = Literal["normal","early_dry","worsening_dry","drought","aftermath"]` and frozen `PressureState{ pressure_id: str, stage: PressureStage, activation_turn: int, world: WorldCondition, signal: str, title: str, causal_source_id: str }` — **exactly 7 fields, no `world_modifiers`**. Put the enum+model in **`backend/app/domain/pressure.py`**, re-exported via `domain/__init__.py` (F4 — distinct domain concept, avoids `types.py` catch-all). `pressure_id` e.g. `"northern_drought"` stable; `causal_source_id` defaults to `f"pressure:{pressure_id}:{stage}"` (via `default_factory` or validator) and is the single source for the trace node (F3). Add **model validator** enforcing the biconditional (F2): `stage=="drought" <=> world=="drought"` and every other stage => `world=="normal"`. Validate `activation_turn == index in PRESSURE_ARC`. | Satisfies spec without DSL; 7-field exactness structurally tested; biconditional prevents the invalid `early_dry+drought` state R1 meant to eliminate (now inside one object, F2). File location settled (F4). | Generic Event registry rejected; `world_modifiers` rejected; `GameState.pressure_stage` rejected; `types.py` catch-all location rejected (F4); stage/world unconstrained rejected (F2). |
| 2 | **Single source of truth for `world` (R1,F2)** | Change `resolve_turn` signature to `resolve_turn(state, command, pressure: PressureState, rng_context) -> TurnResolution` and derive `world = pressure.world` internally. `FiveTurnGame.submit` calls `pressure = pressure_for_turn(idx)` then `resolve_turn(state, command, pressure, ctx)`. The `PressureState` validator (Decision 1) guarantees `pressure.world` is already consistent with `pressure.stage`. | Eliminates three-representation hazard and the F2 intra-object hazard. One fact, one place. | Keeping bare `world` arg alongside pressure rejected. |
| 3 | **Arc authoring — mapping 5 turns to 5 stages (R4,Q1,Q2,F1)** | Hard-code `PRESSURE_ARC: tuple[PressureState,5]`: <br>0 `normal` {world normal, signal "The growing settlement keeps food demand high.", title "A Growing Settlement", activation 0}, <br>1 `early_dry` {world normal, signal "Grain remains abundant, but the rains have begun to fail.", title "Surplus" (unchanged), activation 1}, <br>2 `worsening_dry` {world normal, signal "The dry spell persists. Farmers warn the next harvest is at risk.", title "Warning Signs", activation 2}, <br>3 `drought` {world drought, signal "Drought cuts farm output — regional supply tightens.", title "Drought", activation 3}, <br>4 `aftermath` {world normal, signal "Markets adjust to the drought's aftermath.", title "Aftermath", activation 4}. <br>T2/T3 prose is observational about **rainfall**, not output. Only T4 flips `world=drought`. | Truthful prose; two escalating warnings; title preservation keeps `test_turn_specs_length_and_titles:368` green. Histories that avoid `expand_farm` (F1) now provably share T4 market. | 6 turns, light-drought early stages, "weak harvest hints" wording all rejected. |
| 4 | **Structured threat for rivals (keep-as-is + R1)** | `next_world_known_for_turn(idx)` returns `"drought"` iff `PRESSURE_ARC[idx].stage == "worsening_dry"` (T3 only), else `None`. Implemented in `pressure.py`. `FiveTurnGame._observable_for` builds `ObservableContext` from that helper and `pressure.world`. No prose parsing. | Warning is authored stage, not parsed prose. | Parsing signal text rejected; graded early_dry boost rejected. |
| 5 | **Trace integration — pressure as causal root (R3,F3)** | In `turn.py:resolve_turn`, emit leading `CausalNode(id="pressure_stage", kind="pressure", label=<stage title-derived>, before=None, after=None, delta=None, reason_code=pressure.causal_source_id, parent_ids=())` — **read directly from the field, do not recompute** `f"pressure:{id}:{stage}"` (F3). Then `world` node `parent_ids=("pressure_stage",)`. Chain: `pressure_stage → world → farm_output → home_supply → home_price → … → wealth`. No hash, no numeric delta. Do not modify `trace.py` `_validate_dag`. | Guarantees AC2 systemic path; inspectable root; validates via existing fallback; single source for `causal_source_id` (F3). | Hash/validator loosening, recomputed format string, direct pressure→price edge all rejected. |
| 6 | **Signal/title ownership** | `TurnSpec` subsumed by `PressureState`. Keep `TurnSpec` alias: `TURN_SPECS = tuple(TurnSpec(world=p.world, signal=p.signal, title=p.title) for p in PRESSURE_ARC)` in `prototype.py`. Single source is `PRESSURE_ARC`. | Zero churn for `TURN_SPECS` imports. | Deleting `TurnSpec` or keeping two lists rejected. |
| 7 | **Current-pressure accessor when complete (Q3, already resolved)** | `game.current_pressure: PressureState \| None` — returns `None` when `is_complete`, else `pressure_for_turn(len(history))`. `pressure_for_turn` raises on out-of-range idx; callers needing aftermath pressure use `PRESSURE_ARC[4]`. | Mirrors `current_spec()` contract; no IndexError on completed game. | Returning `PRESSURE_ARC[4]` when complete rejected. |
| 8 | **No new costs / market math** | Reuse `actor.compute_farm_output`; Python formula stays authoritative. | Deferred to Section 15. | Parameterized modifiers rejected. |

---

## Recommended Approach

Stay additive and keep the kernel as authority. Implement in dependency order so each step is testable:

1. **Domain:** New `backend/app/domain/pressure.py` with `PressureStage` + `PressureState` (7 fields, frozen, validator for stage/world biconditional per F2 and `causal_source_id` default). Re-export via `domain/__init__.py`.

2. **Engine:** New `backend/app/engine/pressure.py` defining `PRESSURE_ARC: tuple[PressureState,5]` hard-coded with the 5 stages above (exact prose per R4, `activation_turn == index`), helper `pressure_for_turn(idx) -> PressureState`, and `next_world_known_for_turn(idx)`. No RNG, pure, validated.

3. **Prototype:** Refactor `backend/app/engine/prototype.py` so `TURN_SPECS` is derived from `PRESSURE_ARC` and `FiveTurnGame` drives progression from `PRESSURE_ARC`. Change `submit()` to `pressure = pressure_for_turn(idx)` → `resolve_turn(state, command, pressure, ctx)`. Build `ObservableContext` threat from `pressure.stage == "worsening_dry"` via `next_world_known_for_turn`. Remove `_next_world_known_for_turn`. Add `current_pressure` per Q3 contract (None when complete).

4. **Turn kernel:** Extend `backend/app/engine/turn.py` to accept `PressureState` (derive `world`), emit the `pressure_stage` root node per Decision 5 using `pressure.causal_source_id` directly (F3), parent `world` to it. Keep `_target_price/_bounded_price` and actor calls unchanged. Update `backend/app/engine/demo.py` call site to construct a `PressureState` (or pass through `pressure_for_turn`) instead of bare `world`.

5. **Rivals/CLI:** No scoring rewrite; only threat source changes. `backend/app/cli.py` displays `game.current_pressure.title/signal/stage` per turn header; `StrategicSummary.format()` appends stage per turn. Keep two-phase rival timing unchanged.

All functions remain plain, sync, deterministic.

---

## Work Plan

### 1 — Domain pressure types (no behavior change yet)
- **Surface:** `backend/app/domain/pressure.py` (new) + `backend/app/domain/__init__.py` (+ `backend/app/domain/types.py` unchanged)
- **Do:** Add `PressureStage` literal and `PressureState` frozen model with exactly `pressure_id, stage, activation_turn, world, signal, title, causal_source_id`; `activation_turn` in 0..4; `causal_source_id` default `f"pressure:{pressure_id}:{stage}"` (computed in validator so explicit overrides are forced to match, F3). Add model validator (F2): `stage=="drought" <=> world=="drought"` and every other stage => `world=="normal"`; reject otherwise.
- **Tests (new, `backend/tests/test_pressure_arc.py`):** Enum validation, frozen, `activation_turn` matches index, 5 stages in order `normal→early_dry→worsening_dry→drought→aftermath`, world only `drought` on impact, `causal_source_id` stable (= `f"pressure:{id}:{stage}"`), invalid stage rejected. **F2 regression:** assert `PressureState` construction raises for at least `early_dry`+`drought`, `worsening_dry`+`drought`, `drought`+`normal`. Structural smallness sub-checks: field count ==7, no `world_modifiers` attr.
- **Depends:** none.

### 2 — Pressure arc + pure helpers
- **Surface:** `backend/app/engine/pressure.py` (new) + `backend/app/engine/__init__.py` re-export if convenient
- **Do:** Hard-code `PRESSURE_ARC` tuple of 5 `PressureState` with truthful signals per R4 (ids stable `"northern_drought"`). Implement `pressure_for_turn(idx)`, `world_for_turn(idx)`, `next_world_known_for_turn(idx)` (worsening→drought only). Validate at import that `p.activation_turn == index` for all p. No RNG, no I/O.
- **Tests (extend `test_pressure_arc`):** Determinism (`pressure_for_turn(2).stage == "worsening_dry"`), `next_world_known == "drought"` only on idx 2, idempotent, `pressure_id` stable, out-of-range raises, `current_pressure` contract when complete.
- **Depends:** 1.

### 3 — Prototype refactor to drive from pressure (keep TURN_SPECS compat)
- **Surface:** `backend/app/engine/prototype.py`
- **Do:** Import `PRESSURE_ARC`/`pressure_for_turn`/`next_world_known_for_turn` from `engine/pressure.py`. Derive `TURN_SPECS` from `PRESSURE_ARC` for compat. Remove `_next_world_known_for_turn`. Change `submit()` to `pressure = pressure_for_turn(idx)` and pass `pressure` to `resolve_turn`. Update `_observable_for` to populate `next_world_known` from `next_world_known_for_turn(idx)`. Add `current_pressure` property per Q3 (`None` when complete).
- **Tests:** Existing `test_five_turn_prototype.py` still passes via derived `TURN_SPECS`; new assertions — `game.current_pressure.stage` progression `normal→early_dry→worsening_dry→drought→aftermath`, `game.current_pressure is None` after 5 submits, `current_signal` matches arc, `current_spec` still mirrors pressure.
- **Depends:** 2.

### 4 — Turn kernel signature + trace integration (pressure → world chain)
- **Surface:** `backend/app/engine/turn.py` (+ `backend/app/engine/demo.py` call site; **no change** to `backend/app/domain/trace.py` per R3)
- **Do:** Change `resolve_turn(state, command, pressure: PressureState, rng_context)` — derive `world = pressure.world` at top. Emit leading `pressure_stage` node with `kind="pressure"`, `delta=None`, `reason_code=pressure.causal_source_id` (direct read, F3), `label` derived from `pressure.title`. Make `world` node `parent_ids=("pressure_stage",)`. Keep all other nodes parented as before. Update docstring and `TURN_ORDER` comment to `pressure_stage -> world -> production -> ...` if documented.
- **Tests:** `backend/tests/test_causal_trace.py` — assert chain `pressure_stage → world → farm_output → home_supply → home_price → … → wealth` exists for all turns; drought path includes `drought_reduced_yield`; **no edge from `pressure_stage` directly to any price node** (price reachable only via `farm_output`/`supply`); `reason_code` on `pressure_stage` equals `pressure.causal_source_id` (F3); drivers still ≤3; validator not modified (assert file text of `trace.py` does not contain `pressure` in `allowed_empty_roots`).
- **Depends:** 3.

### 5 — Rivals & settlement keep structured threat (no scoring rewrite)
- **Surface:** `backend/app/engine/rivals.py` + `prototype.py: _observable_for`
- **Do:** Confirm `ObservableContext.next_world_known` now sourced from `next_world_known_for_turn` (pressure stage) — same observable value as before (drought only on T3). Keep integer/bps scoring constants unchanged.
- **Tests:** `backend/tests/test_deterministic_rivals.py` — behavioral fingerprint still holds across early/worsening/drought contexts; early_dry (T2) does **not** trigger drought threat, worsening_dry (T3) **does**; probe `pressure_for_turn(1).stage=="early_dry"` → `next_world_known is None` vs `pressure_for_turn(2).stage=="worsening_dry"` → `"drought"`.
- **Depends:** 3.

### 6 — CLI + summary polish
- **Surface:** `backend/app/cli.py`, `backend/app/engine/prototype.py:StrategicSummary`
- **Do:** Display current pressure stage/title/signal per turn header (e.g. `PRESSURE normal → early dry → worsening → DROUGHT → aftermath`) and include stage in non-interactive run output. In `StrategicSummary.format()`, append stage per turn (`T2 Surplus [early_dry]`). Ensure outcome reveal still shows `WHY?` drivers and rival headlines. `current_pressure is None` prints `"Complete"` / `""` for signal/title after game over (mirrors `current_spec`).
- **Depends:** 3.

### 7 — New Section 8 acceptance tests (exact specification per R5/R6 + Q1/Q2/Q5 + F1)
- **Surface:** `backend/tests/test_pressure_arc.py` (new file; **no existing test assertions relaxed**) — note F2 regressions now in Work Plan 1 as well
- **Do:** Implement exactly the tests enumerated in the Validation Plan below. They prove AC1+AC3 via the mechanism-isolated, warning-isolated instrument (F1), AC2 systemic chain, AC4 determinism/inspectability (including `current_pressure is None` when complete), and AC5 structural smallness.
- **Depends:** 4, 5.

---

## Validation Plan

```bash
# Must pass (Section 1 gates still apply)
uv sync --project backend
make test              # = uv run --project backend pytest -v  → ~120 passed (112 + ~8 new pressure tests)
make lint              # = ruff check backend  → All checks passed
make type              # = pyright  → 0 errors, 0 warnings
make format-check      # = ruff format --check backend  → formatted (count increments by new files)

# Targeted checks
uv run --project backend pytest -v backend/tests/test_pressure_arc.py
uv run --project backend pytest -v backend/tests/test_five_turn_prototype.py backend/tests/test_deterministic_rivals.py backend/tests/test_causal_trace.py

# Signal/title preservation guard (must stay green)
grep -n abundant backend/tests/test_five_turn_prototype.py   # expect "abundant" in T2 signal assertion
grep -n '"Surplus"' backend/tests/test_five_turn_prototype.py  # expect title edge

# CLI smoke — use the real path backend/app/cli.py (R7), and a policy that actually ships (R7)
uv run --project backend python backend/app/cli.py --help
uv run --project backend python backend/app/cli.py --choices "hold,hold,hold,hold,hold" --seed seed-8-001
uv run --project backend python backend/app/cli.py --choices "build_granary,secure_route,buy_grain,hold,ship_grain" --seed seed-8-001 --verbose
uv run --project backend python backend/app/cli.py --choices "hold,build_granary,buy_grain,hold,hold" --seed seed-8-001 --verbose

# Proof of F1 isolation — must show equality + inequality on the SAME seed
uv run --project backend python - << 'PY'
import sys
sys.path.insert(0, 'backend')
from app.engine.prototype import FiveTurnGame
from app.domain.types import PlayerCommand as C
# Mechanism-isolated instrument: neither history calls expand_farm, so T4 market is provably identical
prep   = [C(type='hold'), C(type='build_granary'), C(type='buy_grain', quantity=20), C(type='hold'), C(type='hold')]
unprep = [C(type='hold'), C(type='hold'),          C(type='hold'),                  C(type='hold'), C(type='hold')]
for name, choices in [('prep', prep), ('unprep', unprep)]:
    g=FiveTurnGame(seed='seed-8-useful')
    g.run(choices)
    t4 = g.history[3]
    print(name, 'supply', t4.next_state.market.supply, 'price', t4.next_state.market.current_price,
          'price_value', next(n.delta for n in t4.causal_trace.nodes if n.id=='price_value_effect'),
          'inv', t4.next_state.player.inventory.grain, 'wealth', t4.player_outcome.wealth_delta)
PY
# Expected (verified): both supply 100, price 4750 (equal), yet price_value 130 vs 104, inv 250 vs 200, wealth 130 vs 104 (different)

# Closeout sequence (F5) — run after gates green, before flipping BUILD_SPEC status
# 1. gates above green
# 2. graphify update .; git diff --stat / git status (commit regenerated tracked artifacts if changed)
# 3. sync STATE.md to actual HEAD (exact test count, new domain/pressure.py + engine/pressure.py, current_pressure contract, real gate output — not estimates)
# 4. add DECISIONS.md entry (next sequential number) recording turn-derived/session-authored pressure (R1/F2)
# 5. flip BUILD_SPEC.md Section 8 Status to COMPLETE only after 1–4 green
# 6. commit + push; stop (do not begin Section 9)
```

### Exact new/changed tests (what each proves)

No existing assertions are edited or relaxed. All new tests live in `backend/tests/test_pressure_arc.py` (plus one extension in `test_causal_trace.py` and one probe in `test_deterministic_rivals.py`).

| Test | File | What it proves | How it isolates pressure (grill+F1 hardened) |
|------|------|----------------|-----------------------------------------------|
| `test_pressure_arc_is_five_stages_in_order` | `test_pressure_arc.py` | Arc is exactly 5 stages, order `normal→early_dry→worsening_dry→drought→aftermath`, `activation_turn == index`, only `drought` stage has `world=="drought"` | Direct assertion on `PRESSURE_ARC` — no DSL, no `world_modifiers` field exists |
| `test_pressure_signals_observational_not_output` | `test_pressure_arc.py` | T2/T3 prose describes rainfall, not harvest output; production in T2/T3 is still normal | Checks `PRESSURE_ARC[1].signal == "Grain remains abundant, but the rains have begun to fail."` and `PRESSURE_ARC[2].signal == "The dry spell persists. Farmers warn the next harvest is at risk."`; also asserts `world=="normal"` for both |
| `test_pressure_stage_world_validator` (**F2**) | `test_pressure_arc.py` | `PressureState` biconditional is enforced | Asserts `PressureState` construction raises for at least `early_dry`+`drought`, `worsening_dry`+`drought`, `drought`+`normal` |
| `test_warning_is_useful_preparation_changes_drought_outcome` (**AC1+AC3, R5/R6, Q1/Q2/Q5, F1**) | `test_pressure_arc.py` | Warning is **useful** — acting on it during T2–T3 changes the T4 drought consequence, isolating both timing (shared T1, diverge only at warnings) and mechanism (identical T4 market) | Same seed `seed-8-useful`, **mechanism + warning-isolated** histories sharing T1 `hold` and avoiding `expand_farm` in either arm: <br>• Prepared: `[hold, build_granary, buy_grain:20, hold, hold]` <br>• Unprepared: `[hold, hold, hold, hold, hold]` (literal no-response) <br>Pre-condition affordability: every `TurnResolution` `command` node `reason_code` is success (no `insufficient_*`/`no_route_access`). <br>**Pre-condition equality (F1):** `prep_T4.next_state.market.supply == unprep_T4.next_state.market.supply` (100==100), `prep_T4.next_state.market.current_price == unprep_T4.next_state.market.current_price` (4750==4750), and `farm_output` after equal (60==60) — proves identical market shock. <br>Post-condition (threshold-free, Q5): `prep_T4.price_value_effect != unprep_T4.price_value_effect` (130 vs 104) and at least one of `wealth_delta`/`inventory` differs (wealth 130 vs 104, inventory 250 vs 200, both differing). Computed on `seed-8-useful` — cited as evidence, not gating threshold beyond inequality. **Does not** assert which final wealth wins; no multi-seed sweep. |
| `test_drought_still_systemic_via_production_and_supply` (**AC2**) | `test_pressure_arc.py` | Drought reaches price only through production→supply→price, no direct price hack | For same state/capacity, `pressure=drought` farm_output < `pressure=normal` farm_output via `compute_farm_output`; trace for T4 has `pressure_stage` → `world` → `farm_output` → `supply` → `price` chain; **assert no edge `(pressure_stage, price)` or `(pressure_stage, home_price)` exists** — price parents must include `supply`/`farm_output`; also assert `pressure_stage` node `reason_code == pressure.causal_source_id` (F3) |
| `test_pressure_chain_determinism_and_inspectability` (**AC4, Q3**) | `test_pressure_arc.py` | Arc is deterministic and inspectable without DB; `current_pressure` contract correct | Same `seed+choices[5]` twice → byte-equal `state`, `rival_history`, trace; `pressure_for_turn(state.turn)` and `game.current_pressure` match `PRESSURE_ARC[turn]` when `not is_complete`; **`game.current_pressure is None` when `is_complete`** (Q3); trace each turn contains `pressure_stage` node with `reason_code == pressure.causal_source_id` (F3); `pressure_for_turn(5)` raises |
| `test_no_generic_dsl_smallness_structural` (**AC5, Q4, Q6**) | `test_pressure_arc.py` | System is small, no generic framework — structurally, not by line count | `len(PRESSURE_ARC)==5`, `PressureState.model_fields` has exactly 7 keys (no `world_modifiers`), `open("backend/app/domain/pressure.py"/"backend/app/engine/pressure.py").read()` contains no `"json"` / `"import random"` / `"weighted"` / `"sampler"`, imports are only `typing`/`pydantic`/`domain/types`; no weighted sampler |
| `test_pressure_to_world_is_only_via_stage` | `test_causal_trace.py` (extension) | Validates causal topology invariant | Already-covers `pressure_stage` → `world` edge; fail if any price node's `parent_ids` contains `pressure_stage` directly |
| `test_threat_only_on_worsening_not_early` | `test_deterministic_rivals.py` (probe) | Structured threat is stage-derived, graded correctly | `next_world_known_for_turn(1) is None` (early_dry does not threaten), `next_world_known_for_turn(2) == "drought"` (worsening does) — proves prose not parsed |
| `test_histories_fully_affordable` (sub-assertion of AC1+AC3 test, Q2) | `test_pressure_arc.py` | Guards AC1+AC3 instrument against clamped no-ops | For both histories, every turn's `command` node `reason_code` ∉ `{"insufficient_cash*","insufficient_storage","no_route_access"}` and `quantity` deltas equal requested. If any clamped, test fails on pre-condition. |

**Recomputed evidence for the new instrument (replacing stale +130/-18, Q2's old confounded histories):**
- On `seed-8-useful` (and `seed-8-001` identically): `prep_T4` supply **100**, price **4750**, farm_output **60**, `price_value_effect` **130**, inventory **250**, wealth_delta **130**; `unprep_T4` supply **100**, price **4750**, farm_output **60**, `price_value_effect` **104**, inventory **200**, wealth_delta **104**. Equality holds (100==100, 4750==4750, 60==60); inequality holds on the exposure metrics (130 vs 104, 250 vs 200). The old Rev 3 numbers `+130/-18` with supply `100 vs 520` are superseded by these isolated figures.

**Expected evidence after implementation:**
- CLI per-turn headers show stages `normal → early_dry → worsening_dry → DROUGHT → aftermath` and signals escalate before impact; `6 MONTHS LATER` still shows wealth/inventory/price and `WHY?` drivers plus `MIRA`/`DARAN` headlines.
- Trace dump (verbose) includes chain `pressure_stage:pressure:northern_drought:worsening_dry → world:drought → farm_output:drought_reduced_yield → home_supply → home_price → … → wealth`, with `pressure_stage` node's `reason_code` exactly `pressure.causal_source_id`.
- Same seed+choices second run byte-equal (`final_wealth`, `rival_history`, trace).
- `test_warning_is_useful_preparation_changes_drought_outcome` passes with mechanism-isolated, fully affordable histories and equality pre-condition; `test_no_single_policy_dominates_all_metrics` still passes but is no longer the instrument for Section 8.
- No existing test file edited to relax an assertion (verified by diff + grep for `abundant`/`"Surplus"`).

---

## Risks / Rollback

- **Risk:** Changing `TURN_SPECS` signals (T2 surplus wording) breaks substring checks like `assert "abundant" in TURN_SPECS[1].signal.lower()` (`test_five_turn_prototype.py:365`). **Mitigation:** R4 wording retains `"Grain remains abundant"` as prefix, so `"abundant"` substring still passes. Keep title `"Surplus"` exactly. Verify with `grep -n abundant backend/tests/*.py` before merge.

- **Risk:** Changing `resolve_turn` signature breaks existing call sites (`prototype.py`, `demo.py`, tests). **Mitigation:** Update all call sites in same commit to pass `PressureState` instead of `world`. `world` is a field on the pressure object, so kernel change is one line (`world = pressure.world`). No churn in `GameState`.

- **Risk:** Adding `kind="pressure"` trace node could be mistaken for needing a validator change. **Mitigation:** Do not change `trace.py` — verified fallback admits `delta=None` parentless nodes. Add a regression that would fail if someone later tightens the validator.

- **Risk:** Rivals that previously keyed on `next_world_known=="drought"` only on idx 2 still work, but adding `early_dry` stage could be confused with threat. **Mitigation:** Keep existing boost tiers unchanged; only `worsening_dry` triggers drought threat, `early_dry` is `None` (new test proves it).

- **Risk (Q2):** Affordable-history pre-condition could hide a future cost change that makes histories unaffordable. **Mitigation:** Test explicitly asserts affordability (Q2) so a cost increase fails the pre-condition with a clear message rather than silently testing a no-op.

- **Rollback:** Revert `prototype.py` to re-introduce hard-coded `TURN_SPECS` and ignore `pressure` module; remove `pressure_stage` node emission from `turn.py`; restore `resolve_turn(state, command, world, ctx)` signature. No `GameState` migration needed because no field was added.

---

## Decisions Settled (R8 + grill + F1–F5)

This plan is decision-complete. All prior open choices plus grill and round-2 findings are now locked:

1. **GameState field vs pure derivation:** Resolved per R1 — no `GameState.pressure_stage` field. Pressure is derived from `turn` via `pressure_for_turn` and surfaced via `game.current_pressure` + trace. `current_pressure` is `None` when complete (Q3, already resolved — keep as-is per round-2 convergence note).

2. **Signal prose for T2 early dry:** Resolved per R4 — `"Grain remains abundant, but the rains have begun to fail."` (observational rainfall, not output), title remains `"Surplus"`.

3. **Warning isolation (Q1):** Instrument shares T1 `hold`, diverges only at T2–T3 warning stages.

4. **Mechanism isolation (F1):** Instrument avoids `expand_farm` in either arm, so T4 market is provably identical; equality pre-condition asserts supply/price/farm_output identity.

5. **Affordability (Q2):** Both histories fully affordable (hold+granary+buy20 cost 387, hold×5 cost 0), no clamped commands.

6. **Stage/world biconditional (F2):** Model validator enforces `stage=="drought" <=> world=="drought"`.

7. **`causal_source_id` single source (F3):** `turn.py` reads `pressure.causal_source_id` directly, does not recompute format string.

8. **File location (F4):** `backend/app/domain/pressure.py` re-exported via `domain/__init__.py`.

9. **Smallness (Q4):** Structural checks, not line count — already resolved, keep as-is.

10. **Threshold (Q5):** Threshold-free inequality on `price_value_effect` (and wealth/inventory), not magic-number gated — evidence numbers recomputed to `130 vs 104` (isolated) replacing stale `+130/-18` (confounded).

No unresolved implementation choices remain.

---

## Keep as-is (from review, preserved)

- One hard-coded five-stage arc; no DSL, no JSON loader, no weighted sampler.
- Five turns, not six — protects "exactly five decisions."
- `TURN_SPECS` derived from `PRESSURE_ARC` for temporary compatibility, with `PRESSURE_ARC` stated explicitly as the single source.
- Only T4 actually changes production; T5 aftermath emerges from carried economic state.
- Structured threat derived from `stage == "worsening_dry"`, never from parsing prose.
- Reuse `actor.compute_farm_output`; no new RNG or event sampler.
- Already resolved in Rev 3 (per round-2 convergence note — do not redo): `current_pressure is None` when complete; `<60 lines` replaced with structural checks.

---

## What Changed Versus Rev 3

| Area | Rev 3 | Rev 4 | Review item |
|------|-------|-------|-------------|
| **AC1/AC3 unprepared history** | `[hold, expand_farm, expand_farm, hold, hold]` — timing-isolated but mechanism-confounded (farm_capacity 30 vs 10 → different T4 supply 520 vs 100, price_value `+130 vs -18`) | **`[hold, hold, hold, hold, hold]`** (literal no-response) — shares T1, diverges only at warnings, *neither* arm calls `expand_farm`, so T4 market is provably identical | **F1 BLOCKING** |
| **Equality pre-condition** | None (only post-condition inequality) | **New:** `prep_T4.supply == unprep_T4.supply` (100==100), `price ==` (4750==4750), `farm_output ==` (60==60) — proves isolation before asserting different exposure | **F1 BLOCKING** |
| **Evidence numbers cited** | `price_value +130 vs -18`, supply `100 vs 520` (confounded) | **Recomputed:** `price_value 130 vs 104` (delta 26), `wealth 130 vs 104`, `inventory 250 vs 200`, with equality `supply 100==100, price 4750==4750, farm 60==60` | **F1** (recompute) |
| **`PressureState` validator** | None — `early_dry`+`drought` still validated | **Model validator:** `stage=="drought" <=> world=="drought"`; all other stages => `world=="normal"`; regression tests for 3 invalid combos | **F2 BLOCKING** |
| **`causal_source_id` → trace** | `turn.py` recomputed `f"pressure:{id}:{stage}"` separately from field | **`turn.py` reads `pressure.causal_source_id` directly**; `PressureState` enforces default formula if explicitly set (F3) | **F3 should-fix** |
| **File location hedge** | `types.py (or pressure.py)` | **`backend/app/domain/pressure.py`**, re-exported via `domain/__init__.py` | **F4 should-fix** |
| **Validation closeout** | Implicit | **Explicit 6-step closeout** per `AGENTS.md`/`BUILD_SPEC.md §0.3/§0.4` (F5): gates, graphify, STATE.md, DECISIONS.md, BUILD_SPEC status, push; stop | **F5 should-fix** |

Nothing in the "keep as-is" list was dropped. No turn-kernel rewrite, no new abstraction beyond the one `domain/pressure.py` + one `engine/pressure.py` module pair, no Section 9/15 material.

---

## Closeout Checklist (F5 — literal last step)

After implementation, do not mark Section 8 complete until all of:

1. `make test` / `make lint` / `make type` / `make format-check` green (real output, not estimate).
2. `graphify update .` and commit regenerated tracked artifacts if `git status` shows changes.
3. `STATE.md` synced to HEAD: exact `pytest` test count, new `domain/pressure.py` + `engine/pressure.py` modules, `current_pressure`/`PressureState` contract, real gate results.
4. `DECISIONS.md` next entry (012) recording pressure is turn-derived/session-authored (not canonical `GameState`), matching R1/F2.
5. Only then flip `BUILD_SPEC.md` Section 8 `Status: NOT STARTED` → `COMPLETE`.
6. Commit + push. Stop. Do not begin Section 9.
