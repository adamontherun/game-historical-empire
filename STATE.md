# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 9 — COMPLETE (2026-08-10)

**Headless Strategy and Balance Harness — storage scarcity + route viability fix, hold rank ≥3 with 8.6% margin:** Retuned `default_start_state` storage `400→130`, route capacity `20→60`, transport `800→300`. With competent policies (production sells surplus that won't fit each turn, trade ships every turn margin `river-transport-home>0` else buys/sells at home peak) the 40-seed harness clears all gates: `production 2290` `storage 1974` `trade 2347` `cash 2109` `random 1738` — cash rank 3/5 (trade + production beat hold by 11.3% and 8.6%, both >5% margin), median_ratio 1.02 PASS (<1.60), dead PASS (production 2290 ≥0.70*2109), price 3876-8535 PASS ([2000,9000]), negativity PASS, swing 612 ≤2500. Decomposition: shipped params + shipped policies rank1, shipped params + competent policies rank2 (production 3683 beats hold 3133 but trade 2727 still loses), retuned params + competent policies rank3 — both halves needed, neither alone sufficient. Upkeep/consumption prototyped over 20-70 and capacity-scaled variant moves hold 1→2 never 3 and blows dominance ratio to 2.04 (production dominant) / 5.01; spoilage deferred per BUILD_SPEC §15 and Section14 ownership, not implemented. Regression gates added: granary worthless (`storage < start_grain+farm*YIELD*5`) and route repay (ship-when-profitable vs hold, with > without).

### What exists

```
backend/
  app/
    domain/
      types.py               # MarketState{..., regional_output} + PlayerCommand{..., sell_grain} frozen
      trace.py               # CausalNode/TURN_ORDER includes regional_output
    engine/
      prototype.py           # default_start_state Home 280/410/5000/4000 regional360 River 80/130/5200 storage130 farm5 route 60/300
      harness.py             # 5 policies: production sells surplus, storage buys+peak sell, trade ships when margin>0 else buy/sell; gates median_ratio <1.60 dead ≥0.70 hold rank ≥3 price [2000,9000]
      actor.py               # resolve_buy/resolve_sell + YIELD 10 shared
      turn.py                # supply signal+regional_after+farm-demand, price bounded 20%
      rivals.py              # sell_grain prefs
      cli.py                 # --balance
  tests/
    test_balance_harness.py  # hold rank ≥3 PASS + granary-not-worthless + route-repay regressions
    test_five_turn_prototype.py # supply 280/116 farm5, drought prep peak ≥130
    test_deterministic_rivals.py # diff ≥1
```

### Boundaries

- Pure engine, no FastAPI. Determinism via rng_for, integers only. HOLD rank 3/5 with 8.6% margin (production 2290 vs 2109), ratio 1.02, price 3876-8535.
- Storage 130 < idle 270 so granary load-bearing; route 60/300 lets trade repay 400 cost (ship 60 at +~300 margin early, sell home at peak when margin negative).
- No new mechanic/verb/state field. Upkeep and spoilage considered and rejected (see DECISIONS 016).

### Normal verification

```bash
make test              # 132 passed
make lint              # All checks passed!
make type              # 0 errors, 0 warnings
make format-check      # 32 files already formatted
```

### Last known green

```
pytest 132 passed in 1.37s
ruff check All checks passed!
pyright 0 errors, 0 warnings
price 3876-8535 PASS
hold cash 2109 rank 3/5 vs max 2347 (trade_heavy) PASS — cash must rank ≥3 (≥2 policies beat it)
```

### Decisions relevant

- Farm 10→5, storage 400→130, route 20/800→60/300, policies competent (surplus-sell + ship-when-profitable), hold rank ≥3 gate.
- DECISIONS 016: unswept binding params storage_capacity and route.capacity (fortransport cost), decomposition shipped/competent/retuned, upkeep/spoilage rejected.

### Intentionally missing

Section 10 FastAPI not started.

### Next milestone

Section 10 Minimal FastAPI Boundary (in-memory sessions, three endpoints).
