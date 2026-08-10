# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 9 — IN PROGRESS (2026-08-10)

**Headless Strategy and Balance Harness — farm lowered to 5, policies made competent, hold still rank 1 (binding constraint):** Lowered starting `farm_capacity` from 10→5 (free baseline 100→50 grain/turn, 500→250 over 5 turns, storage 400 no longer saturated by doing nothing, so expanding finally produces storable sellable grain). Retuned `default_start_state` to `supply 280/demand 410/regional 360/responsiveness 4000/storage 400` (demand 410 to keep surplus ~0 with farm 50, price 3876-8535). Made harness policies competent: `production_heavy` expands farm early when affordable then sells only at peak (turn 4, up to 150), `storage_heavy` builds granary then buys scaled to cash+headroom (up to 80) pre-drought and sells only at peak (turn 4, up to 150), `trade_heavy` secures route then buys scaled and ships/sells only at peak. All buys scaled to `min(space, max_affordable, 80)` not hardcoded 10/20, sells scaled to inventory and timed to post-drought price peak. Replaced `hold_not_top` (cash not max) with `hold rank ≥3` gate: cash_preserving must rank no higher than 3rd of 5 (≥2 policies beat it) — doing nothing should be mediocre, not second-best. Current 200-seed harness with new policies: `production 2977` `storage 2927` `trade 2990` `cash 3133` `random 2408` — cash rank 1/5, hold_not_top FAIL (0 policies beat it, need 2), median_ratio 1.05 PASS, dead PASS, price 3876-8535 PASS, negativity PASS. Sweep over farm 2-10, supply 280-600, demand 340-420, regional 280-400, resp 3000-6000 shows no config achieves hold rank ≥3 with price staying in [2000,9000] under current mechanics — lower farm makes production win but storage/trade still lose by ~100-200, higher resp makes trade barely beat but pushes price >9000, higher supply lowers early price but also reduces hold wealth and still storage loses. Binding constraint is free farm output still yields ~250 grain valued at high final price, while arbitrage profit is capped by 20% per-turn movement and granary cost 300, so buying low (5000) selling high (8500) nets ~300-400 per 80 grain, insufficient to overcome hold's free grain plus cash preservation. Missing mechanic likely needed: farm maintenance cost or diminishing returns, or storage/route providing value beyond simple arbitrage (e.g., spoilage avoidance, price impact of farm output), or trade river arbitrage margin.

### What exists

```
backend/
  app/
    domain/
      types.py               # MarketState{..., regional_output} + PlayerCommand{..., sell_grain} frozen
      trace.py               # CausalNode/TURN_ORDER includes regional_output
    engine/
      prototype.py           # default_start_state Home 280/410/5000/4000 regional360 River 80/130/5200 storage400 farm5
      harness.py             # 5 policies competent scaled buys + peak sells, gates: median_ratio <1.60, dead ≥0.70, hold rank ≥3 (≥2 beat), price [2000,9000]
      actor.py               # resolve_buy/resolve_sell shared
      turn.py                # supply signal+regional_after+farm-demand, price bounded 20%
      rivals.py              # sell_grain prefs
      cli.py                 # --balance
  tests/
    test_balance_harness.py  # hold rank ≥3 gate (currently FAIL)
    test_five_turn_prototype.py # supply 280/116 farm5
    test_deterministic_rivals.py # diff ≥1
```

### Boundaries

- Pure engine, no FastAPI. Determinism via rng_for, integers only. HOLD still rank 1 (binding).

### Normal verification

```bash
make test              # 1 failed (hold_not_top), 129 passed
make lint              # All checks passed (1 file reformatted)
make type              # 0 errors
```

### Last known green

```
pytest 129 passed, 1 failed (hold rank 1/5 need ≥3)
ruff check All checks passed
pyright 0 errors
price 3876-8535 PASS
```

### Decisions relevant

- Farm 10→5, demand 400→410, policies scaled buys + peak sells, hold rank ≥3 gate.

### Intentionally missing

Section 10 FastAPI not started.

### Next milestone

Tune or add mechanic to make hold rank ≥3 without breaking price band — or report missing mechanic.
