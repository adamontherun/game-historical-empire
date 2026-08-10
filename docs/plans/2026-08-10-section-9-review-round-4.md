# Section 9 — review round 4 (consolidated, final) — SUPERSEDES rounds 2 and 3

Reconciles my own measurements with the second reviewer's independent review of the pushed
branch. **Both of my earlier route proposals were wrong**, in opposite directions, and the
real answer is smaller than either. Read this as the authority.

Muse's round-2 implementation is **genuinely green** — independently re-run: `132 passed`,
ruff clean, pyright `0 errors`, format clean, `hold rank 3/5`. The work below is what the
matched controls exposed *after* that, not a rejection of it.

---

## The one technique that produced every finding in this round

For each strategy's defining investment, run **the identical policy with that single command
suppressed**. Not against `hold` — against itself minus the one decision. Everything below
came from that, and every claim about an investment's value must now be reported that way.

## R1 — The granary does not repay its cost, and `test_build_granary_not_worthless` cannot see it

`build_granary` incremental value, measured with `policy_storage_heavy` vs itself with
`build_granary` suppressed, at the shipped config:

```
with    : ['build_granary', 'buy_grain:80', 'hold', 'hold', 'sell_grain:150']
without : ['hold',          'buy_grain:60', 'hold', 'hold', 'sell_grain:130']
build_granary: -21 on 300 cost = -7.0% return  ->  DOES NOT REPAY
```

The shipped test only asserts `storage_capacity < start_grain + farm × YIELD × 5`. That is
necessary but **not sufficient**: a granary can have usable headroom and still be a trap.
`build_granary` was in exactly the state `secure_route` was in before this section — the
defining move of a named archetype, strictly value-destroying.

## R2 — But the granary is not broken. `policy_storage_heavy` is a third strawman

Rounds 2 and 3 caught two strawman policies. There is a third, and it is the reason for R1:
the policy **buys grain to fill space that the free harvest was going to fill anyway**, so
the granary ends up storing purchased grain (~2.6/unit of appreciation) instead of free
harvest (~8.5/unit).

A storage policy that builds capacity when the incoming harvest would overflow, and buys
only into space the harvest will not claim, flips it with **no constant tuning at all**:

| config | production | storage | trade | hold | granary | route |
|---|---|---|---|---|---|---|
| shipped constants, shipped policy | 2290 | 1974 | 2347 | 2109 | **−21** | +280 |
| shipped constants, **fixed policy** | 2290 | **2347** | 2241 | 2109 | **+56** | +174 |

Keep `BUILD_GRANARY_COST = 300` and `BUILD_GRANARY_DELTA = 50` exactly as they are. Sweeping
them was unnecessary — a policy bug was masquerading as an economy bug, which is the same
mistake DECISIONS 015 made in the other direction.

## R3 — Revert `route.capacity` to 20. Transport cost was the entire route fix

Round 2 named capacity as the binding constraint. That was measured without the control and
is **wrong**. With the matched no-route control, at transport 300:

| route capacity | route incremental value | return on 400 cost |
|---|---|---|
| **20 (original)** | **+174** | **43.5%** |
| 40 | +311 | 77.8% |
| 60 (Muse shipped) | +280 | 70.0% |

The route repays at the **original capacity 20**. Raising it to 60 was never needed. Revert
`route.capacity` to `20` and keep only `transport_cost_per_unit` 800→300.

Smaller transactions also keep the price-taking approximation (R5) honest, so 20 is the
conservative choice as well as the smaller diff.

## R4 — Retract round 3's River Town rescale entirely

Round 3 proposed `river_market.supply` 80→200 and `demand` 130→350, justified as "shipments
are 20% of the market's supply instead of 75%". **That justification is invalid.**
`MarketState.supply` is an availability *signal/index*, not conserved physical stock;
`river_supply` is held constant every turn and shipment volume never feeds back into it. So
a shipped-units-to-supply ratio is not a depth or conservation argument, and my
`ship% ≤ 35%` criterion was measuring nothing. Credit to the second reviewer for catching it.

Since the route repays at capacity 20 with River untouched (R3), **make no River change.**
`river_market` stays `supply 80 / demand 130`.

## R5 — State the price-taking boundary explicitly instead of pretending to fix it

`sell_grain` converts inventory to cash at the pre-turn Home price, and the quantity sold is
not an input to the resulting supply signal; shipments never affect River price. So
"sell at the peak and let the farm refill" also rests on price-taking. Do not add
market-impact mechanics. Record the boundary in `STATE.md` and `DECISIONS`:

> Player sales and shipments are **price-taking** in the five-turn prototype. Endogenous
> transaction price impact is deferred to Section 14. Section 9 tunes transaction sizes and
> costs only enough that this approximation remains usable.

## R6 — `hold rank ≥3` must be computed over the four intentional policies, not five

`random_legal` is a control, not an archetype. As written the rank counts it, so a lucky
random bot could supply one of the two "strategies that beat doing nothing". Compute the
rank over `production_heavy`, `storage_heavy`, `trade_heavy`, `cash_preserving` only, and
require **at least two of the three active archetypes** to beat hold by a **material 5%**:

```python
active_median * 10_000 >= hold_median * 10_500
```

Use 5%, **not** the ~11% currently observed. Encoding the observed margin as the threshold
is how buying a passing grade starts.

## R7 — Gate math is floating-point (blocking)

```
harness.py:243   win_rate: float
harness.py:267   median_ratio: float
harness.py:381   win_rate = wins.get(pid, 0) / config.n_seeds
harness.py:423   dominant_pass = median_ratio < 1.60
```

Section 9 defines an engine-owned, CI-comparable measurement contract, and the project has
held integer/fixed-point discipline since Section 2. Convert to `win_rate_bps: int` and
`median_ratio_bps: int`, and compare without division:

```python
dominant_pass = top_median * 10_000 < overall_median * 16_000
dead_pass     = policy_median * 10_000 >= overall_median * 7_000
```

Format the displayed ratio deterministically from the integer bps.

## R8 — The price-movement assertion is looser than the rule it claims to enforce

```python
max_delta = before * 2000 // 10000 + 1
assert abs(after - before) <= max_delta + 500      # test_balance_harness.py:89-90
```

At a price near 5000 that is a 50% loosening, and it would accept a movement the test says
it rejects. Make it the exact engine rule from `_bounded_price`:

```python
assert abs(after - before) <= before * state_max_movement_bps // 10_000
```

Read `max_movement_bps` from state rather than hard-coding 2000.

## R9 — Tie handling in `run_batch` is biased

`harness.py:296-317` picks a winner then re-walks `POLICY_IDS` decrementing and
re-incrementing to "fix" ties, awarding them to whichever policy is listed first. Report
`unique_wins` and `tied_best_count` separately and delete the fixup loop. Win-rate is
informational, not a gate.

---

## Final target config

| field | shipped now | target |
|---|---|---|
| `player.storage_capacity` | 130 | **130** (keep) |
| `route.transport_cost_per_unit` | 300 | **300** (keep) |
| `route.capacity` | 60 | **20** (revert — R3) |
| `river_market.supply` / `demand` | 80 / 130 | **unchanged** (R4) |
| `BUILD_GRANARY_COST` / `DELTA` | 300 / 50 | **unchanged** (R2) |

Net change vs. the original Section 9 start state: **two numbers** —
`storage_capacity` 400→130 and `transport_cost_per_unit` 800→300 — plus three policy fixes.

Measured at that config:

| policy | median | vs hold |
|---|---|---|
| storage | 2347 | +11% |
| production | 2290 | +9% |
| trade | 2241 | +6% |
| hold | 2109 | — |

hold rank **4/4** (last among the intentional policies); ratio **1.02**; dead **0.92**;
price **3876–8535**; granary **+56**; route **+174**.

## Work items

1. Fix the third strawman: `policy_storage_heavy` builds capacity when the incoming harvest
   would overflow, and buys only into space the harvest will not claim (R2).
2. Revert `route.capacity` to `20` (R3). Make no River Town change (R4).
3. **Matched-control regression tests**, replacing `test_build_granary_not_worthless`'s
   sufficiency gap and rewriting `test_route_can_repay_establishment_cost` around the **real**
   policies rather than a toy probe:
   - `policy_storage_heavy` must beat itself with `build_granary` suppressed.
   - `policy_trade_heavy` must beat itself with `secure_route` suppressed.
   Keep the existing headroom assertion as a cheap necessary condition alongside them.
4. Report `trade_wealth`, `trade_without_route_wealth`, `route_incremental_value`, and
   `route_incremental_value_bps_of_cost` in the harness output, so this confound cannot
   silently return (R1).
5. Rank over the four intentional policies; ≥2 active archetypes beat hold by ≥5% (R6).
6. Integer bps gate math; drop both floats (R7).
7. Exact price-movement assertion (R8). Fix tie handling (R9).
8. Set `BUILD_SPEC.md` Section 9 Status back to **IN PROGRESS** until all of the above pass,
   then to COMPLETE. It was marked COMPLETE with the granary still a trap and the gate math
   still floating-point.
9. Update `STATE.md` and `DECISIONS.md` 016: record the matched-control technique, that the
   granary trap was a **policy** bug not an economy bug, that route capacity was reverted
   because transport cost was the whole fix, that the River rescale was proposed and
   **retracted** as an invalid depth argument, and the price-taking boundary from R5.
   Do not overstate trade — it is the weakest of the three at +6%.
10. `graphify update .` and commit the regenerated artifacts.

## Do not

- Do not weaken, loosen or delete any assertion to go green (BUILD_SPEC §0.4). Updating an
  expected number because the economy intentionally moved is legitimate; changing a
  threshold is not.
- No new mechanic, verb, or state field. Spoilage is a §15 deferred module owned by
  Section 14; upkeep was measured and rejected in round 2 (D5).
- Do not tune `BUILD_GRANARY_COST`/`DELTA` or River Town. Both were swept and are unnecessary.
