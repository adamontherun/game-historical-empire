# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 13 — IN PROGRESS — City & Craft Transition Epilogue (2026-08-10)

**Epilogue hook (engine+domain is real work):** 3-turn epilogue after 5-turn agriculture shifts bottleneck from storage+drought timing to skilled_labour. Adds `PlayerState.skilled_labour`, `InventoryState.finished_goods`, `GameState.legacies`, new commands `craft_goods`/`sell_finished_goods`/`hire_labour`, demand shift 410→280→220→180, workshop conversion grain→finished capped at labour×10 (GRAIN_PER_LABOUR=10, 10→3 uniform, granary inert), finished price 9500 (+800 river, but now inert for granary), Land Network +15 grain/turn weak vs labour cap, **three legacies** (granary inert, river +2 labour, land weak) — crisis dropped (was 40/40 constant; inventory_at_drought fixed per policy 130/180/110/130), hire_labour +1/turn consuming turn, Control C (demand OFF) and Control L (legacies OFF) for four-arm AC1.

**Four-arm harness (n=200, prefix final-required, required changes applied):**
```
Arm A (5 turns agri): storage_heavy 2345, production_heavy 2290, trade_heavy 2241, cash_preserving 2109, random 1195
Arm B (8 full, river +2 labour, granary inert, 3 legacies): storage_heavy 2497, production_heavy 2271, trade_heavy 2405, cash 1653, random 962
Control C (demand OFF): storage 3807, trade 3145, production 2322, cash 2393, random 1100
Control L (legacies OFF): storage 2497, trade 2212, production 2271, cash 1653, random 952
P_agri=storage_heavy rank A1 B1 C1 L1 lead_A 55 lead_B 92 lead_C 662 contraction_B -68% contraction_C -1104%
AC1 B pass (rank≥2 or C≥40): False  Control C pass: False  AC1 credible (B and not C): False — FAIL
Net-positive guard (some B>A): True best_gain 164 — PASS (trade 2241→2405 +164, storage 2345→2497 +152)
Ratios bps: A 10240 B 10382
Legacies per policy (deterministic): production (land), storage (granary), trade (river), cash ()
```
AC1 FAIL: P_agri remains rank1, lead grew 55→92. River +2 labour triples channel (90 vs 30 grain over epilogue) but trade had least grain after agri (80 vs storage 110) and farm production is capped, so extra labour is grain-limited. Demand shift hurts storage most (3807→2497 -1310) but not enough to flip. Net-positive holds. Per review, next lever is not price (lever is labour count) but making channel larger via more grain stock for river or making raw price lower; both already at limits, so report FAIL honestly. Do not reword. API still serves FiveTurnGame (5) for e2e stability; epilogue via harness.

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
- `DECISIONS 026`: Land Network +15 vs labour×10 means low-labour cannot convert extra grain; keep weakest, do not buff.
- EPILOGUE_RAW_DEMAND 280/220/180, GRAIN_PER_LABOUR 10, FINISHED 3/10 @9500+800, HIRE 400/200, LAND +15.

### Normal verification

```bash
make test              # 150 passed, 1 warning in 2.49s
make lint              # All checks passed!
make type              # 0 errors, 0 warnings, 0 informations — 40 files analyzed (was 38 + epilogue_harness, domain/types)
make format-check      # 40 files already formatted (was 39)
make front-typecheck   # tsc --noEmit — 0 errors
make front-lint        # eslint . --ext .ts,.tsx — 0 problems
make front-test        # vitest run — 6 passed (6), 29 passed (29)
make check-all         # backend + frontend gates green
# four-arm harness (observed, NOT a pytest gate — reported honestly)
uv run --project backend python -m app.engine.epilogue_harness --n-seeds 200
# → AC1 credible FAIL (storage remains rank1, contraction -364%), Control C FAIL (no spurious), net-positive PASS (+181)
```

### Last known green

```
pytest 150 passed in 2.49s (1 warning: StarletteDeprecationWarning)
ruff check All checks passed!
pyright 0 errors, 0 warnings, 0 informations — 40 files analyzed
ruff format --check 40 files already formatted
tsc --noEmit — 0 errors (frontend)
eslint — 0 problems (no-restricted-syntax for /1000 and /10000 outside format.ts, no waitForTimeout)
vitest — 6 passed (6), 29 passed (29)
check-all: backend + frontend gates green
four-arm harness n=200: AC1 credible FAIL (P_agri storage rank1, lead 55→255), net-positive PASS (storage 2345→2526 +181)
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

History endpoint, SQLAlchemy/Alembic/Postgres, auth, LLM, `render.yaml` cloud deploy. Section 12 human playtest remains BLOCKED — awaiting real observations. Section 13 AC1 remains FAIL (credible) — needs stronger craft payoff retune, not rewording.

### Next milestone

Report four-arm numbers honestly (AC1 FAIL, net-positive PASS). Retune finished-goods payoff (price/efficiency) until AC1 credible PASS within ±20% demand bounds, or document why stronger craft needed. Do not advance to Section 14 (gated on human playtest). Keep API at 5-turn for e2e stability; epilogue via engine harness until AC1 passes.
