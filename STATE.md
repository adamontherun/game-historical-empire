# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 13 — IN PROGRESS — City & Craft Transition Epilogue (2026-08-10) — REVERTED TO PLAUSIBLE (moderate)

**Epilogue hook (engine+domain is real work):** 3-turn epilogue after 5-turn agriculture shifts bottleneck from storage+drought timing to skilled_labour. Adds `PlayerState.skilled_labour`, `InventoryState.finished_goods`, `GameState.legacies`, new commands `craft_goods`/`sell_finished_goods`/`hire_labour`, **moderate legible** demand shift 410→280→220→180 (removed punitive 80/30/10 + 25%→800 collapse), workshop conversion grain→finished capped at labour×10 (GRAIN_PER_LABOUR=10, 10→3 uniform, granary inert), finished price **9500 +800 river** (reverted from 22000, no collapse BPS), Land Network +15 grain/turn weak vs labour cap, **three legacies** (granary inert, river +2 labour, land weak) — crisis dropped (was 40/40 constant). Structural fixes KEEP: river_contracts grants +2 skilled_labour, granary_expertise inert for crafting, crisis_reputation dropped, land_network +15 deliberately weak. hire_labour +1/turn consuming turn.

**Honest status (2026-08-10 correction):** The structural regime-shift mechanism is implemented and **unit-proven** via deterministic scenario test (equal wealth, labour-rich wins). The full statistical demonstration across harness policies is **deferred until human playtest confirms the loop is worth tuning**. Do not claim AC1 is met by the harness. `run_four_arm` remains in the codebase as an instrument for post-playtest tuning, not a gate.

**Scenario test (deterministic, not statistical) — PASS:**
```
Equal wealth start: 2250 (grain-rich/labour-poor: 150 grain, 1 labour, 1500 cash vs grain-poorer/labour-rich: 70 grain, 3 labour, 1900 cash; price 5000)
After 3 epilogue turns (craft max each turn):
  grain-rich/labour-poor (land_network, 1 labour):  turn6 10 grain +3 finished @6000 wealth 1588 → turn8 10 grain +9 finished @8640 wealth 1671
  grain-poorer/labour-rich (river_contracts, 3 labour): turn6 10 grain +9 finished @6000 wealth 2052 → turn8 10 grain +15 finished @8640 wealth 2140
  → labour-rich 2140 > grain-rich 1671 — PASS (mechanism: labour×10 cap, 30 vs 10 grain/turn)
```

**Four-arm harness (n=200, prefix sec13, MODERATE demand 280/220/180, price 9500+800) — instrument only, AC1 credible FAIL:**
```
Arm A (5 turns agri): cash_preserving=2109, production_heavy=2290, storage_heavy=2345, trade_heavy=2241
Arm B (8 full): cash_preserving=1653, production_heavy=2271, storage_heavy=2497, trade_heavy=2405
Control C (demand OFF): cash_preserving=2393, production_heavy=2322, storage_heavy=3807, trade_heavy=3145
Control L (legacies OFF): cash_preserving=1653, production_heavy=2271, storage_heavy=2497, trade_heavy=2212
P_agri=storage_heavy rank A1 B1 C1 L1 lead_A 55 lead_B 92 lead_C 662 contraction_B -68% contraction_C -1104%
AC1 B pass (rank≥2 or C≥40): False  Control C pass: False  AC1 credible (B and not C): False — FAIL
Net-positive guard (some B>A): True best_gain=164 (trade 2241→2405) — PASS
Ratios bps: A=10240 B=10382
Per-policy wealth deltas (moderate, legible — no wealth tax):
  storage_heavy 2345 → 2497 +152 +6%
  production_heavy 2290 → 2271 -19 -1%
  trade_heavy 2241 → 2405 +164 +7%
  cash_preserving 2109 → 1653 -456 -21%  (>10% only for cash; intentional policies within ±7%)
Legacies per policy (deterministic 3): production (land), storage (granary inert), trade (river +2 labour), cash ()
Trace: urban_demand at demanded/2 signalling city shift, plus craft/labour; no raw_price_collapse node (removed)
```
No policy loses more than ~10% among intentional (storage +6%, trade +7%, production -1%); labour-rich path visibly gains. Previous punitive tuning (80/30/10 + 25%→800, 22000) produced storage 2345→1789 -24% and cash -38% — a wealth tax, not a hook — reverted per correction. EightTurnGame 5+3, API still FiveTurnGame (5) for e2e stability.

### What exists

```
backend/
  app/
    main.py                    # create_app() -> FastAPI, mounts /api/v1 router
    api/
      __init__.py
      sessions.py              # GameSession{game_id, run_seed, revision, game: FiveTurnGame|EightTurnGame, lock, commands}, SESSION_STORE
      schemas.py               # CreateGameRequest/ChoiceRequest, ChoiceView, PlayerSummary, EmpireSummary{3 fields}, MarketView, RouteStatus{next_margin}, RivalHeadlines, OutcomeView, CompletionSummaryView, GameView{+skilled_labour,finished_goods,finished_goods_price,legacies,is_epilogue,epilogue_turn}
      mappers.py               # choices_for legality/affordability +2 qty: buy/sell/ship + craft/hire/sell_finished when turn>=5, to_game_view with legacies/skilled/finished
      service.py               # create_game/get_game(with lock, no yield)/choose(with lock+sleep per DECISIONS 021) 404/409/422 — still FiveTurnGame for API (8 via engine directly)
      router.py                # POST /api/v1/games, GET /api/v1/games/{id}, POST /.../choices/{choice_id}
    domain/
      types.py                 # PlayerState{+skilled_labour}, InventoryState{+finished_goods}, GameState{+legacies}, MarketState, RouteState, PlayerCommand{+craft_goods,sell_finished_goods,hire_labour}
      trace.py                 # CausalNode + kinds craft/finished_inventory/finished_price/labour/urban_demand
      pressure.py              # PressureState 7 fields
    engine/
      prototype.py             # FiveTurnGame TURN_LIMIT=5 + EightTurnGame EIGHT_TURN_LIMIT=8, EPILOGUE_TURNS=3, derive_legacies, default_start_state 280/410/360/4000/130
      actor.py                 # ship_margin + resolve_craft/resolve_sell_finished/resolve_hire_labour, GRAIN_PER_LABOUR 10, FINISHED 3/10 @9500+800, HIRE 400/200, LAND +15, EPILOGUE_RAW_DEMAND 280/220/180
      harness.py               # BatchConfig validation (5-turn)
      epilogue_harness.py      # FourArmResult run_four_arm (A/B/C/L) + net-positive guard
      turn.py                  # resolve_turn with craft/hire/sell_finished, demand shift 410→..., wealth with finished, TURN_ORDER unchanged
      rivals.py                # harvest via compute_farm_output
      rng.py
      rounding.py
      cli.py
    tests/
      test_api.py                # 15 tests incl. sell uncapped 024, buy uncapped 022, concurrent lock
      test_engine_purity.py
      test_balance_harness.py
      test_five_turn_prototype.py
      test_deterministic_rivals.py
      test_invariants.py
      test_two_markets_route.py
      test_causal_trace.py
      test_turn_kernel.py
  pyrightconfig.json
frontend/
  index.html
  vite.config.ts               # proxy /api → 8000, VITE_API_URL fallback
  tsconfig.json / tsconfig.node.json
  package.json                 # vite 6.4, react 18.3, tanstack query 5, vitest 3, playwright 1.49, eslint 9 flat
  eslint.config.js             # no-restricted-syntax bans /1000 and /10000 outside format.ts, waitForTimeout
  vitest.config.ts             # jsdom
  playwright.config.ts         # two projects mobile 390×844 + desktop 1280×800, webServer backend+frontend
  src/
    main.tsx
    App.tsx                    # phase machine start→decision→reveal→completion + LegacyStrip when legacies present, empireWithLabour
    api/
      client.ts                # createGame/getGame/commitChoice (expected_revision)
      types.ts                 # GameView + LegacyView, skilled_labour etc optional
      queries.ts
    lib/
      format.ts                # money/pricePerUnit/percent — ONLY /1000 & /10000 site (K2)
      tableau.ts               # 3 rows + workshop row when skilled_labour present (R1+epilogue)
      runRecord.ts             # Section 12: formatRunRecord(seed, rules, choiceIds)
    components/
      StartScreen.tsx          # R8 Begin + R9 Age of Grain · Chapter I
      HeaderBar.tsx            # turn pips Turn n of 5 (epilogue handling via game.turn)
      WorldBand.tsx            # signal serif 22px, data-pressure-stage
      EmpireTableau.tsx        # R1 no arrows, data-testid tier-*
      MarketCard.tsx           # R2: price / grain + Availability + Demand
      MarketPulse.tsx          # side-by-side Home/River + RouteLine
      RouteLine.tsx            # R4: Current route spread … / grain (quote)
      RivalsStrip.tsx          # B5: rival_headlines resolved context
      DecisionBlock.tsx        # B1: group by kind, qty verbatim, exact id submit
      OutcomeReveal.tsx        # B2/B5/B7/R6/R7: 7 beats
      CompletionSummary.tsx    # R10: hero wealth, total change, estate, run record
      FooterDebug.tsx          # R12: seed · rules
      LegacyStrip.tsx          # NEW Section 13: pill strip for legacies
    styles/
      tokens.css
      app.css                  # 480px centred, cards, reveal, commit bar static 8px
    __tests__/
      format.test.ts
      tableau.test.ts
      decisionBlock.test.tsx
      commit.test.tsx
      outcomeReveal.test.tsx
      runRecord.test.tsx       # Section 12: 4 tests
  e2e/
    critical.spec.ts           # 5-turn flow still (API still 5); epilogue via engine harness only
    screenshots/ 4 files
  dist/
Makefile                       # test/lint/type/format-check + front-typecheck/front-lint/front-test/front-e2e + check-all
docs/plans/2026-08-10-section-13-city-craft-epilogue.md  # plan revised for four-arm, net-positive, hire 1/turn, crisis exposure
docs/plans/2026-08-10-section-13-review-round-1.md
```

### Boundaries

- In-memory sessions only; no Postgres/SQLAlchemy/Alembic/auth/LLM/history endpoint/cloud deploy.
- `GameView` is presentation — frontend never recomputes cost/margin/wealth/quantity; `ChoiceView` verbatim, `ship_margin` reliability-aware, `format.ts` only /1000 & /10000 site.
- Per-session `asyncio.Lock` with `sleep(0)` in `choose` per DECISIONS 021; `revision` distinct from `turn`.
- `available_choices` legality+affordability only, `buy`/`sell`/`ship` uncapped, `ship` no margin gate, `craft` capped by labour×10, `hire_labour` +1/turn consuming turn, `sell_finished` capped by finished inventory. Two quantities per verb.
- Frontend phase machine `start → decision → reveal → completion` — fifth commit has both latest_outcome and completion_summary for 5-turn API; 8-turn engine has epilogue via harness only.
- Drivers top-3, price is Home price, `price_value_effect` includes finished revaluation (stable price), wealth = cash + grain*home_price + finished*finished_price.
- Pure engine boundary: `engine`+`domain` no `fastapi`/`alembic`/`app.api`; `tableau()` pure with 3 rows + workshop row when skilled_labour present.
- `DECISIONS 026`: Land Network +15 vs labour×10 means low-labour cannot convert extra grain; keep weakest, do not buff. Structural fixes: river_contracts +2 labour, granary_expertise inert, crisis dropped, land weak.
- EPILOGUE_RAW_DEMAND 280/220/180 (moderate, no collapse BPS), GRAIN_PER_LABOUR 10, FINISHED 3/10 @9500+800, HIRE 400/200, LAND +15. No EPILOGUE_RAW_PRICE_COLLAPSE_BPS.

### Normal verification

```bash
make test              # 151 passed, 1 warning in 2.79s (added test_epilogue_scenario)
make lint              # All checks passed!
make type              # 0 errors, 0 warnings, 0 informations — 41 files analyzed
make format-check      # 41 files already formatted
make front-typecheck   # tsc --noEmit — 0 errors
make front-lint        # eslint . --ext .ts,.tsx — 0 problems
make front-test        # vitest run — 6 passed (6), 29 passed (29)
make check-all         # backend + frontend gates green
# scenario test (deterministic gate, not harness)
uv run --project backend pytest -q backend/tests/test_epilogue_scenario.py -v
# → 1 passed: equal wealth labour-rich 2140 > grain-rich 1671 after 3 turns
# four-arm harness (instrument only, NOT a gate — reported honestly)
# BatchConfig(n_seeds=200, prefix=sec13): AC1 credible FAIL (storage rank1, contraction -68%), net-positive PASS (+164 trade)
```

### Last known green

```
pytest 151 passed in 2.79s (1 warning: StarletteDeprecationWarning)
ruff check All checks passed!
pyright 0 errors, 0 warnings, 0 informations — 41 files analyzed
ruff format --check 41 files already formatted
tsc --noEmit — 0 errors (frontend)
eslint — 0 problems (no-restricted-syntax for /1000 and /10000 outside format.ts, no waitForTimeout)
vitest — 6 passed (6), 29 passed (29)
check-all: backend + frontend gates green
scenario test: 1 passed (labour-rich 2140 > grain-rich 1671, equal start 2250)
four-arm harness n=200 (instrument, not gate): AC1 credible FAIL (storage rank1, 55→92), net-positive PASS (trade +164)
  per-policy deltas: storage +6% (2345→2497), production -1% (2290→2271), trade +7% (2241→2405), cash -21% (2109→1653)
```

### Decisions relevant

- DECISIONS 017: no-strategy-gatekeeping, two quantities, per-session lock, trace/latest-only, OperationState dormant, ship_margin single helper.
- DECISIONS 018 revised (R1): pyright strict app + standard tests.
- DECISIONS 021 (R3): per-session lock `sleep(0)` load-bearing.
- DECISIONS 022 (R2): buy cap removal 55/110.
- DECISIONS 023: Section 11 decision surface — verb cards + quantity verbatim + exact id + Commit + phase-selected pressure.
- DECISIONS 024: sell cap removal — `sell` now uncapped at inventory.
- DECISIONS 026: Land Network deliberately weak +15 vs labour×10, Crisis exposure+survival, hire 1/turn consumes turn, demand shift primary, four-arm+net-positive guards.

### Intentionally missing

History endpoint, SQLAlchemy/Alembic/Postgres, auth, LLM, `render.yaml` cloud deploy. Section 12 human playtest remains BLOCKED — awaiting real observations. Section 13 AC1 full statistical harness remains **deferred** — structural mechanism is unit-proven (scenario test), but four-arm credible demonstration failed (storage rank1) and is not claimed. Do not reword AC1; await human playtest before further tuning.

### Next milestone

Ship plausible moderate epilogue (280/220/180, 9500+800) with structural fixes kept, get it in front of people, tune with real feedback. Section 14 remains gated on human playtest; do not tune harness rank ordering further until playtest confirms loop is worth tuning. Keep API at 5-turn for e2e stability; epilogue via engine (EightTurnGame) + deterministic scenario test.
