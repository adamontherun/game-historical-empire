# Section 9 — review round 3 (consolidated) — SUPERSEDES round 2 on the route

Round 2's diagnosis stands. **Round 2's route fix does not**, and this document retracts it.
Read this document as the authority; round 2 remains on disk for the reasoning trail.

---

## R1 — Retraction: round 2's route fix was buying a passing grade

Round 2 recommended `route.capacity` 20→60 and `transport_cost_per_unit` 800→300, and
claimed "19 of 32 swept configs pass all four gates". The configs do pass. The
attribution was wrong.

The control that should have been built first: **the identical trade policy that never
secures the route.**

| policy | wealth |
|---|---|
| hold ×5 | 1853 |
| trade policy, **never secures route** | **2137** |
| trade policy + route, capacity 40 | 2164 |
| trade policy + route, capacity 60 | 2217 |

The route contributes **+27 to +80** — around 1–4% — and it earns even that by shipping
**50–75% of River Town's entire supply** into a market that `turn.py` holds at constant
supply (`river_supply_stable`, `turn.py:900`) and which therefore never reprices against
the shipment. That is profit manufactured out of a modelling gap, not an economic fix.

What actually beats holding in those configs is unrelated to trade: with storage scarce,
selling the full store into the turn-4 price peak and letting the free farm output refill
it is worth ~284. The route was riding on that and taking the credit.

This is orchestration failure pattern #1 in my own recommendation — an arm that differed
in more than the variable under study. The no-route control is what rules it out, and any
future claim about the route must be reported against that control.

## R2 — Transport cost, not capacity, is what makes the route a trap

With the no-route control in place and swept properly:

| transport | route cap | river supply | route contribution vs no-route |
|---|---|---|---|
| 800 | 40 | 200 | **−248** |
| 800 | 60 | 200 | **−263** |
| 500 | 40 | 200 | **−224** |
| 500 | 60 | 200 | **−233** |
| 300 | 40 | 200 | **+66** |
| 300 | 60 | 200 | **+129** |

At transport 500 and 800, securing the route **destroys 224–300 wealth** regardless of
capacity or river size. Round 2 named capacity as the binding constraint; that was
measured without the control and is wrong. The transport toll is the trap: 800/unit
against a cross-market price gap of ~900 leaves nothing, and the 400 establishment cost is
then unrecoverable under every line of play.

## R3 — River Town is not a market at its shipped scale

River Town: `supply 80, demand 130`. Home Valley: `supply 280, demand 410` plus
`regional_output 360`. A single player farm produces 50–150/turn. A "town" that can absorb
20 units of grain per turn is not a trading partner; it is a stall. That mis-scaling is
what forces the choice between "route moves trivial volume" and "route floods an
unresponsive market".

Scaling River Town to `supply 200, demand 350` keeps it a net importer (demand/supply 1.75,
scarcer than Home's 1.46 — coherent for a consumption town next to a farming valley) and
drops shipments from 75% of its supply to 20%, so the exogenous-price approximation is no
longer load-bearing.

**This does not make trade a strong archetype.** At the recommended config the route
contributes +66 on ~2200 wealth (3%). Trade beats holding mainly through the same
buy/sell timing available without a route. Say so plainly in DECISIONS rather than
implying the route carries the strategy.

---

## What to change

Start-state tuning only. **No new mechanic, no new verb, no new state field.** Spoilage is
a §15 deferred module owned by Section 14; upkeep was measured and rejected (round 2, D5).

| field | from | to |
|---|---|---|
| `player.storage_capacity` | 400 | **100** |
| `route.transport_cost_per_unit` | 800 | **300** |
| `route.capacity` | 20 | **40** |
| `river_market.supply` | 80 | **200** |
| `river_market.demand` | 130 | **350** |

Measured at that config with competent policies:

| policy | median wealth | vs hold |
|---|---|---|
| trade | 2203 | +19% |
| storage | 2071 | +12% |
| hold | 1853 | — |
| production | 1644 | −11% |

hold rank **3/4**; dominance ratio **1.06** (gate <1.60); dead fraction **0.79**
(gate ≥0.70); price **3876–8535** (gate [2000, 9000]); every strategy that beats hold does
so by **≥12%** (not knife-edge); route contribution **+66** (positive); peak shipment
**20%** of River Town supply.

Treat the numbers as a starting point and re-derive against the real five-policy harness.
Do not ship a config where the margin over holding is under 5%, and **do not ship one where
the route contribution is negative** — that would leave `secure_route` a trap.

## R4 — Gate math is floating-point, which breaks eight sections of integer discipline

Independently raised by the second reviewer and confirmed in the shipped code:

```
harness.py:243   win_rate: float
harness.py:267   median_ratio: float
harness.py:381   win_rate = wins.get(pid, 0) / config.n_seeds
harness.py:423   dominant_pass = median_ratio < 1.60
```

The **gate comparison itself** is a float comparison. BUILD_SPEC §12 requires integer
canonical state and the project has held that line since Section 2. Convert ratios to
basis points and compare by cross-multiplication:

```python
dominant_pass = max_median * 10_000 < overall_median * 16_000
```

Keep `win_rate` reported but as `win_rate_bps`, and define deterministic rounding for mean
and even-count median rather than relying on float division.

## R5 — Tie handling in `run_batch` is biased and convoluted

`harness.py:296-317` picks a winner, then re-walks `POLICY_IDS` to "fix" the count by
decrementing and re-incrementing. Ties are awarded to whichever policy appears first in
`POLICY_IDS`, which manufactures wins for `production_heavy` by ordering alone. Since
win-rate is informational rather than a gate, report `unique_wins` and `tied_best_count`
separately and delete the decrement/re-increment dance.

---

## Work items

1. Fix the two strawman policies (round 2, unchanged): `policy_trade_heavy` must ship every
   turn while `river − transport − home > 0` and stop when it is not;
   `policy_production_heavy` must sell the surplus that will not fit in storage each turn.
2. Retune `default_start_state` per the table above, re-derived against the real harness.
3. Get `make test` green with the `hold rank ≥3` gate **intact**. Do not weaken, loosen or
   delete any assertion (BUILD_SPEC §0.4). Updating an expected number because the economy
   intentionally moved is legitimate; changing a threshold is not.
4. Convert gate math to integer basis points (R4).
5. Fix tie handling (R5).
6. **Regression test — granary must not be worthless:** assert starting `storage_capacity`
   is below what an idle player accumulates over five turns
   (`start_grain + farm_capacity × YIELD_PER_CAPACITY × 5`).
7. **Regression test — the route must earn its keep:** a ship-while-profitable policy must
   finish **ahead of the identical policy that never secures the route**. This is the
   control from R1 and it is the single most important new test in this round; it is what
   makes "trade is a real strategy" falsifiable.
8. **Regression test — the exogenous-river approximation stays valid:** assert peak
   shipment volume stays under ~35% of `river_market.supply`. `turn.py` will not reprice
   River Town against a shipment, so this test pins the range in which that simplification
   is honest, and fails loudly if future tuning starts leaning on it.
9. Update `STATE.md`; add DECISIONS 016 recording: the two parameters 015 never swept; the
   policy-competence vs economy decomposition (shipped+shipped = rank 1, shipped+competent
   = rank 2, retuned+competent = rank 3); that upkeep and spoilage were considered and
   rejected with reasons; **and that the route contributes only ~3%, with River Town price
   impact deferred to Section 14.** Do not overstate trade.
10. `graphify update .` and commit the regenerated artifacts.

## Keep as-is

- The `hold rank ≥3` gate. With deterministic policies on a fixed arc, win-rate is 0/1 by
  construction, so BUILD_SPEC AC2 is trivially satisfiable and means nothing; "doing
  nothing must not be the best play" is the honest operationalization.
- median-ratio and dead-fraction gates, the price band, paired seeds, `insufficient_*`
  affordability assertions, `PRESSURE_*` constants over bare strings, determinism by
  double-run equality.
- The ship margin going negative at the drought peak (home pays more than the river during
  a famine). Ship early, sell home late is a real lesson and should survive tuning.
- Production ending below hold in its pure form. Flooding the market you sell into is the
  correct consequence; the dead gate at 0.70 is where that line is held.
