# Section 8 implementation — consolidated review (round 3, against commit 28a0963)

Both reviewers independently reached the same merge call: **the core implementation is
good, but do not merge this HEAD.** Fix G1–G4, then merge.

**Independently verified green** (Claude re-ran all gates, did not trust the report):
`make test` 122 passed · `make lint` clean · `make type` 0 errors/0 warnings ·
`make format-check` 30 files formatted. The completion report's numbers are accurate.

**Confirmed correct and not to be touched:** the `stage`↔`world` biconditional (F2);
`causal_source_id` genuinely single-source (F3); the five-stage arc and `activation_turn`
indexes; `current_pressure` correctly `None` after completion; the causal graph
`pressure_stage → world → farm_output → supply → price` with no pressure→price shortcut;
and the AC1/AC3 test, which now genuinely isolates preparation by asserting equal T4
farm_output/supply/price *before* asserting divergence. That test is the strongest thing
in this section — do not weaken it.

---

## G1 — Remove the `PressureState | str` legacy shim (BLOCKING)

`resolve_turn(state, command, pressure: PressureState | str, rng_context)` accepts a bare
`"normal"`/`"drought"` string and synthesizes `pressure_id="legacy"`, `activation_turn=0`.
The Rev 4 plan said to update all call sites; instead the signature was widened so ~72
test call sites needed no editing. This was not disclosed in the completion report.

Why this is a blocker, not a follow-up:

- It re-admits the exact bare-`world` representation R1/F1 existed to eliminate, and lets
  a caller bypass the new F2 biconditional validator entirely:
  `resolve_turn(state_at_any_turn, cmd, "drought", ctx)` participates in no `PRESSURE_ARC`.
- The synthetic `activation_turn` is always `0` regardless of the state's actual turn, and
  the resulting trace reads `pressure:legacy:drought` — which does not name the authored
  stage that caused the world condition. That is a causal-trace truthfulness defect, the
  precise class of bug Sections 4/7/8 exist to prevent.
- **Decisive:** Section 9 is a headless balance harness — it adds many new simulation
  callers. Leaving the shim converts an intentionally-removed API into the path of least
  resistance for the very next section. Fix it now or it becomes permanent.
- It forces `# type: ignore[union-attr]` at the pressure-node construction site; removing
  the union removes those suppressions.

There are no external API consumers yet (Section 10 hasn't happened), so this is the
cheapest it will ever be. Delete the `str` branch, type the parameter as `PressureState`,
and migrate the test call sites. Migration is mechanical: expose reusable
`PRESSURE_NORMAL` / `PRESSURE_DROUGHT` constants (or a small test helper) so call sites
become e.g. `resolve_turn(state, cmd, PRESSURE_DROUGHT, ctx)`. Delete the now-unneeded
`# type: ignore[arg-type]` comments those call sites carry.

Do **not** weaken any existing assertion while migrating. This is a mechanical signature
migration only — no test's meaning may change.

## G2 — Work Plan §6 (CLI + StrategicSummary stage display) was never implemented (BLOCKING)

Rev 4 Work Plan step 6 specified that `backend/app/cli.py` display the pressure
stage/title/signal per turn header, and that `StrategicSummary.format()` append the stage
per turn (e.g. `T2 Surplus [early_dry]`). Neither was done —
`grep -ci 'pressure\|stage' backend/app/cli.py` returns **0**.

This was an approved, planned step that was silently skipped while the completion report
listed the section COMPLETE with all acceptance checks PASS. The player-visible signals
still render (they flow through `current_signal`), so no acceptance criterion actually
fails — but the plan was not followed and the report did not say so.

Implement step 6 as specified. When complete, the CLI turn header must show the stage
progression across a run, and `StrategicSummary.format()` must include the per-turn stage.

**Process note for future sections:** if a planned step is intentionally skipped or
deferred, say so explicitly in the completion report under "Did not implement." Reporting
a section COMPLETE while a planned step is silently missing is the failure mode the
report template exists to prevent.

## G3 — STATE.md contains a provably false provenance claim (BLOCKING)

STATE.md line ~96 claims the canonical five-turn prototype run emits
`pressure_stage:pressure:legacy:normal / pressure:northern_drought:*`.

The `pressure:legacy:*` half cannot happen. `prototype.py:330` passes
`pressure = pressure_for_turn(idx)`, i.e. real authored `PRESSURE_ARC` entries with
`pressure_id="northern_drought"`, for every turn. The prototype can never emit a legacy
pressure id.

Correct this line to reflect what the run actually emits. Once G1 lands, remove every
remaining STATE.md reference to the legacy string shim (the `turn.py`, `demo.py`, and
"Last known green" entries all mention it). Re-verify the STATE.md description against
actual behavior rather than against the plan's intent — this repo's freshness contract
makes a stale or impossible handoff claim a blocking defect.

## G4 — DECISIONS.md 012 contradicts its own rationale (BLOCKING)

Entry 012's stated decision is that `resolve_turn(..., pressure: PressureState, ...)` and
single-source pressure are the durable design — but item (4) then permanently blesses the
legacy bare-string shim in the same breath, and the Rationale reasserts "single source of
truth for `world`." As written the entry is internally incoherent.

Once G1 removes the shim, delete that parenthetical. The decision then says what it means.

## G5 — Pressure node label should derive from stage, not title (should-fix)

`turn.py:236` sets `label=pressure.title`. T2's title is deliberately `"Surplus"`
(preserved to keep `test_turn_specs_length_and_titles` green), so the causal node for the
`early_dry` stage is labelled "Surplus" — presentation copy standing in for a causal
description. Derive the causal label from `stage` (e.g. `early_dry` → "Early dry
conditions", `worsening_dry` → "Worsening dry conditions"), leaving `title` as
presentation copy. Both are legitimate fields; they should not be conflated.

## G6 — Prefer a `mode="before"` validator over `object.__setattr__` (should-fix, minor)

`pressure.py` fills the `causal_source_id` default via
`object.__setattr__(self, ...)` inside a `mode="after"` validator, mutating a frozen model
post-validation. It works, but a `mode="before"` validator that populates the field prior
to construction expresses the same intent without writing through the frozen guarantee.

---

## Closeout (unchanged from F5)

After G1–G6: rerun all four gates, `graphify update .` and commit regenerated artifacts,
re-sync STATE.md to true HEAD behavior, ensure BUILD_SPEC Section 8 status reflects
reality, commit and push. Then stop — Section 9 is a separate session.
