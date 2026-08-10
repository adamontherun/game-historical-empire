# Section 8 — Pressure-Driven Event Arc — Plan (Rev 3 — post-grill, incorporates R1–R8 + grill fixes)

**Date:** 2026-08-10 (revised 2026-08-10 after review round 1; revised again 2026-08-10 after grill)
**Branch:** `section/8-pressure-driven-event-arc` (from `origin/main` at `53fb3e6`)
**Spec Authority:** `BUILD_SPEC.md` Section 8 (Status: NOT STARTED) + global §§10–16 + `DECISIONS.md` 001–011 + `STATE.md` §7
**Related:** `backend/app/domain/types.py`, `backend/app/domain/trace.py`, `backend/app/engine/turn.py`, `backend/app/engine/actor.py`, `backend/app/engine/prototype.py`, `backend/app/engine/rivals.py`, `backend/app/cli.py`, `backend/app/engine/demo.py`, `backend/tests/test_five_turn_prototype.py`, `backend/tests/test_deterministic_rivals.py`
**Review input:** `docs/plans/2026-08-10-section-8-review-round-1.md` (R1–R8) + headless grill of Rev 2 (Q1–Q7 below)

---

## Goal

Replace the current hard-coded `TURN_SPECS` + single-value `next_world_known` warning with a small, coherent, deterministic world-pressure system that drives one 5-turn arc:

```
normal → early_dry → worsening_dry → drought → aftermath
```

Keep impact **systemic** (drought reduces farm output → supply signal → price pressure → price, never `price *= 1.4`), keep the 5-turn headless game intact, and keep the system trivially inspectable without introducing a generic 30-event DSL, content loader, or new goods/rivals.

---

## Success Criteria (maps to Section 8 AC + global rules)

1. **At least one useful warning before impact (AC1, proven via the single AC1+AC3 instrument below).** Turns 2–3 surface early (`early_dry`) and worsening (`worsening_dry`) dry signals that a prepared player can act on. Usefulness is proven operationally: two legal histories that are identical through T1 (normal) and diverge only during the warning stages (T2–T3) produce materially different T4 drought outcomes.

2. **Drought stays systemic (AC2).** Drought changes `farm_output` via `actor.compute_farm_output` (40% reduction), then `home_supply` (`signal_next = max(0, signal+farm_output-demand)`), then `home_price` via `_target_price/_bounded_price`. No direct price mutation. Proved by trace parent chain.

3. **Different preparation → different result (AC3).** Same authored drought + same seed, different legal warning-stage preparation → materially different T4 drought exposure/consequence. Proven by the same instrument as AC1; threshold-free (inequality) rather than magic-number gated.

4. **Deterministic & inspectable (AC4).** Same `run_seed + ruleset_version + choices[5]` → identical pressure progression, signals, world conditions, prices, rival headlines, and trace. Inspectable via `pressure_for_turn(idx)` / `game.current_pressure` (None when complete) / trace pressure node. No new canonical field in `GameState`.

5. **Small, no DSL (AC5).** One hard-coded 5-element `PRESSURE_ARC`, one enum + one frozen model, one pure helper module `engine/pressure.py`. Structural smallness checks (no JSON loader, no sampler) — not a line-count threshold. `ruff`/`pyright` clean.

6. **Housekeeping preserved.** `engine`+`domain` pure, integers only, deterministic RNG, drivers ≤3, rivals deterministic via integer scoring + structured threat, 112 existing tests remain green (none relaxed).

---

## Context And Current Facts (verified against code)

- **Spec §8:** One pressure arc with *possible* fields `id, stage, signal_text, world_modifiers, activation_turn, causal_source_id`; authored turns allowed; must stay systemic; no generic framework. `world_modifiers` is optional — correctly omitted per R2.

- **Domain `backend/app/domain/types.py`:** `GameState{turn, run_seed, ruleset_version, player, market:Home, river_market, route}`; `WorldCondition = Literal["normal","drought"]`; no pressure field yet; adding one would duplicate `turn`+arc (R1).

- **Trace `backend/app/domain/trace.py:47,102,149-165,170-173`:** `CausalNode.kind: str` (not the `Kind` literal), `allowed_empty_roots = {"world","command"}` (102), must-have-parents list 149–165 excludes `"pressure"`, fallback at 170–173 admits any `delta is None` (or 0) node as root without being in `allowed_empty_roots`. Verified: a pressure node `kind="pressure", delta=None, parent_ids=()` validates as-is. No validator change needed (R3).

- **Actor `backend/app/engine/actor.py:14-21`:** `YIELD_PER_CAPACITY=10`, `DROUGHT_YIELD_REDUCTION_BPS=4000`, `EXPAND_FARM_COST=500` (+10 cap), `BUILD_GRANARY_COST=300` (+50 cap), `ROUTE_ESTABLISH_COST=400`, `cost_for_quantity = qty*price//1000`, `affordable_quantity` as in 41–42. All costs integer, shared.

- **Prototype `backend/app/engine/prototype.py`:** `FiveTurnGame` owns `state + history[5] + rivals`; `TURN_SPECS` 5 signals; `current_spec()` returns `None` when `is_complete`; `default_start_state` cash 1000, grain 20, farm 10, storage 200, prices 5000/5200. `_next_world_known_for_turn(2)=="drought"` only.

- **Turn `backend/app/engine/turn.py:122`:** Current `resolve_turn(state, command, world, rng_context)` — will become `resolve_turn(state, command, pressure: PressureState, rng_context)` deriving `world = pressure.world`.

- **CLI `backend/app/cli.py`:** Entry point is `backend/app/cli.py` (not `backend/app/engine/cli.py` — `ls` confirms only the former exists). Invocation `uv run --project backend python backend/app/cli.py ...`.

- **Tests:** 112 passing; citations `test_five_turn_prototype.py:153` (`test_no_single_policy_dominates_all_metrics`) and `:368` (`titles[1]=="Surplus"`) verified.

---

## Verification of Review Claims

All four cited locations checked directly:

- **`trace.py:149-165` + `170-173`:** Correct — `"pressure"` not in must-have-parents list, `delta is None` falls through to `continue`. No `allowed_empty_roots` change needed.
- **`test_five_turn_prototype.py:153`:** Correct — divergence test already passes without pressure.
- **`test_five_turn_prototype.py:368`:** Correct — `titles[1]=="Surplus"` would break on rename.
- **`backend/app/cli.py`:** Correct — draft's `python -m app.engine.cli` wrong; smoke policy without `secure_route` never ships.

No review claim was wrong. All eight items adopted.

---

## Grill — Stress Test of Rev 2 (decision-forcing Q&A)

The following grill was run against Rev 2. Each question states the challenge, the computed evidence, and the settled decision folded into Rev 3. Where the product owner must be escalated, it is marked **ESCALATE** — none required for Section 8.

### Q1 — Does the AC1/AC3 instrument actually isolate the WARNING?

**Challenge:** Rev 2 proposed:
`prep=[build_granary, buy_grain:20, hold, hold, hold]` vs `unprep=[expand_farm, expand_farm, expand_farm, hold, hold]`
These histories already differ at **T1**, which is `normal` (before any warning). The T4 divergence could therefore be attributed to a pre-warning decision, not to the warning-driven preparation at T2–T3. Does the instrument isolate the warning?

**Evidence:** Under the Rev 3 arc, T1=`normal`, T2=`early_dry`, T3=`worsening_dry`, T4=`drought`. The warning stages are T2–T3. Histories differing at T1 change starting capital/composition before the warning exists, conflating "good opening" with "heeded the warning". A cleaner instrument shares T1 and diverges only during T2–T3.

**Answer/Decision:** Replace the instrument with **warning-isolated histories sharing T1**:

- **Prepared (warning-heeded):** `[hold, build_granary, buy_grain:20, hold, hold]` — T1 hold (neutral), T2 build storage, T3 buy grain during worsening warning.
- **Unprepared (warning-ignored):** `[hold, expand_farm, expand_farm, hold, hold]` — same T1 hold, T2–T3 farm expansion (concentration, not preparation).

Same seed `seed-8-useful`. Both histories are fully affordable (see Q2). Comparison is on the **T4 `TurnResolution`** (index 3): inventory after T4, `wealth_delta`, and the wealth decomposition nodes `price_value_effect` / `quantity_value_effect` must differ. This isolates the warning: the only difference in the two runs is what the player did *after* the warnings appeared. **No ESCALATE.**

### Q2 — Are the proposed histories affordable and executable?

**Challenge:** Starting cash is 1000. `EXPAND_FARM_COST=500`, `BUILD_GRANARY_COST=300`, `buy_grain:20` costs `20*price_milli//1000`. If any command would be rejected/clamped (`insufficient_cash*`), the history does not prove what the test claims — it proves a no-op.

**Evidence (computed via `FiveTurnGame` with `seed grill-seed-001`, costs from `actor.py`):**

- **Rev 2 unprepared `[expand, expand, expand, hold, hold]`:**
  - T1 expand: 1000→500 ✓ (`expand_farm`)
  - T2 expand: 500→0 ✓ (`expand_farm`)
  - T3 expand: 0→0 ✗ **`insufficient_cash_for_expand`, delta 0, farm unchanged** — third command is a no-op. History is not what it claims to be; T4 divergence is between "2× farm" and "1× granary+buy", not "3× farm". Computed T4 `wealth_delta` for 3× and 2× are identical (-9) because third expand was inert.

- **Rev 2 prepared `[build_granary, buy_grain:20, hold, hold, hold]`:**
  - T1 granary: 1000→700 ✓
  - T2 buy20 @ price_before 4545: cost `20*4545//1000=90` → 700→610 ✓ (`buy_grain`, not clamped)
  - Affordable, but shares the Q1 isolation defect.

- **Rev 3 isolating histories (both affordable, no clamping):**
  - `prep_iso [hold, build_granary, buy_grain:20, hold, hold]`:
    - T1 hold 1000→1000, T2 granary 1000→700 ✓, T3 buy20 @ 4375 cost 87 → 700→613 ✓, T4 hold, T5 hold. All `reason_code` in `{"hold","build_granary","buy_grain"}`, no `insufficient_*`. Final `cash_low 613`.
  - `unprep_iso [hold, expand_farm, expand_farm, hold, hold]`:
    - T1 hold 1000→1000, T2 expand 1000→500 ✓, T3 expand 500→0 ✓, no insufficient. Final `cash_low 0`.

  T4 outcomes: `prep_iso` price_value_effect `+130` (Home price 4230→4750, inventory 250), `unprep_iso` price_value_effect `-18` (price 3023→2932, inventory 200 capped). Deltas are material and fully from executed commands.

**Decision:** Adopt the **isolating, affordable histories** above as the AC1+AC3 instrument. Add an explicit **affordability assertion** in the test: every `TurnResolution`'s `command` node `reason_code` is in the success set `{"hold","build_granary","expand_farm","buy_grain","secure_route","ship_grain"}` and not in `{"insufficient_cash*","insufficient_storage","no_route_access"}` (i.e., no clamping), and the test asserts `command.delta == requested` for buy/expand terms where applicable. History with a clamped command fails the test's pre-condition, not its post-condition.

### Q3 — What does `current_pressure` return when complete?

**Challenge:** `FiveTurnGame` has `turn_limit=5`, `history` length 0..5, `PRESSURE_ARC` has 5 elements (idx 0..4). `pressure_for_turn(len(history))` with `len==5` is out of range. Rev 2 said `current_pressure` returns `pressure_for_turn(len(history))` when not complete, but left the complete case undefined. What is the contract?

**Evidence:** `prototype.py:292-306` — `current_spec()` returns `None` when `is_complete` (and `current_signal`/`current_title` propagate that). The pressure accessor should mirror this; returning `PRESSURE_ARC[4]` (aftermath) when complete would imply the game is still "on" aftermath turn 4, which it is not — it is over. Index 5 is past the arc.

**Decision:** Define:

```python
@property
def current_pressure(self) -> PressureState | None:
    if self.is_complete:
        return None
    return pressure_for_turn(len(self._history))
```

- `pressure_for_turn(idx)` raises `IndexError` (or `ValueError`) for idx not in 0..4; never called with 5 via the accessor.
- Direct callers needing the aftermath pressure after completion use `PRESSURE_ARC[4]` or `pressure_for_turn(4)`, not `current_pressure`.
- Documentary: `current_signal`/`current_title` continue to derive from `current_pressure.signal/title` when not complete, else `""` / `"Complete"`.

### Q4 — Is "pressure.py is under 60 lines" a legitimate test? What is the structural equivalent?

**Challenge:** A line-count threshold is brittle — adding a comment or docstring breaks it; deleting a blank line passes it while adding a JSON loader would not be caught if formatted tersely. What does it actually prove, and what is the right structural check for "small, no DSL"?

**Answer:** The intent is to prove "one hard-coded arc, no loader, no sampler, no generic framework". Line count is a proxy, not the property. Replace with structural assertions that would fail if the forbidden thing were added regardless of formatting:

- `len(PRESSURE_ARC) == 5`
- `PressureState.model_fields.keys() == {"pressure_id","stage","activation_turn","world","signal","title","causal_source_id"}` — exactly 7 fields, no `world_modifiers`
- `not any("json" in s for s in open("backend/app/engine/pressure.py").read().lower().split())` — equivalently assert `import json` / `json.load` not present as import string, and assert `import random` not present — but implement as file-text scan for `"json"` / `"import random"` / `"weighted"` / `"sampler"` substrings, which would catch a loader even if short.
- `pressure.py` imports only `typing`/`pydantic`/`domain/types` — no `sqlalchemy`, `fastapi`, `httpx`, `openai`.

**Decision:** Replace the `<60 lines` check with the structural suite above. Keep the arc definition visibly short (~15 lines of tuple entries) as a code-review expectation, not a test threshold.

### Q5 — Threshold hedging ("like ≥50 money or ≥5 grain") — pick exact numbers or go threshold-free

**Challenge:** Rev 2's `test_warning_is_useful` said "at least two of {…} differ by material delta (>0, and at least one exceeds a threshold like ≥50 money or ≥5 grain)". The hedging ("like") leaves the implementer to invent a magic number; a future price reformulation could still pass/fail depending on the choice.

**Evidence from Q2 computation:** With the isolating histories, T4 `price_value_effect` is `+130` vs `-18` (delta 148 money), `wealth_delta` `+130` vs `-18` (same), `inventory after T4` 250 vs 200 (delta 50 grain, but both capped at storage — inventory delta is partly from earlier cap). The material difference is not marginal.

**Options:**
- (a) Threshold-free strict inequality: `assert prep_T4.price_value_effect != unprep_T4.price_value_effect` and `assert prep_T4.inventory != unprep_T4.inventory` — proves different exposure without magic numbers.
- (b) Exact thresholds: e.g. `abs(delta_price_value) >= 50` or `abs(delta_inventory) >= 10`.

Threshold-free is more robust to price-parameter tweaks and has no magic number to justify; it directly asserts "preparation changed the drought outcome" without claiming a magnitude. A magnitude floor adds no product value for Section 8 and drifts into Section 9 balancing.

**Decision:** Make the core assertion **threshold-free** on the T4 decomposition: `prep_T4.price_value_effect != unprep_T4.price_value_effect` and at least one of `prep_T4.wealth_delta != unprep_T4.wealth_delta` or `prep_T4.next_state.player.inventory.grain != unprep_T4.next_state.player.inventory.grain`. Additionally assert each history's affordability (Q2) so the inequality is not between a success and a clamped no-op. Document the observed deltas (148 money, 50 grain) as evidence, not as gating thresholds.

### Q6 — Scope creep toward Section 9 or 15

**Challenge:** Does any part of the plan build Section 9 (balance harness — strategy win rates, multi-seed sweeps) or Section 15 (content model / `content_version` / JSON loader / parameterized modifiers) early?

**Findings:**
- Rev 2's AC3 and smallness language already deferred win-rate sweeps; Rev 2 correctly states "do not sweep seeds, do not assert win rate". No change needed.
- `world_modifiers` was already removed (R2); Rev 3 keeps it removed. No `content_version`, no JSON file, no weighted sampler, no DSL.
- The only borderline creep risk is the "price_value_effect >= X" threshold in Q5 if it were interpreted as a balance gate. Adopting threshold-free (Q5) eliminates even the appearance of Section 9 gating.
- CLI smoke and `StrategicSummary` stage display are Section 8 presentation, not Section 9 harness.

**Decision:** Keep the scope statement explicit: Section 8 proves only that warning-driven preparation changes the *same* drought's outcome for *one* seed; no multi-seed harness, no win-rate, no content loader, no `world_modifiers` parameterization. Add a guard test that `PressureState` has exactly 7 fields and `pressure.py` contains no `json`/`sampler` loader text (Q4).

### Q7 — Anything that would silently weaken an existing test

**Challenge:** Does the plan relax `test_turn_specs_length_and_titles:368` (titles), `test_signals_truthful_about_mechanics` substring checks, or any other existing assertion to accommodate new prose/arc?

**Findings:**
- T2 title remains `"Surplus"` (R4) — `test_turn_specs_length_and_titles` stays green.
- T2 signal Rev 3 is `"Grain remains abundant, but the rains have begun to fail."` — retains substring `"abundant"` so `assert "abundant" in TURN_SPECS[1].signal.lower()` at `test_five_turn_prototype.py:365` stays green. Word "abundant" is the load-bearing token; verify before merge with `grep -n abundant backend/tests/*.py`.
- No other existing test is edited. `TURN_SPECS` is derived, so length/title/signal checks that read `TURN_SPECS` automatically reflect pressure without edit; they are not relaxed, they are satisfied.
- `resolve_turn` signature change touches call sites but not test logic; tests that call `resolve_turn` will be updated to pass `PressureState` (mechanical, not a weakening).
- `trace.py` validator is not loosened (R3).

**Decision:** Keep the "no existing assertion edited or relaxed" rule. Add a checklist item in the work plan to `grep` existing tests for signal/title substrings before merge.

### ESCALATE

None. All seven questions are settleable from code, spec, and computed cash/price evidence. No product-owner decision is needed for Section 8's scope.

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

| # | Decision | Choice (revised per R1–R8 + grill Q1–Q7) | Why | Alternative Rejected |
|---|----------|-------------------------------------------|-----|----------------------|
| 1 | **Pressure representation — where & how small (R1,R2,Q4,Q6)** | Introduce `PressureStage = Literal["normal","early_dry","worsening_dry","drought","aftermath"]` and frozen `PressureState{ pressure_id: str, stage: PressureStage, activation_turn: int, world: WorldCondition, signal: str, title: str, causal_source_id: str }` — **exactly 7 fields, no `world_modifiers`**. Put the enum+model in `backend/app/domain/types.py` (or `backend/app/domain/pressure.py` re-exported via `domain/__init__.py`) and pure helpers in `backend/app/engine/pressure.py`. `pressure_id` e.g. `"northern_drought"` stable; `causal_source_id` defaults to `f"pressure:{pressure_id}:{stage}"`. Validate `activation_turn == index in PRESSURE_ARC`. | Satisfies spec's suggested fields without DSL; pressure drives both world and prose from one source. 7-field exactness proven structurally; line-count proxy removed (Q4). | Generic `Event{weight, duration, modifiers}` registry rejected; `world_modifiers` mapping rejected (R2); `GameState.pressure_stage` rejected (R1); line-count gate rejected (Q4). |
| 2 | **Single source of truth for `world` (R1)** | Change `resolve_turn` signature to `resolve_turn(state, command, pressure: PressureState, rng_context) -> TurnResolution` and derive `world = pressure.world` internally. `FiveTurnGame.submit` calls `pressure = pressure_for_turn(idx)` then `resolve_turn(state, command, pressure, ctx)`. | Eliminates three-representation hazard. Inspectability via `pressure_for_turn(state.turn)` + `game.current_pressure` + trace is sufficient. | Keeping bare `world` arg alongside pressure rejected. |
| 3 | **Arc authoring — mapping 5 turns to 5 stages (R4,Q1,Q2)** | Hard-code `PRESSURE_ARC: tuple[PressureState,5]`: <br>0 `normal` {world normal, signal "The growing settlement keeps food demand high.", title "A Growing Settlement", activation 0}, <br>1 `early_dry` {world normal, signal **"Grain remains abundant, but the rains have begun to fail."**, title **"Surplus"** (unchanged), activation 1}, <br>2 `worsening_dry` {world normal, signal **"The dry spell persists. Farmers warn the next harvest is at risk."**, title "Warning Signs", activation 2}, <br>3 `drought` {world drought, signal "Drought cuts farm output — regional supply tightens.", title "Drought", activation 3}, <br>4 `aftermath` {world normal, signal "Markets adjust to the drought's aftermath.", title "Aftermath", activation 4}. <br>T2/T3 prose is observational about **rainfall**, not output. Only T4 flips `world=drought`. | Truthful prose (no claim T2 harvest weakened); two escalating warnings; title preservation keeps `test_turn_specs_length_and_titles:368` green; affords isolating histories (Q1/Q2). | 6 turns rejected; T2 pure surplus with no hint rejected; light-drought early stages rejected; "weak harvest hints" wording rejected. |
| 4 | **Structured threat for rivals (keep-as-is + R1, Q1)** | `next_world_known_for_turn(idx)` returns `"drought"` iff `PRESSURE_ARC[idx].stage == "worsening_dry"` (T3 only), else `None`. Implemented in `pressure.py`. `FiveTurnGame._observable_for` builds `ObservableContext` from that helper and `pressure.world`. No prose parsing. | Warning is authored stage, not parsed prose; no behavior change beyond sourcing the same T3 warning from pressure. | Parsing `signal_text` rejected; graded `early_dry` boost rejected (would alter fingerprint without need). |
| 5 | **Trace integration — pressure as causal root (R3, Q6)** | In `turn.py:resolve_turn`, emit leading `CausalNode(id="pressure_stage", kind="pressure", label=<stage title-derived>, before=None, after=None, delta=None, reason_code=f"pressure:{pressure.pressure_id}:{pressure.stage}", parent_ids=())` then `world` node `parent_ids=("pressure_stage",)`. Chain: `pressure_stage → world → farm_output → home_supply → home_price → … → wealth`. No hash, no numeric delta. Do not modify `trace.py` `_validate_dag`. | Guarantees AC2 systemic path; inspectable root; validates via existing fallback; no price node directly parented to pressure. | Hash/validator loosening rejected. |
| 6 | **Signal/title ownership** | `TurnSpec` subsumed by `PressureState`. Keep `TurnSpec` alias: `TURN_SPECS = tuple(TurnSpec(world=p.world, signal=p.signal, title=p.title) for p in PRESSURE_ARC)` in `prototype.py`. Single source is `PRESSURE_ARC`. | Zero churn for `TURN_SPECS` imports. | Deleting `TurnSpec` or keeping two lists rejected. |
| 7 | **Current-pressure accessor when complete (Q3)** | `game.current_pressure: PressureState \| None` — returns `None` when `is_complete`, else `pressure_for_turn(len(history))`. Mirrors `current_spec()` pattern. `pressure_for_turn` raises on out-of-range idx; callers needing aftermath pressure use `PRESSURE_ARC[4]`. | Out-of-range handled explicitly; complete game does not pretend to be on turn 5. | Returning `PRESSURE_ARC[4]` when complete rejected — conflates "over" with "on aftermath". Returning `PRESSURE_ARC[len(history)]` without guard rejected — IndexError. |
| 8 | **No new costs / market math** | Reuse `actor.compute_farm_output`; Python formula stays authoritative. | Deferred to Section 15. | Parameterized executable modifiers rejected. |

---

## Recommended Approach

Stay additive and keep the kernel as authority. Implement in dependency order so each step is testable:

1. **Domain:** Add `PressureStage` + `PressureState` (7 fields, frozen) in `backend/app/domain/types.py` (or new `pressure.py` re-exported). Export via `domain/__init__.py`.

2. **Engine:** New `backend/app/engine/pressure.py` defining `PRESSURE_ARC: tuple[PressureState,5]` hard-coded with the 5 stages above (exact prose per R4, `activation_turn == index`), helper `pressure_for_turn(idx) -> PressureState`, and `next_world_known_for_turn(idx)`. No RNG, pure, validated.

3. **Prototype:** Refactor `backend/app/engine/prototype.py` so `TURN_SPECS` is derived from `PRESSURE_ARC` and `FiveTurnGame` drives progression from `PRESSURE_ARC`. Change `submit()` to `pressure = pressure_for_turn(idx)` → `resolve_turn(state, command, pressure, ctx)`. Build `ObservableContext` threat from `pressure.stage == "worsening_dry"` via `next_world_known_for_turn`. Remove `_next_world_known_for_turn`. Add `current_pressure` per Q3 contract.

4. **Turn kernel:** Extend `backend/app/engine/turn.py` to accept `PressureState` (derive `world`), emit the `pressure_stage` root node per Decision 5, parent `world` to it. Keep `_target_price/_bounded_price` and actor calls unchanged. Update demo `backend/app/engine/demo.py` call site to pass pressure as well.

5. **Rivals/CLI:** No scoring rewrite; only threat source changes. `backend/app/cli.py` displays `game.current_pressure.title/signal/stage` per turn header; `StrategicSummary.format()` appends stage per turn. Keep two-phase rival timing unchanged.

All functions remain plain, sync, deterministic.

---

## Work Plan

### 1 — Domain pressure types (no behavior change yet)
- **Surface:** `backend/app/domain/types.py` (+ optional `backend/app/domain/pressure.py`) + `backend/app/domain/__init__.py`
- **Do:** Add `PressureStage` literal and `PressureState` frozen model with exactly `pressure_id, stage, activation_turn, world, signal, title, causal_source_id`; `activation_turn` in 0..4; `causal_source_id` default `f"pressure:{pressure_id}:{stage}"`.
- **Tests (new, `backend/tests/test_pressure_arc.py`):** Enum validation, frozen, `activation_turn` matches index, 5 stages in order `normal→early_dry→worsening_dry→drought→aftermath`, world only `drought` on impact, `causal_source_id` stable, invalid stage rejected. Structural smallness sub-checks: field count ==7, no `world_modifiers` attr.
- **Depends:** none.

### 2 — Pressure arc + pure helpers
- **Surface:** `backend/app/engine/pressure.py` (new) + `backend/app/engine/__init__.py` re-export if convenient
- **Do:** Hard-code `PRESSURE_ARC` tuple of 5 `PressureState` with truthful signals per R4 (ids stable `"northern_drought"`). Implement `pressure_for_turn(idx)`, `world_for_turn(idx)`, `next_world_known_for_turn(idx)` (worsening→drought only). Validate at import that `p.activation_turn == index` for all p. No RNG, no I/O.
- **Tests (extend `test_pressure_arc`):** Determinism (`pressure_for_turn(2).stage == "worsening_dry"`), `next_world_known == "drought"` only on idx 2, idempotent, `pressure_id` stable, out-of-range raises, `current_pressure` contract when complete (see Work Plan 3 test).
- **Depends:** 1.

### 3 — Prototype refactor to drive from pressure (keep TURN_SPECS compat)
- **Surface:** `backend/app/engine/prototype.py`
- **Do:** Import `PRESSURE_ARC`/`pressure_for_turn`/`next_world_known_for_turn`. Derive `TURN_SPECS` from `PRESSURE_ARC` for compat. Remove `_next_world_known_for_turn`. Change `submit()` to `pressure = pressure_for_turn(idx)` and pass `pressure` to `resolve_turn`. Update `_observable_for` to populate `next_world_known` from `next_world_known_for_turn(idx)`. Add `current_pressure` property per Q3 (`None` when complete).
- **Tests:** Existing `test_five_turn_prototype.py` still passes via derived `TURN_SPECS`; new assertions — `game.current_pressure.stage` progression `normal→early_dry→worsening_dry→drought→aftermath`, `game.current_pressure is None` after 5 submits, `current_signal` matches arc, `current_spec` still mirrors pressure.
- **Depends:** 2.

### 4 — Turn kernel signature + trace integration (pressure → world chain)
- **Surface:** `backend/app/engine/turn.py` (+ `backend/app/engine/demo.py` call site; **no change** to `backend/app/domain/trace.py` per R3)
- **Do:** Change `resolve_turn(state, command, pressure: PressureState, rng_context)` — derive `world = pressure.world` at top. Emit leading `pressure_stage` node with `kind="pressure"`, `delta=None`, `reason_code=f"pressure:{pressure.pressure_id}:{pressure.stage}"`, `label` derived from `pressure.title`. Make `world` node `parent_ids=("pressure_stage",)`. Keep all other nodes parented as before. Update docstring and `TURN_ORDER` comment to `pressure_stage -> world -> production -> ...` if documented.
- **Tests:** `backend/tests/test_causal_trace.py` — assert chain `pressure_stage → world → farm_output → home_supply → home_price → … → wealth` exists for all turns; drought path includes `drought_reduced_yield`; **no edge from `pressure_stage` directly to any price node** (price reachable only via `farm_output`/`supply`); drivers still ≤3; validator not modified (assert file text of `trace.py` does not contain `pressure` in `allowed_empty_roots`).
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

### 7 — New Section 8 acceptance tests (exact specification per R5/R6 + Q1/Q2/Q5)
- **Surface:** `backend/tests/test_pressure_arc.py` (or `test_pressure_driven_arc.py`) — new file; **no existing test assertions relaxed**
- **Do:** Implement exactly the tests enumerated in the Validation Plan below. They prove AC1+AC3 via the isolated, affordable instrument (Q1/Q2), AC2 systemic chain, AC4 determinism/inspectability (including `current_pressure is None` when complete), and AC5 structural smallness (Q4).
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

# Quick harness sanity — preparation divergence is on T4, not final wealth (Q1/Q2 isolated histories)
uv run --project backend python - << 'PY'
import sys
sys.path.insert(0, 'backend')
from app.engine.prototype import FiveTurnGame
from app.domain.types import PlayerCommand as C
# Warning-isolated instrument: share T1 (normal), diverge only at T2-T3 (early/worsening)
prep   = [C(type='hold'), C(type='build_granary'), C(type='buy_grain', quantity=20), C(type='hold'), C(type='hold')]
unprep = [C(type='hold'), C(type='expand_farm'),    C(type='expand_farm'),          C(type='hold'), C(type='hold')]
for name, choices in [('prep', prep), ('unprep', unprep)]:
    g=FiveTurnGame(seed='seed-8-001')
    g.run(choices)
    t4 = g.history[3]  # drought impact turn
    print(name, 'T4 wealth', t4.player_outcome.wealth_delta,
          'price_value', next(n.delta for n in t4.causal_trace.nodes if n.id=='price_value_effect'),
          'inv', t4.next_state.player.inventory.grain,
          'price', t4.next_state.market.current_price,
          'cmd_reason', next(n.reason_code for n in t4.causal_trace.nodes if n.id=='command'))
PY
```

### Exact new/changed tests (what each proves)

No existing assertions are edited or relaxed. All new tests live in `backend/tests/test_pressure_arc.py` (plus one extension in `test_causal_trace.py` and one probe in `test_deterministic_rivals.py`).

| Test | File | What it proves | How it isolates pressure (grill-hardened) |
|------|------|----------------|---------------------------------------------|
| `test_pressure_arc_is_five_stages_in_order` | `test_pressure_arc.py` | Arc is exactly 5 stages, order `normal→early_dry→worsening_dry→drought→aftermath`, `activation_turn == index`, only `drought` stage has `world=="drought"` | Direct assertion on `PRESSURE_ARC` — no DSL, no `world_modifiers` field exists (Q6) |
| `test_pressure_signals_observational_not_output` | `test_pressure_arc.py` | T2/T3 prose describes rainfall, not harvest output; production in T2/T3 is still normal | Checks `PRESSURE_ARC[1].signal == "Grain remains abundant, but the rains have begun to fail."` and `PRESSURE_ARC[2].signal == "The dry spell persists. Farmers warn the next harvest is at risk."`; also asserts `world=="normal"` for both |
| `test_warning_is_useful_preparation_changes_drought_outcome` (**AC1+AC3, R5/R6, Q1/Q2/Q5**) | `test_pressure_arc.py` | Warning is **useful** — acting on it during T2–T3 changes the T4 drought consequence, isolating the warning (not T1) | Same seed `seed-8-useful`, **warning-isolated** histories sharing T1 `hold`: <br>• Prepared: `[hold, build_granary, buy_grain:20, hold, hold]` (heeds warning) <br>• Unprepared: `[hold, expand_farm, expand_farm, hold, hold]` (ignores warning) <br>Pre-condition: every `TurnResolution` `command` node `reason_code` is success (no `insufficient_*`/`no_route_access`) — i.e., fully affordable (Q2). <br>Post-condition (threshold-free, Q5): `prep_T4.price_value_effect != unprep_T4.price_value_effect` and at least one of `prep_T4.wealth_delta != unprep_T4.wealth_delta` or `prep_T4.next_state.player.inventory.grain != unprep_T4.next_state.player.inventory.grain`. Computed deltas for reference: price_value `+130` vs `-18` (delta 148 money), inventory 250 vs 200 — evidence, not gate. **Does not** assert which final wealth wins; no multi-seed sweep (Q6). |
| `test_drought_still_systemic_via_production_and_supply` (**AC2**) | `test_pressure_arc.py` | Drought reaches price only through production→supply→price, no direct price hack | For same state/capacity, `pressure=drought` farm_output < `pressure=normal` farm_output via `compute_farm_output`; trace for T4 has `pressure_stage` → `world` → `farm_output` → `supply` → `price` chain; **assert no edge `(pressure_stage, price)` or `(pressure_stage, home_price)` exists** — price parents must include `supply`/`farm_output` |
| `test_pressure_chain_determinism_and_inspectability` (**AC4, Q3**) | `test_pressure_arc.py` | Arc is deterministic and inspectable without DB; `current_pressure` contract correct | Same `seed+choices[5]` twice → byte-equal `state`, `rival_history`, trace; `pressure_for_turn(state.turn)` and `game.current_pressure` match `PRESSURE_ARC[turn]` when `not is_complete`; **`game.current_pressure is None` when `is_complete`** (Q3); trace each turn contains `pressure_stage` node with `reason_code == f"pressure:{pressure_id}:{stage}"`; `pressure_for_turn(5)` raises |
| `test_no_generic_dsl_smallness_structural` (**AC5, Q4, Q6**) | `test_pressure_arc.py` | System is small, no generic framework — structurally, not by line count | `len(PRESSURE_ARC)==5`, `PressureState.model_fields` has exactly 7 keys (no `world_modifiers`), `open("backend/app/engine/pressure.py").read()` contains no `"json"` / `"import random"` / `"weighted"` / `"sampler"` (file-text scan), imports are only `typing`/`pydantic`/`domain/types`; no weighted sampler |
| `test_pressure_to_world_is_only_via_stage` | `test_causal_trace.py` (extension) | Validates causal topology invariant | Already-covers `pressure_stage` → `world` edge; fail if any price node's `parent_ids` contains `pressure_stage` directly |
| `test_threat_only_on_worsening_not_early` | `test_deterministic_rivals.py` (probe) | Structured threat is stage-derived, graded correctly | `next_world_known_for_turn(1) is None` (early_dry does not threaten), `next_world_known_for_turn(2) == "drought"` (worsening does) — proves prose not parsed |
| `test_histories_fully_affordable` (sub-assertion of AC1+AC3 test, Q2) | `test_pressure_arc.py` | Guards AC1+AC3 instrument against clamped no-ops | For both histories, every turn's `command` node `reason_code` ∉ `{"insufficient_cash*","insufficient_storage","no_route_access"}` and `quantity` deltas equal requested (buy 20→20, expand→10). If any clamped, test fails on pre-condition with explicit message. |

**Expected evidence after implementation:**
- CLI per-turn headers show stages `normal → early_dry → worsening_dry → DROUGHT → aftermath` and signals escalate before impact; `6 MONTHS LATER` still shows wealth/inventory/price and `WHY?` drivers plus `MIRA`/`DARAN` headlines.
- Trace dump (verbose) includes chain `pressure_stage:pressure:northern_drought:worsening_dry → world:drought → farm_output:drought_reduced_yield → home_supply → home_price → … → wealth`.
- Same seed+choices second run byte-equal (`final_wealth`, `rival_history`, trace).
- `test_warning_is_useful_preparation_changes_drought_outcome` passes with warning-isolated, fully affordable histories (T4 price_value `+130` vs `-18`, inventory 250 vs 200); `test_no_single_policy_dominates_all_metrics` still passes but is no longer the instrument for Section 8.
- No existing test file edited to relax an assertion (verified by diff + grep for `abundant`/`"Surplus"`).

---

## Risks / Rollback

- **Risk:** Changing `TURN_SPECS` signals (T2 surplus wording) breaks substring checks like `assert "abundant" in TURN_SPECS[1].signal.lower()` (`test_five_turn_prototype.py:365`). **Mitigation:** R4 wording retains `"Grain remains abundant"` as prefix, so `"abundant"` substring still passes. Keep title `"Surplus"` exactly. Verify with `grep -n abundant backend/tests/*.py` before merge.

- **Risk:** Changing `resolve_turn` signature breaks existing call sites (`prototype.py`, `demo.py`, tests). **Mitigation:** Update all call sites in same commit to pass `PressureState` instead of `world`. `world` is a field on the pressure object, so kernel change is one line (`world = pressure.world`). No churn in `GameState`.

- **Risk:** Adding `kind="pressure"` trace node could be mistaken for needing a validator change. **Mitigation:** Do not change `trace.py` — verified fallback admits `delta=None` parentless nodes. Add a regression that would fail if someone later tightens the validator.

- **Risk:** Rivals that previously keyed on `next_world_known=="drought"` only on idx 2 still work, but adding `early_dry` stage could be confused with threat. **Mitigation:** Keep existing boost tiers unchanged; only `worsening_dry` triggers drought threat, `early_dry` is `None` (new test proves it).

- **Risk (new grill):** Affordable-history pre-condition could hide a future cost change that makes histories unaffordable. **Mitigation:** Test explicitly asserts affordability (Q2) so a cost increase fails the pre-condition with a clear message rather than silently testing a no-op.

- **Rollback:** Revert `prototype.py` to re-introduce hard-coded `TURN_SPECS` and ignore `pressure` module; remove `pressure_stage` node emission from `turn.py`; restore `resolve_turn(state, command, world, ctx)` signature. No `GameState` migration needed because no field was added.

---

## Decisions Settled (R8 + grill)

This plan is decision-complete. The two choices previously listed under "Open Questions" are resolved, and the grill's forced decisions are now locked:

1. **GameState field vs pure derivation:** Resolved per R1 — no `GameState.pressure_stage` field. Pressure is derived from `turn` via `pressure_for_turn` and surfaced via `game.current_pressure` + trace. `current_pressure` is `None` when complete (Q3).

2. **Signal prose for T2 early dry:** Resolved per R4 — `"Grain remains abundant, but the rains have begun to fail."` (observational rainfall, not output), title remains `"Surplus"`.

3. **Warning isolation (Q1):** Instrument shares T1 `hold`, diverges only at T2–T3 warning stages.

4. **Affordability (Q2):** Both histories fully affordable (hold+granary+buy20 cost 387, hold+farm+farm cost 1000), no clamped commands; test asserts affordability.

5. **Smallness (Q4):** Structural checks, not line count.

6. **Threshold (Q5):** Threshold-free inequality on `price_value_effect` (and wealth/inventory), not magic-number gated.

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

## What Changed Versus the Draft and Versus Rev 2

### Versus original draft (R1–R8 already in Rev 2, reiterated in Rev 3)

| Area | Draft | Rev 2/Rev 3 | Review item |
|------|-------|-------------|-------------|
| `GameState.pressure_stage` field | Added with default `"normal"` | **Removed** — no canonical field; pressure derived from `turn` | R1 BLOCKING |
| `resolve_turn` signature | `resolve_turn(state, command, world, ctx)` unchanged | `resolve_turn(state, command, pressure: PressureState, ctx)` deriving `world` internally | R1 BLOCKING |
| `world_modifiers` on `PressureState` | `Mapping[str,int]` typed but unused | **Deleted** — 7 fields exactly | R2 BLOCKING |
| Trace pressure node | `after=stage_hash?` contemplated | `before/after/delta = None`, `kind="pressure"`, no hash | R3 BLOCKING |
| `trace.py` validator | Proposed adding `"pressure"` to `allowed_empty_roots` | **No change** — existing fallback already admits it (verified at 149–165/170–173) | R3 BLOCKING |
| T2 prose | "weak harvest hints" (implies output fell) | **"Grain remains abundant, but the rains have begun to fail."** (rainfall, not output) | R4 BLOCKING |
| T2 title | "Surplus / Early Dry" | **"Surplus"** (unchanged, preserves `test_turn_specs_length_and_titles:368`) | R4 BLOCKING |
| AC3 evidence | 3 policies → different `final_wealth` (already passes today) | **T4 drought result** between two T1–T3 preparation histories → differing inventory/wealth-decomposition | R5 BLOCKING |
| AC1 evidence | Inspect `current_signal` before T4 | **Folded into R5 test** — warning proven useful by preparation → T4 divergence | R6 |
| CLI commands | `python -m app.engine.cli` + non-shipping smoke policy | `uv run --project backend python backend/app/cli.py` + `build_granary,secure_route,buy_grain,hold,ship_grain` | R7 |
| Open Questions | Two unresolved choices | **Removed** — both settled (R1+R4) | R8 |
| Scope | — | No strategy-win-rate or multi-seed sweep; Section 9 deferred | R5 keep-as-is |

### What the grill changed (Rev 2 → Rev 3) — concise

| Grill Q | Rev 2 | Rev 3 | Impact |
|---------|-------|-------|--------|
| **Q1 Warning isolation** | Histories differed at T1 (normal): `prep=[granary,buy,hold…]` vs `unprep=[farm,farm,farm,hold…]` — T4 divergence confounds pre-warning vs warning effect | **Warning-isolated:** share T1 `hold`, diverge only at T2–T3 (warning stages): `prep=[hold,granary,buy:20,hold,hold]` vs `unprep=[hold,farm,farm,hold,hold]` | AC1/AC3 now proves the warning mattered, not the opening |
| **Q2 Affordability** | `unprep` 3× farm — third expand was `insufficient_cash_for_expand` no-op (1000 cash only affords 2×500) — computed via FiveTurnGame. No affordability guard | **Both histories fully affordable** (granary 300 + buy 87 = 387 leftover 613; farm 500+500=1000 leftover 0) at surveyed prices; test asserts `reason_code ∉ insufficient_*` and requested deltas achieved | Instrument not polluted by clamped no-ops |
| **Q3 `current_pressure` when complete** | Undefined; `pressure_for_turn(len(history))` would OOR at 5 | **`current_pressure: PressureState \| None`** — `None` when `is_complete` (mirrors `current_spec`), else `pressure_for_turn(len(history))`; `pressure_for_turn(5)` raises | No `IndexError` on completed game; inspectability contract explicit |
| **Q4 Line-count test** | `pressure.py <60 lines` — brittle proxy | **Structural smallness:** `len(PRESSURE_ARC)==5`, 7-field exactness, file-text scan for no `json`/`random`/`weighted`/`sampler`, imports limited | Catches loader addition regardless of formatting; no spurious breakage on comments |
| **Q5 Threshold hedging** | `"like ≥50 money or ≥5 grain"` — hedged magic number | **Threshold-free:** `prep_T4.price_value_effect != unprep_T4.price_value_effect` plus inventory/wealth inequality; deltas (148 money, 50 grain) cited as evidence not gate | No magic number to tune; survives price-parameter tweaks |
| **Q6 Scope creep** | Already deferred Section 9, but threshold language bordered on balance gate | **Explicit guard:** no `json`/`sampler`/`content_version`/`world_modifiers`; AC1+AC3 is one seed, one comparison, not multi-seed sweep | Harder to accidentally reintroduce Section 9/15 |
| **Q7 Weakening tests** | Already "no relax", but not grep-guarded | **Added grep guard** for `abundant`/`"Surplus"` substrings and checklist to diff `test_five_turn_prototype.py:365,368` before merge | Prevents silent weakening |

**ESCALATE:** Nothing. All grill questions settled from code/computed evidence; no product-owner decision needed.

Nothing in the "keep as-is" list was dropped. No turn-kernel rewrite, no new abstraction beyond the one `pressure.py` helper, no Section 9/15 material.
