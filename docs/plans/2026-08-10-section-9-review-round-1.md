# Section 9 plan — consolidated review (round 1)

The plan is well-structured and the self-grill correctly identified the degenerate-sweep
problem (Q6). But empirical testing against the actual engine shows **Decision 4's fix
does not work**, and surfaces a much larger finding that changes what Section 9 is for.

All numbers below were produced by running the real `FiveTurnGame`, not reasoned about.

---

## E1 — The engine is completely seed-invariant (confirms Q6, more strongly than stated)

`turn.py:146-164` calls `rng_for` twice, but **both draws are discarded**:

```python
_ = rng.random()        # "consume deterministically; do not drive core price"
_ = rng_route.random()
```

Nothing in turn resolution depends on the seed. Only `random_legal` varies. The plan's
diagnosis is correct and the underlying concern is real.

## E2 — Decision 4's ±2 supply perturbation does not fix the degeneracy (BLOCKING)

Sweeping `default_start_state().market.supply` across the full ±2 range, holding policies
fixed:

| supply Δ | production | storage | trade | cash | winner |
|---|---|---|---|---|---|
| −2 | 548 | 1774 | 1530 | 1916 | cash |
| −1 | 548 | 1769 | 1527 | 1912 | cash |
| 0 | 548 | 1763 | 1523 | 1909 | cash |
| +1 | 548 | 1758 | 1520 | 1905 | cash |
| +2 | 548 | 1752 | 1516 | 1901 | cash |

Total wealth movement across the entire perturbation range is ~0.3%, and **the winner
never changes**. Win-rate would be 100% for one policy across all 200 seeds, so AC2 stays
exactly as unfalsifiable as it was without the perturbation. Decision 4 does not achieve
its stated purpose.

## E3 — A wider start-state band does not fix it either (rules out the obvious alternative)

I proposed widening to a multi-dimensional band. Tested across 18 configurations —
cash ∈ {700, 1000, 1400} × supply ∈ {85, 100, 115} × demand ∈ {85, 95}:

**`cash` (hold×5) won all 18.** Distinct winners across the whole band: `{cash}`.

So the problem is not the perturbation's magnitude or dimensionality. Widening the band
is not the fix, and my own round-1 suggestion is withdrawn.

## E4 — The real finding: the game currently has a universally dominant strategy, and it is "do nothing" (BLOCKING — changes Section 9's scope)

Re-tested with affordability-aware policies where **every command executes cleanly** (no
`insufficient_*`, verified via each turn's `command` node `reason_code`), so this is not
the affordability confound the plan warns about:

| policy | commands | wealth |
|---|---|---|
| **cash_hold** | hold ×5 | **1909** |
| mixed | granary, buy 20, hold, hold, hold | 1746 |
| storage | granary ×3, hold, hold | 1690 |
| trade | secure_route, buy 20, hold, hold, ship 20 | 1448 |
| production | expand_farm ×2, hold ×3 | 548 |

Doing nothing beats every active strategy. Expanding the farm is *ruinous* — 3.5× worse
than idling.

The mechanism is economically coherent, which is what makes it a real design problem
rather than a bug: expanding farm capacity raises `farm_output`, which raises
`home_supply`, which *lowers* `home_price`. The player floods their own market and
crashes the price they sell into, having spent all their cash to do it. Meanwhile holding
retains cash and lets the drought revalue existing inventory upward.

This matters beyond Section 9. BUILD_SPEC's core loop is *observe → choose → commit →
experience consequences*, and §29 defines success as the player wanting to make one more
decision. Right now the optimal play is to make **no** decisions. The five-turn horizon is
too short for any investment to pay back, and production actively self-harms.

### What this means for the plan

Section 9's stated goal is "Detect obvious dominant strategies and broken economic ranges
**before building the UI**", and its stop condition is "stop when the prototype is stable
enough that UI playtesting is more valuable than additional headless tuning." Detection is
working — the harness would immediately and correctly report failure. But the plan treats
AC2 purely as a test gate and has no provision for what happens when it fails, which it
will on first run.

So the plan must decide, explicitly:

1. **Does Section 9 include economic rebalancing, or only detection + reporting?** The
   spec's framing ("no universally dominant strategy" as a *target*, "additional headless
   tuning" in the stop condition) reads as: tuning is in scope. Recommend Section 9 covers
   detection **and** the tuning needed to clear its own gate.
2. **The balance gate must not be a hard-failing unit test on first implementation.**
   Land the harness and its report first, with the dominance thresholds evaluated and
   *reported* (exit code 2, per the plan's own design). Convert the thresholds into a
   blocking test only once the economy actually passes them. Otherwise the section cannot
   be committed green, and the temptation becomes loosening thresholds to go green — the
   exact failure mode BUILD_SPEC §0.4 forbids.
3. **Do not fix this by nerfing the drought or hand-tuning until `cash` loses.** The
   target is no *universally* dominant strategy, not equal outcomes (spec: "Do not
   optimize for equal strategy outcomes"). Candidate levers to investigate, in
   plausibility order: investment payback within a 5-turn horizon (costs vs
   `YIELD_PER_CAPACITY=10`), the price impact of a single producer's own output on the
   market they sell into, and whether idle cash should carry any opportunity cost.

## E5 — Decision 4 should be replaced, not tuned

Given E2 and E3, the ±2 perturbation adds a harness-owned divergence from the shipped
game's actual start state while achieving nothing. Remove it. Seed variation should come
from `random_legal` only, and the batch should be honest that with a fixed authored arc,
deterministic policies are seed-invariant by construction — that is a property of the
design, not a defect to paper over.

If genuine world diversity is wanted later, the authored way to get it is varying the
pressure arc (e.g. drought at T3 vs T4 vs T5) — but that is Section 15 content work and
explicitly out of scope here. Do not add it now.

## E6 — Decision 6's `win_rate >= 0.05` floor is unsound as written

The gate requires every non-random policy to win ≥5% of seeds. With deterministic
policies on a fixed arc, every policy's win-rate is exactly 0 or 1 — there is no
intermediate value available. The floor can therefore never be satisfied by four of five
policies regardless of balance quality.

Replace win-rate-based "dead strategy" detection with a **median-ratio** test, which is
well-defined under determinism: a policy is dead if its median final wealth is below some
fraction of the overall median. The plan already proposes `median >= 0.70 × overall_median`
— keep that and drop the win-rate floor. Note that under the current economy
`production` at 548 vs an overall median near 1690 would correctly flag as dead.

---

## Keep as-is

- Harness in `engine/harness.py`, CLI via `backend/app/cli.py --balance`, markdown + stable
  JSON output with exit code 2 on threshold breach.
- No bare-string `resolve_turn` overload; use `PRESSURE_NORMAL` / `PRESSURE_DROUGHT` /
  `pressure_for_world`. Keep the grep guard.
- Paired-seed design and per-policy `insufficient_* == 0` affordability assertions —
  well-motivated, and my own first-pass policies hit exactly that confound (3 of 5 turns
  rejected), which is good evidence the guard is needed.
- Determinism proven by double-run equality rather than a golden file.
- Integer-only, no global random, engine purity.
