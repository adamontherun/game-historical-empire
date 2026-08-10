# Section 8 plan — consolidated review (round 2, against Rev 3)

Rev 3 (post-grill) was reviewed by ChatGPT against the pushed branch. Reconciled against
Rev 3's own grill findings below — two items ChatGPT raised were already fixed
independently by Muse's self-grill (noted as moot). Five items are real and unaddressed.
Apply all five as Rev 4, then proceed directly to implementation.

---

## F1 — The AC1/AC3 instrument still confounds "heeded the warning" with "chose a different production lever" (BLOCKING, highest priority)

Rev 3's instrument (Decision/Q1 fix) already solved the *timing* confound (both histories
now share T1). It did not solve a *mechanism* confound that remains in the same test:

```
prepared:   [hold, build_granary, buy_grain:20, hold, hold]
unprepared: [hold, expand_farm,   expand_farm,   hold, hold]
```

`expand_farm` changes `farm_capacity`. `farm_capacity` drives `farm_output`
(`actor.compute_farm_output`), which drives `home_supply`
(`signal_next = max(0, signal+farm_output-demand)`), which drives `home_price`. The
unprepared history enters T4 with capacity 30 vs the prepared history's capacity 10 — so
even under the identical T4 drought, the two runs do **not** face the same market supply
or price. The test's own computed evidence shows this: `unprep_iso` T4 price is still
falling (`price_value_effect -18`) while `prep_iso`'s is rising (`+130`) — a signature of
divergent supply paths, not purely of divergent player exposure to one shared shock.

This means the test — as specified — could pass for reasons that have nothing to do with
Section 8's pressure/warning system. Comparing a farm-heavy policy to a storage-heavy
policy under a scripted T4 drought is exactly what `test_no_single_policy_dominates_all_metrics`
(`test_five_turn_prototype.py:153`) already does without any pressure arc. AC1/AC3 needs
to prove the warning specifically mattered, not that policies differ.

**Fix:** Verified structurally — neither `buy_grain` nor `build_granary` appears as an
input to `home_supply`'s signal formula; only `farm_output` (via `farm_capacity`) does.
So if neither compared history calls `expand_farm`, T4 market conditions become
*provably* identical between the two runs. Change the instrument to:

```
prepared:   [hold, build_granary, buy_grain:20, hold, hold]   # unchanged
unprepared: [hold, hold,          hold,          hold, hold]  # literal no-response
```

Add a new **pre-condition equality assertion** proving isolation actually holds, not just
asserting it by construction:

```
prep_T4.next_state.market.supply == unprep_T4.next_state.market.supply
prep_T4.next_state.market.current_price == unprep_T4.next_state.market.current_price
# (equivalently: assert equal farm_output at T4 in both traces)
```

Then the existing post-condition (threshold-free inequality on `price_value_effect` /
`wealth_delta` / inventory) proves that with an *identical* market shock, the player's
prior response to the warning is what produced a different outcome — the actual AC1/AC3
claim. Recompute the evidence numbers for the new histories and cite them in the plan
(replacing the stale `+130`/`-18` figures, which were for the old confounded histories).

## F2 — `PressureState` still permits the invalid combination R1 was meant to eliminate (BLOCKING)

Rev 3's Decision 1/2 correctly removed `GameState.pressure_stage` and made `resolve_turn`
derive `world` from the passed `PressureState`. But `PressureState` itself has no
constraint tying `stage` to `world` — this still type-checks and validates:

```python
PressureState(stage="early_dry", world="drought", ...)
```

The invalid state R1 was meant to eliminate didn't get removed, it moved inside one
object. Add a model validator enforcing the biconditional for this prototype's arc:

```
stage == "drought"  <=>  world == "drought"
every other stage   =>   world == "normal"
```

Add regression tests asserting `PressureState` construction raises for at least:
`early_dry`+`drought`, `worsening_dry`+`drought`, `drought`+`normal`.

## F3 — `causal_source_id` and the trace `reason_code` are two code paths computing one fact (should-fix)

`PressureState.causal_source_id` defaults to `f"pressure:{pressure_id}:{stage}"`
(Decision 1 / Work Plan §1). Separately, `turn.py`'s pressure trace node reconstructs the
identical formula again (Decision 5: `reason_code=f"pressure:{pressure.pressure_id}:{pressure.stage}"`)
instead of reading the field. They agree today only because both happen to implement the
same formula — nothing prevents a `PRESSURE_ARC` entry from overriding `causal_source_id`
with a different value and silently disagreeing with the trace. This is the same
single-source-of-truth bug class R1 fixed elsewhere, recurring at a smaller scale.

**Fix:** in `turn.py`, set `reason_code = pressure.causal_source_id` directly — do not
recompute the format string. Do not let `PRESSURE_ARC` entries override
`causal_source_id` from its default (or add a validator enforcing it matches the formula
if entries do set it explicitly).

## F4 — File location for `PressureStage`/`PressureState` is still hedged (should-fix, cheap)

Decision 1 and Work Plan §1 both still read "in `backend/app/domain/types.py` (or new
`backend/app/domain/pressure.py` re-exported)". A decision-complete plan (R8) should not
leave this open. Use `backend/app/domain/pressure.py`, re-exported via
`backend/app/domain/__init__.py` — pressure is a distinct domain concept from the Section
2 economic primitives already in `types.py`, and this keeps `types.py` from becoming a
catch-all.

## F5 — Validation Plan should state the final repo gates explicitly (should-fix, housekeeping)

The Validation Plan lists test/lint/type/format-check and targeted checks, but doesn't
state the section-closeout sequence explicitly, even though it's already required by this
repo's standing contract (`AGENTS.md`, `BUILD_SPEC.md` §0.3/§0.4). For a long headless
execution run, spell it out as the literal last step so nothing is left to inference:

1. All gates green (`make test lint type format-check`).
2. `graphify update .`; commit regenerated tracked artifacts if changed.
3. Sync `STATE.md` to actual HEAD: exact test count, new `pressure.py` module,
   `current_pressure`/`PressureState` contract, current gate results.
4. Add the next sequential `DECISIONS.md` entry recording that pressure is
   turn-derived/session-authored (not canonical `GameState`), matching R1/F2.
5. Only then flip `BUILD_SPEC.md` Section 8 `Status:` line to `COMPLETE`.
6. Commit, push. Stop — do not begin Section 9.

---

## Already resolved — no action (convergence check)

- **`current_pressure` is `None` when the game is complete.** ChatGPT's Rev 2 review
  flagged this as unresolved; Rev 3's Decision 7 (from Muse's own grill Q3) already
  landed on exactly this design independently, including `pressure_for_turn(5)` raising
  and the AC4 test guarding the comparison to `not is_complete`. Both reviewers converged
  on the same fix without seeing each other's work — treat as settled.
- **The `<60 lines` smallness test.** Already replaced with structural checks (field
  count, no-loader file-text scan, import allowlist) by Muse's own grill (Q4) before
  ChatGPT's Rev 2 review was read. Settled.
