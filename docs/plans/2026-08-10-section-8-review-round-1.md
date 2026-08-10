# Section 8 plan — consolidated review (round 1)

Two independent reviews (Claude + ChatGPT) of
`docs/plans/2026-08-10-section-8-pressure-driven-event-arc.md`.
Both reviewers say: **direction is right, revise before implementing.**
The items below are the reconciled, de-duplicated set. Apply all of them.

---

## R1 — Pressure must be the single source of truth for the turn (BLOCKING)

The plan currently allows three representations of one fact: `PRESSURE_ARC`,
`GameState.pressure_stage`, and the separate `world` argument to `resolve_turn()`.
That permits invalid states such as `pressure_stage="early_dry"` with `world="drought"`.

**Do:**
- Do **not** add `pressure_stage` / `pressure_id` to `GameState`. Pressure is fully
  determined by the authored arc + turn number; storing it canonically duplicates
  information and creates a second source of truth.
- Change `resolve_turn` to receive the `PressureState` step instead of a bare `world`,
  and derive `world = pressure.world` internally.

```
FiveTurnGame
  -> pressure_for_turn(idx) -> PressureState
  -> resolve_turn(state, command, pressure, rng_context)
  -> world = pressure.world
```

- Inspectability for AC4 comes from `pressure_for_turn(state.turn)`,
  `game.current_pressure`, and the causal trace node. That is sufficient; no new
  canonical field is needed.

## R2 — Delete `world_modifiers` (BLOCKING)

The plan proposes adding it "typed but unused for Section 8." That is speculative
scaffolding and is exactly what BUILD_SPEC §31 forbids. BUILD_SPEC §8 lists it as a
*possible* field, not a required one.

`PressureState` fields are exactly:
`pressure_id, stage, activation_turn, world, signal, title, causal_source_id`.

Validate that `activation_turn` equals the step's index in `PRESSURE_ARC`, so tuple
position and `activation_turn` can never disagree. Parameterized modifiers belong in
Section 15, when a real mechanic consumes them. The Python drought rule
(`actor.compute_farm_output`) stays authoritative.

## R3 — Trace root: no numeric hash, and no validator change (BLOCKING)

Drop the plan's `after=stage_hash?` idea. There is no economic numeric delta associated
with "worsening_dry"; do not invent one.

Emit exactly:

```
id          = "pressure_stage"
kind        = "pressure"
label       = "Worsening dry conditions"     # per stage
reason_code = "pressure:northern_drought:worsening_dry"
before/after/delta = None
parent_ids  = ()
```

**Do not** add `"pressure"` to `allowed_empty_roots` in `trace.py`, and do not otherwise
loosen `_validate_dag`. This was checked against the current code: the existing fallback
at `trace.py:170-173` already admits a parentless node whose `delta` is `None`, because
`"pressure"` is not in the must-have-parents kind list at `trace.py:149-165`. The node
above validates as-is. Leave the DAG invariant untouched.

Chain to produce:

```
pressure_stage -> world -> farm_output -> home_supply -> home_price -> ... -> wealth
```

Add a test asserting there is **no** edge from `pressure_stage` directly to any price
node — the drought must reach price only through production and supply.

## R4 — T2/T3 prose must be mechanically truthful (BLOCKING)

T2 keeps `world="normal"`, so production in T2 is completely normal. The plan's proposed
"weak harvest hints" wording implies the harvest itself weakened. It did not.

Use observational prose about *rainfall*, not about *output*:

```
T2 - early_dry
"Grain remains abundant, but the rains have begun to fail."

T3 - worsening_dry
"The dry spell persists. Farmers warn the next harvest is at risk."

T4 - drought
"Drought cuts farm output."
```

Two escalating warnings, with warning -> preparation -> actual production shock kept
distinct.

**Keep the existing T2 title "Surplus".** Do **not** relax
`test_turn_specs_length_and_titles()` (`backend/tests/test_five_turn_prototype.py:368`)
or any other existing assertion to accommodate new prose. BUILD_SPEC §0.4 forbids
weakening acceptance criteria to pass. Add *new* stage assertions instead of editing old
ones. The T2 surplus remains true — it is emergent from `signal + harvest > demand`.

## R5 — AC3 must test preparation, not balance (BLOCKING)

The plan's AC3 evidence ("3 policies -> different final wealth") already passes today via
`test_no_single_policy_dominates_all_metrics()`
(`backend/tests/test_five_turn_prototype.py:153`) with no pressure system at all. As
written, Section 8 could ship with the arc doing nothing and that test would still pass.

The plan also drifts into Section 9 territory by expecting "storage-heavy outperforming
farm-heavy" and talking about no policy dominating across seeds. Strategy win rates and
multi-seed balance are explicitly Section 9.

Section 8 must prove only:

```
same authored drought
+ different legal preparation during the warning stages
-> materially different drought exposure/consequence
```

Compare the **T4 drought result** between two legal T1-T3 preparation histories, asserting
differences in quantities such as inventory retained, the wealth-effect decomposition,
cash exposure, or price revaluation. Do **not** assert which strategy wins. Do **not** add
multi-seed sweeps or win rates.

## R6 — AC1 needs the same instrument

"Inspect `current_signal` before turn 4" only proves a warning *exists*, not that it is
*useful*. Define useful operationally: the warning is actionable, and acting on it changes
the T4 outcome — proven by the R5 test. Fold AC1's evidence into that test.

## R7 — Fix the validation commands

- The CLI is `backend/app/cli.py`. `python -m app.engine.cli` does not exist. Use the
  established invocation: `uv run --project backend python backend/app/cli.py ...`
- The smoke policy `build_granary,build_granary,buy_grain,hold,ship_grain` never secures
  the route, so its final `ship_grain` is guaranteed to be blocked and proves nothing.
  Replace it with a policy that includes `secure_route` before shipping.

## R8 — The plan must be decision-complete

Remove the "Open Questions" section. Both listed choices are settled above: no `GameState`
field (R1), and the T2 prose is fixed (R4). A plan that ships with open implementation
choices is not decision-complete.

---

## Keep as-is (both reviewers agree)

- One hard-coded five-stage arc; no DSL, no JSON loader, no weighted sampler.
- Five turns, not six — protects "exactly five decisions."
- `TURN_SPECS` derived from `PRESSURE_ARC` for temporary compatibility, with
  `PRESSURE_ARC` stated explicitly as the single source.
- Only T4 actually changes production; T5 aftermath emerges from carried economic state.
- Structured threat derived from `stage == "worsening_dry"`, never from parsing prose.
- Reuse `actor.compute_farm_output`; no new RNG or event sampler.
