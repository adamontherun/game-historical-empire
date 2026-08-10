# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 9 — COMPLETE (2026-08-10)

**Headless Strategy and Balance Harness — storage scarcity + route viability + policy competence (matched controls):** Retuned `default_start_state` storage `400→130`, transport `800→300`, route capacity kept `20` (reverted from 60 — transport was entire fix, +174 on 400 at 20, +280 at 60 strains price-taking). With three fixed policies (production sells surplus, storage builds on overflow + buys only headroom, trade ships when `river-transport-home>0`) the 40-seed harness clears all gates: `storage 2345` (+11%), `production 2290` (+9%), `trade 2241` (+6%), `cash 2109`, `random 1738` — hold rank **4/4 intentional** (3/3 active beat hold by ≥5% material: 2345*10000≥22144, 2290≥22144, 2241≥22144), median_ratio_bps 10240 (1.024) PASS (<16000), dead PASS (all ≥0.70*overall 2241, worst 2109*10000=21M ≥15.6M), price 3876-8535 PASS, negativity PASS, swing 612 ≤2500. Route incremental `trade 2241 - without 2067 = +174` (4350 bps of 400 cost, 43.5% return; 60 would give +280 but unnecessary). Granary incremental `storage vs no-build +54` median (was -21 trap, flipped with no constant tuning — policy bug masquerading as economy bug). Price-taking boundary: sales/shipments are price-taking; endogenous impact deferred to Section 14. Decomposition: shipped+shipped rank1, shipped+competent rank2, retuned+competent rank4 — both halves needed.

### What exists

```
backend/
  app/
    domain/
      types.py               # MarketState{..., regional_output} + PlayerCommand{..., sell_grain} frozen
      trace.py               # CausalNode/TURN_ORDER includes regional_output
    engine/
      prototype.py           # default_start_state Home 280/410/5000/4000 regional360 River 80/130/5200 storage130 farm5 route 20/300 (price-taking)
      harness.py             # 5 policies: prod surplus-sell, stor overflow-build+headroom-buy, trade ship-margin>0; gates integer bps (<16000, ≥7000), hold rank 4 intentional ≥2×5% beats, route incremental reporting, tied_best_count
      actor.py               # resolve_buy/resolve_sell + YIELD 10 shared
      turn.py                # supply signal+regional_after+farm-demand, price bounded 20% via _bounded_price
      rivals.py              # sell_grain prefs
      cli.py                 # --balance
  tests/
    test_balance_harness.py  # hold rank 4/4 PASS + granary headroom + matched granary/route controls + exact price envelope + integer bps
    test_five_turn_prototype.py # supply 280/116 farm5, drought prep peak ≥130
    test_deterministic_rivals.py # diff ≥1
```

### Boundaries

- Pure engine, no FastAPI. Determinism via rng_for, integers only. HOLD rank 4/4 intentional with 6% weakest (trade 2241 vs 2109) and 11% strongest (storage 2345), ratio 1.024, price 3876-8535.
- Storage 130 < idle 270 so granary load-bearing; route 20/300 repays +174 (43.5%) at price-taking size (ship 20 vs River supply 80); larger 60 would give +280 but strains approximation — kept at 20.
- Price-taking: player sales/shipments do not affect supply signal or River price (deferred to Section 14). Tuned only transaction sizes/costs enough approximation remains usable.
- No new mechanic/verb/state field. Upkeep and spoilage considered and rejected (see DECISIONS 016); River rescale 80/130→200/350 proposed in round 3 and retracted as invalid depth argument (supply is signal/index, not conserved stock).
- Gates integer bps: dominant `top*10000 < second*16000`, dead `med*10000 ≥ overall*7000`, hold `active*10000 ≥ hold*10500` over 4 intentional, tie handling via unique_wins + tied_best_count, no floats.

### Normal verification

```bash
make test              # 133 passed
make lint              # All checks passed!
make type              # 0 errors, 0 warnings
make format-check      # 32 files already formatted
```

### Last known green

```
pytest 133 passed in 2.76s
ruff check All checks passed!
pyright 0 errors, 0 warnings
price 3876-8535 PASS
hold cash 2109 rank 4/4 intentional vs max 2345 (storage_heavy) PASS — 3/3 active beat hold by ≥5%
route trade 2241 vs without 2067 → +174 (4350 bps of 400)
granary median +54
```

### Decisions relevant

- Farm 10→5, storage 400→130, transport 800→300, route 20 kept, policies competent (surplus-sell + overflow-build/headroom-buy + ship-margin>0), hold rank 4/4 intentional ≥2×5% beats.
- DECISIONS 016: matched-control technique, granary policy bug not economy bug (+56 vs -21), route capacity reverted (transport whole fix), River rescale retracted, price-taking boundary, trade weakest at +6%.

### Intentionally missing

Section 10 FastAPI not started.

### Next milestone

Section 10 Minimal FastAPI Boundary (in-memory sessions, three endpoints).
