# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 12 — BLOCKED — AWAITING HUMAN PLAYTEST (2026-08-10) — Run-record instrumentation

**Instrumentation only (ORCHESTRATION.md §8):** Section 12 cannot be completed autonomously — requires real humans playing and reporting expectations vs. outcomes. This commit closes the one replayability gap named in the prompt: the ordered committed `choice_id`s were recorded nowhere. Frontend now accumulates exact server-provided ids in `App.tsx` local state (`committedIds: string[]`) and shows a pasteable run record on the completion screen (`seed`, `ruleset_version`, ordered ids) plus a "Copy run record" button with `navigator.clipboard` + textarea/execCommand fallback that never throws or logs a console error (AC7). No backend changes, no persistence, no analytics, no network calls — everything is local component state discarded on reload. Decision surface / outcome reveal / tableau untouched. `docs/playtest/` facilitator script is owned by the product owner. Section 12 stays BLOCKED until real observations arrive and the three highest-impact fixes are made.

### What exists

```
backend/
  app/
    main.py                    # create_app() -> FastAPI, mounts /api/v1 router
    api/
      __init__.py
      sessions.py              # GameSession{game_id, run_seed, revision, game, created_at, lock: asyncio.Lock, commands}, SESSION_STORE
      schemas.py               # CreateGameRequest/ChoiceRequest, ChoiceView, PlayerSummary, EmpireSummary{3 fields}, MarketView, RouteStatus{next_margin}, RivalHeadlines, OutcomeView{resolved context + causal_trace}, CompletionSummaryView{no history}, GameView{run_seed, ruleset_version, turn_limit=TURN_LIMIT}
      mappers.py               # choices_for legality/affordability +2 qty: buy 55/110 uncapped (DECISIONS 022), sell uncapped (DECISIONS 024 — was 150), ship pre-harvest, no turn/margin gate
      service.py               # create_game/get_game(with lock, no yield)/choose(with lock+sleep per DECISIONS 021) 404/409/422
      router.py                # POST /api/v1/games, GET /api/v1/games/{id}, POST /.../choices/{choice_id}
    domain/
      types.py                 # OperationState dormant, RouteState delay 0, regional_output 360
      trace.py                 # CausalNode delta strict, OutcomeDriver top-3
      pressure.py              # PressureState 7 fields
    engine/
      prototype.py             # TURN_LIMIT=5, default_start_state 280/410/360/4000/130
      actor.py                 # ship_margin reliability-aware, cost/affordable
      harness.py               # BatchConfig validation
      turn.py                  # _bounded_price, arbitrage quantity-weighted
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
    App.tsx                    # phase machine start→decision→reveal→completion (B2), displayPressure phase-selected (B3), committingRef guard (B8), revision: game.revision (B4), committedIds: string[] Section 12 instrumentation (exact id, order, local state, reset on Begin/PlayAgain)
    api/
      client.ts                # createGame/getGame/commitChoice (expected_revision)
      types.ts                 # GameView shapes
      queries.ts
    lib/
      format.ts                # money/pricePerUnit/percent — ONLY /1000 & /10000 site (K2)
      tableau.ts               # 3 independent rows (R1): estate farm≥15, storage≥180, trade route
      runRecord.ts             # Section 12: formatRunRecord(seed, rules, choiceIds) → "seed=… rules=… choices=…"
    components/
      StartScreen.tsx          # R8 Begin + R9 Age of Grain · Chapter I
      HeaderBar.tsx            # turn pips Turn n of 5, cash format.money
      WorldBand.tsx            # signal serif 22px, data-pressure-stage
      EmpireTableau.tsx        # R1 no arrows, data-testid tier-*
      MarketCard.tsx           # R2: price / grain + Availability + Demand
      MarketPulse.tsx          # side-by-side Home/River + RouteLine
      RouteLine.tsx            # R4: Current route spread … / grain (quote)
      RivalsStrip.tsx          # B5: rival_headlines resolved context, empty state turn 0
      DecisionBlock.tsx        # B1: group by kind, qty verbatim, exact id submit
      OutcomeReveal.tsx        # B2/B5/B7/R6/R7: 7 beats data-reveal-beat/state, drivers impact_money, Home price, from 0
      CompletionSummary.tsx    # R10: hero wealth, total change, estate, run record, rivals, seed·rules + Section 12 run-record-replay block + Copy run record (clipboard with fallback, no console error)
      FooterDebug.tsx          # R12: seed · rules
    styles/
      tokens.css               # --market-home/--market-river identity + --page-ground atmosphere + [data-pressure] + font stacks R11 + tabular-nums
      app.css                  # 480px centred, cards (verb 8px/13px, qty 3px/11px), reveal, commit bar static 8px (J2 0% occlusion, J4 river single line)
    __tests__/
      format.test.ts           # 8 tests inc. /1000 grep via eslint
      tableau.test.ts          # 7 tests inc. positive investing + negative hold×5 flat (B9)
      decisionBlock.test.tsx   # 5 tests inc. verbatim {7,999} (B1), hold cost 0 (B6), 9→6 cards
      commit.test.tsx          # 1 test synthetic turn 2 rev 7 → 7 (B4) — vestigial removed J3
      outcomeReveal.test.tsx   # B7 magnitude
      runRecord.test.tsx       # Section 12: 4 tests — formatRunRecord verbatim+order, reconstruction fails, copy fallback no throw/no console.error, replay block contains seed/rules/ids
  e2e/
    critical.spec.ts           # 4 tests: full 5-turn mobile (expand→granary S2, 4 viewport 390×844 J1 mobile-only, B2/B3/B5/B6/B7/B9), desktop smoke, AC2 no table, AC4 rivals; B8 sync double-click, no waitForTimeout, console+pageerror + Section 12 run-record-replay asserts seed/rules + 5 ids in order + Copy button
    screenshots/
      first-decision.png        # 390×844 viewport J1 scrolled top — J2 0% (static bar, was 82%)
      drought-warning.png       # turn 2 worsening_dry — viewport J1 1073×2321@2.75x
      drought-reveal.png        # after turn 3: header aftermath vs reveal drought B3 — viewport J1
      final-summary.png         # turn 5 R10 — viewport J1
  dist/                        # vite build output
Makefile                       # test/lint/type/format-check + front-type/front-lint/front-test/front-e2e + check-all
docs/plans/2026-08-10-section-11-mobile-react-playable.md  # plan revised for B1–B9 + R1–R12 + S1–S2
docs/plans/2026-08-10-section-11-design-direction.md      # partially superseded banner (review wins)
docs/plans/2026-08-10-section-11-review-round-1.md        # consolidated review (9 blocking, 12 rulings)
docs/plans/2026-08-10-section-12-playtest-gate.md        # Section 12 instrumentation plan — committedIds + run-record + copy fallback + tests
```

### Boundaries

- In-memory sessions only; no Postgres/SQLAlchemy/Alembic/auth/LLM/history endpoint/cloud deploy.
- `GameView` is presentation — frontend never recomputes cost/margin/wealth/quantity; `ChoiceView.cost`/`quantity`/`label`/`id` verbatim per B1/B6, `route_status.next_margin` as quote per R4, `format.ts` only `/1000`/`/10000` site per K2 (eslint no-restricted-syntax). `ship_margin` reliability-aware.
- Per-session `asyncio.Lock` with `sleep(0)` in `choose` per DECISIONS 021; `revision` distinct from `turn` (B4) — `expected_revision: game.revision` always, falsified by synthetic `turn 2 rev 7` test.
- `available_choices` legality+affordability only, `buy`/`sell`/`ship` uncapped per DECISIONS 022/024 (sell `min(inventory,150)` removed), `ship` no margin gate, pre-harvest estimate via `compute_farm_output`. Two quantities per verb where applicable, grouped into one verb card (max 6 cards, 9 choices after route).
- Frontend phase machine `start → decision → reveal → completion` (B2) — fifth commit has both `latest_outcome` and `completion_summary`, reveal shown before completion via `displayPressure` phase-selected (B3). Top-level `rival_headlines` is resolved-turn context (B5) — reveal source matrix enforced.
- Drivers top-3 with residual NOT represented (B7) — no stacked bar, `impact_bps` is magnitude, colour from `impact_money`. `price_delta` is Home price (R6), delta animates `0→delta` (R7), `command_quantity` is requested (R5).
- Pure engine boundary: `engine`+`domain` no `fastapi`/`alembic`/`app.api`; `tableau()` pure with 3 independent rows (R1) thresholds `farm≥15`/`storage≥180`/`route` (B9 exact before/after + negative hold flat).
- `Makefile` now has `front-type/front-lint/front-test/front-e2e` plus `make check-all` per S1 — `ORCHESTRATION.md` §4 verification is `make test && make lint && make type && make format-check` plus frontend via `check-all`.
- Section 12 instrumentation: ordered `choice_id`s accumulated in `App.tsx` local state (`committedIds`) from the exact `selectedId` sent to the server (never reconstructed), reset on Begin/PlayAgain, discarded on reload. Run record `seed=… rules=… choices=…` rendered in `CompletionSummary` (`data-testid="run-record-replay"`) with `Copy run record` (`data-testid="copy-run-record"`) using `navigator.clipboard` with textarea/execCommand fallback; handler swallows errors, logs no console error (AC7). No backend changes, no persistence, no telemetry, no network calls.

### Normal verification

```bash
make test              # 150 passed, 1 warning in 2.06s
make lint              # All checks passed!
make type              # 0 errors, 0 warnings, 0 informations — 38 files analyzed
make format-check      # 39 files already formatted
make front-type        # tsc --noEmit — 0 errors
make front-lint        # eslint . --ext .ts,.tsx — 0 problems (no-restricted-syntax, no waitForTimeout)
make front-test        # vitest run — 6 passed (6), 29 passed (29) — 4 new in runRecord.test.tsx
make check-all         # backend + frontend gates green — check-all: backend + frontend gates green
# e2e (via npx playwright test)
# — 8 passed (4 mobile 390×844 + 4 desktop 1280×800, 45.0s) — full 5-turn mobile (expand→granary, 4 viewport screenshots, run-record-replay asserts seed/rules + 5 ids in order + Copy button click no console error), drought-warning turn2 worsening_dry, drought-reveal B3 header aftermath vs reveal drought, final-summary R10; J2 0% occlusion, B8 sync double-click requestCount 1, no waitForTimeout, console+pageerror zero
```

### Last known green

```
pytest 150 passed in 2.06s (1 warning: StarletteDeprecationWarning)
ruff check All checks passed!
pyright 0 errors, 0 warnings, 0 informations — 38 files analyzed
ruff format --check 39 files already formatted
tsc --noEmit — 0 errors (frontend)
eslint — 0 problems (no-restricted-syntax for /1000 and /10000 outside format.ts, no waitForTimeout)
vitest — 6 passed (6), 29 passed (29) — 4 new Section 12 runRecord tests
playwright — 8 passed (4 mobile 390×844 + 4 desktop 1280×800) — 45.0s — full 5-turn + run-record-replay seed/rules + ordered ids + Copy run record click, no console errors
check-all: backend + frontend gates green
```

### Decisions relevant

- DECISIONS 017: no-strategy-gatekeeping, two quantities, per-session lock, trace/latest-only, OperationState dormant, ship_margin single helper (principle verbatim).
- DECISIONS 018 revised (R1): pyright strict app + standard tests (38 files).
- DECISIONS 021 (R3): per-session lock `sleep(0)` load-bearing.
- DECISIONS 022 (R2): buy cap removal 55/110.
- DECISIONS 023 (NEW): Section 11 decision surface — verb cards + quantity verbatim + exact id + Commit + phase-selected pressure + `cost !== null` (reframed per BUILD_SPEC §0.2 — active section outranks DECISIONS.md).
- DECISIONS 024: sell cap removal — `sell` now uncapped at inventory (was 150), `85/170` at 170.
- DECISIONS 016: matched controls, price-taking, hold rank 4/4, etc.

### Intentionally missing

History endpoint, SQLAlchemy/Alembic/Postgres, auth, LLM, `render.yaml` cloud deploy. Section 12 human playtest remains BLOCKED — awaiting real observations (ORCHESTRATION.md §8).

### Next milestone

Section 12 remains BLOCKED — AWAITING HUMAN PLAYTEST. Facilitator script is owned by product owner (`docs/playtest/`). When written observations arrive, classify each per §12 and fix only the three highest-impact problems. No new goods/turns/rivals/DB/auth/LLM. After handover, proceed to Section 13 City & Craft Transition Epilogue.
