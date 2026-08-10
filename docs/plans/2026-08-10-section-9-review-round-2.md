# Section 9 — implementation review, round 2 (consolidated)

Status at review: harness lands correctly, 129 tests pass, **1 fails** —
`hold rank ≥3` (`cash_preserving` ranks 1/5). STATE.md and DECISIONS 015 describe
this accurately; the handoff is honest and reproduces exactly.

DECISIONS 015 concluded that **no start-state configuration can clear the gate under
current mechanics**, and that a new mechanic (farm maintenance, spoilage, or trade margin)
is required. **That conclusion is wrong**, and this document shows why with measurements
from the real engine.

Headline: the gate is clearable with **no new mechanic and no new verb** — only start-state
tuning. 19 of 32 swept configurations pass all four gates. Details and the exact
decomposition of the fix follow.

---

## Why 015's sweep concluded "impossible"

015 swept `farm`, `supply`, `demand`, `regional`, `responsiveness`, cap and costs. It did
**not** sweep the two parameters that actually bind: `player.storage_capacity` and
`route.capacity`. Both were held at their shipped values (400 and 20) throughout. Those
two are the constraint.

There is also a second, independent cause: two of the five policies are still strawmen
even after 015 made them "competent". That matters because a balance table built from
weak policies is evidence about the policies, not about the economy.

---

## D1 — `storage_heavy`'s core investment buys capacity nobody needs (BLOCKING)

Starting `storage_capacity` is **400**. Starting inventory is **20**. An idle player
accumulates `20 + 5 × 10 × 5 = 270` over the whole game — never reaching the cap.

So `build_granary` (−300 cash, +50 capacity) purchases headroom that is never used. Its
marginal value is **exactly zero** for every policy except `production_heavy`. The storage
strategy's defining move is a pure cash burn, and the ~300 of arbitrage profit it earns
elsewhere is precisely cancelled by the granary it did not need. That is why storage lands
at 2927 vs hold's 3133.

This is also a modelling lie worth naming: a starting smallholder does not own a 400-unit
granary that is 5% full. Storage scarcity is *why* granaries were monumental
infrastructure. Making capacity abundant at turn 0 deletes the entire economic meaning of
the storage strategy.

**Measured** — start storage vs. medians (shipped policies, 4 seeds):

| start storage | production | storage | trade | hold | hold rank |
|---|---|---|---|---|---|
| 400 (shipped) | 2977 | 2927 | 2990 | **3133** | 1 |
| 200 | 1950 | 2347 | 1782 | **2707** | 1 |
| 120 | 1407 | 1889 | 1277 | **2024** | 1 |
| 80 | 1136 | 1695 | 1173 | **1682** | 2 |

## D2 — The river route cannot repay its own establishment cost (BLOCKING)

`route.capacity` is **20 units/turn** against a farm producing 50–150/turn, and
`transport_cost_per_unit` is **800** against a price gap between the two markets of
roughly 600–900. Per-unit ship margin, measured across the arc:

```
river − transport − home  =   −488   +97   +97  −1088  −2510
```

Two turns of `+97` per unit, on at most 20 units, is ~4 cash of profit against a **400**
establishment cost. The route can never repay itself. `secure_route` is not a weak
strategy — it is a **trap**, which is worse than a dead one: BUILD_SPEC's target is "no
obviously dead strategy", and a move that is strictly negative under every line of play
fails that more severely than mediocrity does.

Note the margin series is otherwise excellent design and should be preserved: shipping is
profitable in normal turns and *loss-making at the drought peak*, because your own home
market pays more than the river during a famine. "Ship early, sell home late" is a real
comparative-advantage lesson and is exactly the kind of thing §1 wants the player to learn.
The problem is only that the volume and the toll make the whole route unusable.

**Measured** — capacity is the binding constraint, not transport cost (storage 120,
competent trade policy):

| transport | route cap | trade wealth |
|---|---|---|
| 500 | 20 | 1957 |
| 300 | 20 | 1973 |
| 100 | 20 | 1989 |
| 500 | **40** | **2294** |
| 500 | 60 | 2289 |

Cutting transport 500→100 moves trade by 32. Raising capacity 20→40 moves it by **337**.
Above 40 nothing changes, because inventory rather than route capacity becomes binding —
which is the correct place for the constraint to sit.

## D3 — Two policies are still strawmen, so the balance table is not yet evidence

- `policy_trade_heavy` ships **only on turn 4** (`harness.py:115`). On a 20/turn route that
  is 20 units across the entire game. A competent trader ships every turn the margin is
  positive and stops when it goes negative.
- `policy_production_heavy` hoards into a cap it overflows, then dumps 150 into its own
  crashed market at turn 4. A competent producer sells the surplus that will not fit,
  each turn.

This is orchestration failure pattern #1 (comparing arms that differ in more than the
variable under study). It must be fixed **before** any tuning conclusion is drawn, or the
tuning is fitted to policy weakness.

**The fix decomposes cleanly, and both halves are needed** — measured at shipped
parameters (storage 400 / transport 800 / cap 20) with competent policies:

| | hold rank |
|---|---|
| shipped params + shipped policies | 1 |
| shipped params + **competent** policies | 2 |
| **retuned** params + competent policies | **3** |

Report both halves in DECISIONS. Neither alone is sufficient.

---

## What to change

Start-state tuning only. **No new mechanic, no new verb, no new state field.** BUILD_SPEC
§15 lists spoilage as a long-term module with "Do not implement these until a numbered
section requires them", and Section 14 owns `storage and spoilage` — so spoilage is out of
scope here. Farm maintenance / upkeep was measured too and is *not* needed (see D5).

In `default_start_state`:

| field | from | to | why |
|---|---|---|---|
| `player.storage_capacity` | 400 | **100** | makes granaries load-bearing (D1) |
| `route.capacity` | 20 | **60** | lets the route carry a real cargo (D2) |
| `route.transport_cost_per_unit` | 800 | **300** | leaves a real margin after the toll (D2) |

**Treat these as a starting point, not as authority.** Re-derive them against the *real*
five-policy harness (mine used four policies and simplified them); land wherever the gates
actually pass with the widest margin. The passing region is broad — 19 of 32 swept configs
clear all four gates — so there is room to choose round, defensible numbers rather than
knife-edge ones. **Do not ship a config that passes by <5%**; 015 was burned by exactly
that (hold_not_top passing by 1.6%, flipping when storage moved 400→500).

Measured at storage 100 / transport 300 / cap 60, competent policies:

| policy | median wealth | vs hold |
|---|---|---|
| trade | 2217 | +20% |
| storage | 2071 | +12% |
| hold | 1853 | — |
| production | 1644 | −11% |

hold rank **3/4**, dominance ratio **1.07** (gate <1.60), dead fraction **0.79**
(gate ≥0.70), price **3876–8535** (gate [2000, 9000]).

## D4 — Production ending below hold is acceptable; do not tune it away

Pure production floods its own market: expanding to 15 capacity produces 150/turn into a
home market whose price then falls to 4423 while everyone else sells into 8535. Losing to
idling *in its pure form* is the correct lesson — production without an outlet destroys
the price you sell into — and it is exactly what makes the route valuable. The dead-strategy
gate (0.79 ≥ 0.70) is the right place to hold the line. Do not add a production buff to
make the table prettier; the strategies are meant to be complementary, not equal
(BUILD_SPEC: "Do not optimize for equal strategy outcomes").

## D5 — Upkeep / farm maintenance was measured and rejected

A settlement-consumption mechanic (population eats N grain/turn, shortfall bought at market)
was prototyped and swept over `upkeep ∈ [20, 70]` and a capacity-scaled variant. It moves
hold from rank 1 to rank 2 but **never to rank 3**, and it pushes the dominance ratio well
past the gate (2.04 at upkeep 40, 5.01 at upkeep 60) by making `production_heavy`
dominant instead. It trades one dominant strategy for another while adding a mechanic.
Rejected — recorded here so it is not re-proposed.

---

## Work items

1. Make `policy_trade_heavy` ship every turn while `river − transport − home > 0`, and stop
   when it is not. Make `policy_production_heavy` sell the surplus that will not fit in
   storage each turn rather than hoarding into an overflow.
2. Retune `default_start_state`: `storage_capacity`, `route.capacity`,
   `route.transport_cost_per_unit` as above, re-derived against the real harness.
3. Get `make test` green with the `hold rank ≥3` gate **intact**. Do not weaken, loosen, or
   delete the gate or any other assertion (BUILD_SPEC §0.4). Updating an expected number
   because the economy intentionally moved is legitimate; changing a threshold is not.
4. Add a regression test that fails if `build_granary` is worthless — i.e. assert starting
   `storage_capacity` is below what an idle player accumulates over five turns
   (`start_grain + farm_capacity × YIELD_PER_CAPACITY × 5`). This is the invariant that
   silently broke; it should not be able to break again unnoticed.
5. Add a regression test that the route can repay its establishment cost: a
   ship-every-profitable-turn policy must end ahead of the same policy that never secures
   the route. This is the invariant D2 violated.
6. Update `STATE.md` and add a DECISIONS entry (016) recording: the two binding parameters
   015 did not sweep, the policy-competence vs. economy decomposition, and that upkeep and
   spoilage were considered and rejected (with reasons).
7. `graphify update .` and commit the regenerated artifacts.

## Keep as-is

- The `hold rank ≥3` gate itself. It is stricter than BUILD_SPEC AC2 and it is right:
  with deterministic policies on a fixed arc, win-rate is 0/1 by construction, so AC2 is
  trivially satisfiable and means nothing. "Doing nothing must not be the best play" is the
  honest operationalization of "no universally dominant strategy" for this game.
- median-ratio and dead-fraction gates, the price band, the paired-seed design, the
  `insufficient_*` affordability assertions, `PRESSURE_*` constants over bare strings,
  determinism by double-run equality.
- The ship-margin arc going negative at the drought peak. That is a feature.
