# Section 11 — Mobile-First React Playable — Plan

**Date:** 2026-08-10 — Revised 2026-08-10 per `docs/plans/2026-08-10-section-11-review-round-1.md` (B1–B9, R1–R12, §4, S1–S2) — grill §1 items remain settled, not relitigated
**Branch:** `section/11-mobile-react-playable` (from `origin/main` at Section 10 COMPLETE + DECISIONS 024 — `STATE.md` 150 tests green)
**Spec Authority:** `BUILD_SPEC.md` Section 11 (line 1345, Status NOT STARTED) + global §§6–11 + `AGENTS.md` + `frontend/AGENTS.md`
**Design Authority:** `docs/plans/2026-08-10-section-11-design-direction.md` (Claude, per `docs/ORCHESTRATION.md` §5) — **partially superseded by review round 1**; where they disagree, the review wins (see `design-direction.md` banner). Binding input remains measured `GameView` payload (`run_seed="playtest-1"`).
**Related:** `backend/app/api/schemas.py` (`GameView`, `ChoiceView`, `OutcomeView`, `CompletionSummaryView`, `MarketView`, `RouteStatus`), `backend/app/api/mappers.py` (`choices_for` — now sell uncapped per DECISIONS 024), `backend/app/engine/prototype.py` (`TURN_LIMIT=5`, `default_start_state`), `backend/app/engine/pressure.py` (`PRESSURE_ARC` 5 stages), `backend/app/domain/trace.py`, `DECISIONS.md` 017/022/024, `STATE.md` Boundaries (150 tests), `BUILD_SPEC §31`, `BUILD_SPEC §0.2` (active section outranks DECISIONS.md)

---

## Goal

Ship the first browser-playable vertical slice: a phone-excellent (390×844) single-column React app that lets a new player **Begin → read signal → inspect markets/rivals/route → choose one major action → commit → see time advance → see outcome reveal → understand why → continue** for exactly 5 turns, consuming `GameView` truthfully, with zero economy recomputation in the frontend, and passing `BUILD_SPEC §11` AC1–AC8 plus Playwright critical path with four screenshots and zero console errors.

---

## Success Criteria (maps to AC1–AC8 + gates)

Each AC has a falsifiable rule in Validation; summary:

1. **AC1 — 5-turn completion on phone.** Mobile viewport 390×844: new player can `Begin` → `POST /api/v1/games` → 5 × `POST …/choices/{id} {expected_revision}` → reveal after 5th commit then `completion_summary.is_complete === true`.
2. **AC2 — No dense table required.** Decision surface is verb cards + quantity + commit; choosing never requires opening a detail table. Assertion: no `<table>` in decision surface; all required info (label cost, margin sign) visible on main screen.
3. **AC3 — Every result says what changed and why.** After each commit, reveal shows `wealth_delta`, `inventory_delta`, `price_delta` (Home price, see R6) with sign-colour from `impact_money`, ≤3 verbatim `drivers` (residual not represented, see B7), and collapsed `causal_trace` proof.
4. **AC4 — Rivals visible throughout.** Persistent rivals card rendered every turn; turn 0 explicit empty state, turns ≥1 `mira`/`daran` headlines (top-level `rival_headlines` — not `RivalTurnResult`), completion shows `final_rival_headlines`.
5. **AC5 — Empire visibly changes.** `tableau()` pure function maps three real fields to three independent milestone rows (R1); investing run changes exact visible state, passive run stays flat, and E2E asserts exact before/after text around a known commit.
6. **AC6 — No double-submit.** One rapid double activation emits exactly one HTTP mutation (controlled race with `page.route` defer), commit control disabled/busy while pending, final revision +1 once.
7. **AC7 — Zero console errors on critical path.** Playwright collects both `console` error and `pageerror` from navigation start; any entry fails.
8. **AC8 — Playwright 5-turn mobile + desktop smoke.** Mobile full flow + 4 screenshots; desktop smoke (start + 1 commit + reveal) both green, zero `waitForTimeout`.

**Gates remain green:** `make test` (150 backend), `make lint`, `make type`, `make format-check` plus frontend gates (`npm run typecheck`, `npm run lint`, `npm run test`, `npx playwright test`) and `make check-all` — see §Validation and S1.

---

## Context And Current Facts

- **`frontend/` empty.** Only `.gitkeep` + `AGENTS.md`. This section scaffolds Vite + React + TypeScript + TanStack Query from scratch. No backend change — dev/test hit API via Vite proxy. **Pull first:** `DECISIONS 024` landed on this branch (sell cap `min(inventory,150)` removed → full `inventory` now, `150→151` tests). Do not reintroduce `150`.
- **Backend is source of truth.** `GameView` fields measured via `TestClient(create_app())` (`PYTHONPATH=backend uv run`):

  Regeneration (authoritative, run from `backend/`):

  ```bash
  PYTHONPATH=. uv run python3 -c "
  from fastapi.testclient import TestClient
  from app.main import create_app
  import json
  app=create_app(); c=TestClient(app)
  print(json.dumps(c.post('/api/v1/games', json={'run_seed':'playtest-1'}).json(), indent=2))
  "
  ```

  Measured turn-0 values (representative):

  | field | raw | unit |
  |---|---|---|
  | `player_summary.cash` | `1000` | `Money` |
  | `player_summary.wealth` | `1100` | `Money` |
  | `ChoiceView.cost` (hold 0, expand 500, granary 300, route 400, buy 275 for 55) | `Money` | whole coins; `null` for sell/ship |
  | `home_valley_market.current_price` | `5000` | `PriceMilliunits` (→ 5.000) |
  | `river_town_market.current_price` | `5200` | milliunits |
  | `route_status.transport_cost_per_unit` | `300` | milliunits (→ 0.300) |
  | `route_status.next_margin` | `-100` | milliunits (quote, not prediction — R4) |
  | `home_valley_market.responsiveness` | `4000` | bps (40%) — not shown on primary screen (R2) |
  | `OutcomeView.price_delta` | e.g. `157` | milliunits Home price (R6) |
  | `OutcomeView.wealth_delta`, `impact_money` | e.g. `-500`, `550` | `Money` |
  | `OutcomeView.command_quantity` | `20` | requested, not necessarily executed (R5) |
  | `OutcomeDriver.impact_bps` | e.g. `3238` | magnitude, not signed (B7) |

  After one `expand_farm`: `farm 5→15`, `storage 130`, `route false`, `cash 500`, `inventory 130` (capped), `home price 5157`, `river 6240`, `supply 380`, `choices` collapse.

- **Traps measured (design direction §0, re-measured in grill, corrected by review):**
  - `rival_headlines === null` at turn 0 only; thereafter 2 strings; `completion_summary.final_rival_headlines` at end. **Top-level `rival_headlines` is resolved-turn context, not next-decision context** (B5) — unlike `signal`/`world`/`pressure_stage`.
  - `turn` is 0-based upcoming decision; `turn+1 of turn_limit` for display; `resolved_turn` 0-based for reveal; completion is `completion_summary !== null` (never `turn===turn_limit`). **Fifth response has both `latest_outcome !== null` and `completion_summary !== null` and `available_choices === []`** (B2).
  - **Choice count re-measured:** turn 0 is **8** choices (6 distinct `kind`s). After `secure_route` (cash 600, inv 70, route true) it is **9** choices (`hold, expand_farm, build_granary, buy×2, sell×2, ship×2`) — max **9 across 6 verbs**; `secure_route` + `ship_grain` mutually exclusive so 7 verbs unreachable. `sell_grain` now uncapped (e.g. `170` at inventory 170 per DECISIONS 024, not `150`). All quantities vary (`55/110`, `30/60`, `65/130`, `35/70`, `10/20`, and uncapped sells).
  - `latest_outcome.world/pressure_stage/title/deltas/drivers/trace` is resolved turn; top-level `world/pressure_stage/signal` is next decision; **rival headlines are resolved**; crossing any produces wrong weather or wrong rival beat.
  - `empire_summary` exactly 3 fields `{farm_capacity, storage_capacity, route_established}`; `OperationState` dormant per `types.py:59`.
  - `river_town_market` and `home_valley_market` each have `supply/demand/base_price/current_price/responsiveness`; only `current_price`, `supply` (as "Availability"), `demand` shown on primary per R2.

- **Existing gates:** `Makefile` `make test` (`uv run --project backend pytest -v`), `lint` (`ruff check`), `type` (`cd backend && uv run pyright` strict app + standard tests, 38 files), `format-check`. All green (150 passed). No `render.yaml` change this section.

---

## Constraints And Non-goals

**Must satisfy:**

- No backend edits. `frontend/` talks via Vite proxy `/api → http://localhost:8000`; `VITE_API_URL` defaults to `/api/v1` per `frontend/AGENTS.md`. If a schema shape change looks unavoidable, escalate — don't edit `backend/`. Do not reintroduce `sell 150` cap (DECISIONS 024).
- `GameView` is presentation — no frontend recompute of cost/margin/wealth/affordability/capacity/quantity. Use `ChoiceView.cost`/`quantity`/`label`/`id`, `route_status.next_margin`, `player_summary.wealth` verbatim.
- `expected_revision` on every commit; `409` handling branches on `completion_summary !== null` (never string-parse `detail`), refetch then handle.
- `DECISIONS 017` principle honoured — every legal choice remains reachable; economic bad moves remain choosable; never hide legal sells/buys.
- Desktop is centered single column `max-width: 480px`, not a dashboard — same component tree.

**Out of scope — do NOT build (`BUILD_SPEC §31`, design direction §8):**

- Auth, DB/Postgres, LLM/advisor, real art pipeline, history/replay screen, bottom-nav architecture, multiple age screens, free-text commands, sound, i18n, animation libraries beyond reveal beats, two-column desktop dashboard, backend `next_margin` rename.

---

## Key Decisions

### K1 — Vite + React + TypeScript + TanStack Query, proxy-only backend reach

- **Decision:** Scaffold with `npm create vite@latest` (react-ts), add `tanstack/react-query`, no `react-router` — single game route with local phase. Vite `server.proxy` `{ "/api": "http://localhost:8000" }` for dev and Playwright `webServer`. `VITE_API_URL` env read with fallback `/api/v1`. No CORS addition.
- **Rejected:** Next.js/SSR, Redux/Zustand (overkill; server state is just `GameView`), direct `fetch` without Query (loses cache/invalidation/isPending).

### K2 — Unit-conversion boundary is `format.ts` only (B7-corrected, grill-narrowed)

- **Decision:** Single module `src/lib/format.ts` exporting `money`, `pricePerUnit`, `signedMoney`, `signedPricePerUnit`, `percent`. Every other file imports from it. No inline `/1000` or `/10000` elsewhere.

```ts
// src/lib/format.ts — ONLY place allowed to divide by 1000 or 10000 (price/bps)
export function money(n: number): string                  // 1000 → "1,000"
export function signedMoney(n: number): string            // -500 → "−500" (U+2212)
export function pricePerUnit(milli: number): string       // 5000 → "5.000"
export function signedPricePerUnit(milli: number): string // -100 → "−0.100", 157 → "+0.157"
export function percent(bps: number): string              // 4000 → "40%"
```

Two enforcement layers (grill + review 409-confirmed):

1. **Vitest grep assertion (falsifiable):** scan `src/` excluding `format.ts` for `/\s*1000` and `/\s*10000\b` — not bare `/100` (false-alarms on `width/100*pct`, `Date.now()/1000`). Fails if any component does `current_price / 1000`.

```ts
test('no inline price/bps division outside format.ts', async () => {
  const hits = await grepOutside('src', 'format.ts', /\/\s*1000|\/\s*10000\b/);
  expect(hits, `raw price/bps maths outside format.ts: ${hits.join('; ')}`).toEqual([]);
});
```

2. **ESLint `no-restricted-syntax`** forbidding `BinaryExpression[operator="/"][right.value=1000]` outside `format.ts`.

Tests for correctness: `money(1000)==="1,000"`, `pricePerUnit(5000)==="5.000"`, `signedPricePerUnit(-100)==="−0.100"`, `signedPricePerUnit(157)==="+0.157"` (never `5000`), `percent(4000)==="40%"`, `signedMoney(-500)==="−500"`.

**B7 implication:** `impact_bps` is magnitude (e.g. `[3238,3238,3238]` vs `impact_money [263,263,-263]`). Colour from `impact_money` sign, never `impact_bps`.

### K3 — Pressure drives theming via single phase-selected `data-pressure` source (B3 + R3)

- **Decision:** Root `<div data-pressure={displayPressure}>` where

```tsx
const displayPressure =
  phase === "reveal" && game.latest_outcome
    ? game.latest_outcome.pressure_stage
    : game.pressure_stage;
```

then `data-pressure={displayPressure}` on the root. One source, phase-selected — no per-component weather logic. This resolves the review-found contradiction: my design direction §1.2 painted the drought reveal in aftermath colours.

- **Token split per R3** — market identity is invariant under pressure:

```css
/* identity — NEVER altered by pressure */
--market-home:  #C8912F;
--market-river: #2F7B78;
/* atmosphere — pressure themes alter only these */
--page-ground, --page-rule, --world-accent, --ink
:root { --page-ground:#F5EDE0; --page-hi:#FFFAF1; --ink:#1F1A14; --grain:#C8912F; --river:#2F7B78; --drought:#A6412B; --gain:#4A7C43; --rule:#DCCFBA; }
/* card border/title/glyph uses --market-home/--market-river; signed number uses --gain/--drought */
[data-pressure="normal"]        { --page-ground:#F5EDE0; }
[data-pressure="early_dry"]     { --page-ground:#F0E6D3; }
[data-pressure="worsening_dry"] { --page-ground:#E8DDC8; }
[data-pressure="drought"]       { --page-ground:#E0D5BE; --ink:#2A1F14; }
[data-pressure="aftermath"]     { --page-ground:#EDE8DC; }
```

`@media (prefers-reduced-motion: reduce) { * { transition:none !important; } }`

### K4 — Decision surface: verb cards + quantity + explicit commit — documented deviation (B1-corrected, B6-corrected, R1)

- **Decision:** Group `ChoiceView`s by `kind`. One verb card per distinct `kind` (max 6 cards — `secure_route` + `ship` mutually exclusive, so 7 unreachable). **Render exactly the `quantity` values present in `available_choices`, in payload order** — never compute `min//2` or `min(inventory,150)`. 1 value → no toggle, 2 → two-option segmented control, 3+ → N options. **Submit the exact server-provided `ChoiceView.id`** — never reconstruct `kind + ":" + quantity` (`buy_grain:55` is a mapper detail, not a contract).
- **Quoted quantities vary** (`55/110`, `30/60`, `65/130`, `35/70`, `10/20`, uncapped `170` per DECISIONS 024). Falsifiable: mocked `sell_grain` `{7, 999}` must render `7` and `999`.
- **Label/cost per B6:** render `ChoiceView.label` as authoritative copy; show `cost` only when `cost !== null` (check `!== null`, not truthiness — `hold` has `cost === 0` and would vanish). Never derive proceeds/shipment revenue; `sell`/`ship` have `cost === null` and no proceeds field.
- **R1 — no arrows/prerequisites:** vertical stack as lightweight growth indicator, but no directional arrows or implied ordering — reached rows may be non-contiguous. Three independent milestone rows:

```
Estate   Family Farm  →  Expanded Estate          (farm_capacity >= 15)
Storage  Granary  130 → 180 → …                   (storage_capacity >= 180)
Trade    River access: Closed → Secured           (route_established)
```

Each lights independently (see K6 for thresholds).

**`DECISIONS.md` entry text (to be added verbatim on implementation) — reframed per review §4 (active section outranks DECISIONS.md per BUILD_SPEC §0.2):**

> ### 023 — Section 11 Decision Surface — Verb Cards With Quantity + Explicit Commit (2026-08-10)
> - **Context:** Section 11's "2–4 action buttons" cannot be implemented as 2–4 direct legal actions against the frozen Section 10 API, which exposes up to six simultaneous legal verbs and intentionally preserves two commit depths per quantity verb. Section 10's `available_choices` (e.g. `buy_grain:55/110`, `sell_grain:85/170` uncapped per DECISIONS 024, `ship_grain:10/20`) is itself a Section 11 input constraint.
> - **Decision:** Group `ChoiceView` by `kind` into one verb card per distinct `kind` (max 6). Verbs with multiple quantities render a single card with quantity options exactly as supplied in `available_choices`, in payload order; the exact server-provided `ChoiceView.id` is submitted. A single explicit Commit button preserves "one meaningful major action per turn" and carries `expected_revision: game.revision` (never `game.turn`). Cost shown only when `cost !== null` (`hold` has `0`); `ChoiceView.label` is authoritative for `sell`/`ship`.
> - **Rationale:** Section 11 therefore interprets the requirement as protecting a small, legible decision surface rather than imposing a hard count on server-supplied choices. All legal choices remain directly visible; quantity variants are grouped within one verb control; a single explicit Commit preserves the turn's major-action semantics. This is an orchestrator-approved reconciliation of a requirement that cannot be satisfied literally against its own API, not `DECISIONS` overriding `BUILD_SPEC`. Rejected: three category controls (Invest/Trade/Hold) hiding real choices behind expansion — hits "2–4" literally but makes legal actions less legible and violates "required decision information visible on main screen".
> - **Consequence:** No legal move hidden; `DECISIONS 017` clause 1 upheld; presentation grouping is not authorization.

### K5 — Outcome reveal is a staged phase, not a conditional panel (B2, B5)

- **Decision:** Explicit presentation phase machine, with `GameView` remaining the only server-state source:

```
decision --commit--> reveal --Continue--> decision
                      └----(after turn 5, "Finish")----> completion
```

`phase ∈ {decision, reveal, completion}` is presentation state, not server state. The obvious `if (game.completion_summary) return <CompletionSummary/>` skips the fifth reveal — every AC would still appear satisfied.

- **Source matrix per B5** (top-level `rival_headlines` is resolved-turn context):

| Content | Source |
|---|---|
| turn / title / world / pressure / deltas / drivers / trace | `latest_outcome.*` |
| Mira + Daran | top-level `rival_headlines` |
| next threat (hand-off) | top-level `signal` |

`RivalTurnResult` is engine-private, never exposed; `OutcomeView` has no rival field.

### K6 — `tableau()` pure function (B9-corrected, R1)

- **Decision:** `src/lib/tableau.ts` pure `tableau(empire: EmpireSummary) -> Tier[]` with thresholds justified from measured `default_start_state` (`farm 5 +10`, `storage 130 +50`, `route false→true`). Three independent milestones per R1:

```ts
export type Tier = { id: string; label: string; reached: boolean };
export function tableau(empire: { farm_capacity:number; storage_capacity:number; route_established:boolean }): Tier[]
// Estate  — reached when farm_capacity >= 15  (one expansion) — measured 5→15
// Storage — reached when storage_capacity >= 180 (one granary) — measured 130→180
// Trade   — reached when route_established === true — measured false→true
// (plus the implicit Family Farm base — always reached)
```

- Tier is boolean, not level — farm 25 still tier 1, storage 230 still tier 2; avoids inventing `OperationState.level`.
- **AC5 falsifiable three ways per B9 + grill:** (1) positive investing run `{5,130,false}→{15,180,false}` must increase reached count; (2) negative passive run `{5,130,false}→{5,130,false}` (hold×5) must stay equal; (3) E2E DOM around known commit asserts exact visible before/after state (`Farm capacity 5` / "Expanded Estate" unreached → `Farm capacity 15` / reached), not `not.toEqual`.

### K7 — Frontend gates and Makefile integration (S1)

- **Decision:** Frontend scripts: `typecheck` (`tsc --noEmit`), `lint` (`eslint` flat + `prettier --check`), `test` (`vitest run`), `e2e` (`playwright test`). Makefile adds `front-type`, `front-lint`, `front-test`, `front-e2e` that `cd frontend && npm run ...`, plus **`make check-all`** running all backend and frontend gates (required by review S1 to prevent drift per `ORCHESTRATION.md` §4). `make test/lint/type/format-check` remain backend. `STATE.md` "Normal verification" lists frontend commands with observed output (S1).

---

## Recommended Approach

### File layout for `frontend/` (scaffolded from scratch)

```
frontend/
  index.html
  vite.config.ts              # proxy /api → 8000, VITE_API_URL fallback /api/v1
  tsconfig.json               # strict
  package.json                # vite, react, @tanstack/react-query, vitest, @testing-library/react, jsdom, playwright, eslint (flat), prettier
  public/
  src/
    main.tsx                  # createRoot + QueryClientProvider
    App.tsx                   # phase machine: start → decision → reveal → completion
    api/
      client.ts               # fetch wrappers: createGame, getGame, commitChoice (expected_revision: game.revision)
      queries.ts              # TanStack Query keys + mutations, isPending + committingRef guard
      types.ts                # GameView shapes (hand-typed from schemas.py, minimal)
    lib/
      format.ts               # money/pricePerUnit/percent — ONLY /1000 and /10000 site
      tableau.ts              # tableau(empire) -> Tier[] (three independent rows)
      pressure.ts             # PressureStage type helper (optional)
    components/
      StartScreen.tsx         # R8: Begin button, Age of Grain · Chapter I, seed display
      HeaderBar.tsx           # Age/chapter label (R9) · Turn pips · cash (format.money)
      WorldBand.tsx           # display-serif signal, pressure-tinted via inherited data-pressure (R3)
      EmpireTableau.tsx       # R1: three independent rows, no arrows
      MarketPulse.tsx         # R2: Home/River side-by-side
      MarketCard.tsx          # R2: price / grain (large) + Availability + Demand; no base_price/responsiveness
      RouteLine.tsx           # R4: "Current route spread +0.597 / grain" (never "margin"/"profit"), sign colour — quote
      RivalsStrip.tsx         # empty state at turn 0, headlines thereafter (B5 source)
      DecisionBlock.tsx       # B1: verb cards grouping, quantities verbatim, exact id submit
      VerbCard.tsx            # B6: label authoritative, cost !== null check (0 shown)
      QuantityToggle.tsx      # B1: options from ChoiceView.quantity verbatim
      OutcomeReveal.tsx       # B2 phase, B5 source matrix, R6/R7 numbers, B7 drivers, data-reveal-state
      CompletionSummary.tsx   # R10 hierarchy: hero wealth, total change, estate, run record, rivals, seed·rules
      FooterDebug.tsx         # R12: seed playtest-1 · rules 1.0
    styles/
      tokens.css              # --market-home/--market-river (identity) + --page-ground etc (atmosphere) + [data-pressure] overrides + font stacks (R11) + tabular-nums
      app.css                 # layout: single column max-width 480 centred, cards, typography, motion
    __tests__/
      format.test.ts          # B7 magnitude test, /1000 grep
      tableau.test.ts         # B9 exact before/after + negative hold
      decisionBlock.test.tsx  # B1 verbatim quantities, B4 revision=7, B6 cost 0
      outcomeReveal.test.tsx
  e2e/
    critical.spec.ts          # mobile 390×844 full flow (expand then granary per S2) + desktop smoke
  playwright.config.ts        # two projects, webServer, no waitForTimeout
  eslint.config.js            # flat config, no-restricted-syntax for price maths and waitForTimeout
  vitest.config.ts            # environment jsdom
```

**Component tree (render order — decision screen):**

```
App (phase: start → decision → reveal → completion; data-pressure=displayPressure per B3)
 ├─ StartScreen         (R8: Begin, R9 label, seed)
 ├─ HeaderBar           (R9: Age of Grain · Chapter I · Turn pips n/5 · cash)
 ├─ WorldBand           (signal serif, pressure via inherited data-pressure)
 ├─ EmpireTableau       (R1: 3 independent rows, no arrows)
 ├─ MarketPulse
 │   ├─ MarketCard (Home Valley — --market-home, price "5.000 / grain", Availability, Demand)  R2
 │   ├─ RouteLine (R4: "Current route spread …", dashed when !established)                    R4
 │   └─ MarketCard (River Town — --market-river)                                              R2
 ├─ RivalsStrip         (B5: empty state or Mira/Daran headlines)
 ├─ DecisionBlock       (B1: verb cards, quantities verbatim, exact id)
 │   ├─ VerbCard × (hold|expand_farm|build_granary|secure_route|buy_grain|sell_grain|ship_grain)  B6
 │   │   └─ QuantityToggle (options = ChoiceView.quantity values verbatim)
 │   └─ CommitButton    (disabled when !selected || isPending, committingRef guard B8)
 ├─ OutcomeReveal       (B2: overlay/inline, data-reveal-state, 7 beats, Skip, R6/R7)        B2/B5/B7/R6/R7
 ├─ CompletionSummary   (R10: hero wealth, estate, run record, rivals, Play again)            R10
 └─ FooterDebug         (R12: seed · rules)
```

Desktop: same tree, `max-width: 480px` centred on wider parchment ground.

### Exact unit-conversion boundary (`format.ts`) — see K2 above

### Pressure theming — see K3 above (phase-selected, R3 token split, R11 font stacks)

- **Typography per R11** (implementable stacks, no webfonts):

```css
--font-display: ui-serif, Georgia, "Iowan Old Style", "Palatino Linotype", serif;
--font-ui: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
/* signal 22px/500 display; outcome title 28px/600 display; rival headline 15px/400 italic display; section labels 11px/600 uppercase ui; body+numbers 15px/400 ui; hero 32px/600 ui */
/* all numerals font-variant-numeric: tabular-nums */
```

### Decision surface — see K4 above (B1 verbatim, B6 cost, R1 no arrows, B4 revision)

- **B4 falsifiable:** unit test with synthetic `GameView{turn:2, revision:7}` asserts POST body `{"expected_revision":7}` (sending `turn` would send `2` and pass happy path).
- **B8 double-submit guard (AC6):** TanStack `isPending` + synchronous `committingRef` guard (`if (ref.current) return; ref.current=true`) reset on `onSettled`, plus `disabled` while pending. Playwright holds `/choices/` open via `page.route` deferred gate, fires two activations while in flight, asserts exactly one POST left page.

### Outcome-reveal beat sequence + test hooks (B2, B3, B5, B7, R6, R7)

Measured `PRESSURE_ARC` indices (hold path):

| turn idx | before `pressure_stage` | after `pressure_stage` | after `latest_outcome` |
|---|---|---|---|
| 0 | `normal` | `early_dry` | `normal` / "A Growing Settlement" |
| 1 | `early_dry` | `worsening_dry` | `early_dry` / "Surplus" |
| 2 warning | `worsening_dry` "The dry spell persists…" | `drought` | `worsening_dry` / "Warning Signs" |
| 3 drought commit | `drought` "Drought cuts farm output…" | `aftermath` | `drought` / "Drought" ← **drought reveal** |
| 4 | `aftermath` | `aftermath` | `aftermath` / "Aftermath" |

- **B2:** fifth response has both `latest_outcome` and `completion_summary` — reveal before completion.
- **B3:** drought reveal paints in `drought` colours while header shows `aftermath` — `displayPressure` phase-selected makes this true.
- **B5 source matrix** as in K5.
- **B7:** no "100% explained" stacked bar; render three labels + `impact_money` only; never compute residual; colour from `impact_money` sign, not `impact_bps`.
- **R6:** label "Home price +0.157 / grain" (not unlabelled "Market price").
- **R7:** deltas animate `0 → delta`, not `1,100 → 600`.
- **R4:** route line label "Current route spread +0.597 / grain" (never "margin"/"profit"); quote.

| beat | `data-reveal-beat` | reads | note |
|---|---|---|---|
| 0 time | `0` | `resolved_turn+1`, `title` serif 28px | `Turn {resolved_turn+1}` inside reveal |
| 1 world | `1` | `latest_outcome.world/pressure_stage` | data-pressure drought highlight |
| 2 numbers | `2` | `wealth_delta`, `inventory_delta`, `price_delta` (Home) | `signedMoney`/`signedPricePerUnit` from 0, tabular-nums, gain/drought |
| 3 drivers | `3` | `drivers[0..2]` verbatim label + `impact_money` | never `impact_bps`; no residual |
| 4 why | `4` | `causal_trace.nodes` (~40) | collapsed closed, Skip reveals |
| 5 rivals | `5` | top-level `rival_headlines` | Mira/Daran for this resolved turn |
| 6 next threat | `6` | top-level `signal` | only beat reading top-level |

Container `data-testid="outcome-reveal"` with `data-reveal-state="idle"|"revealing"|"complete"`, `data-reveal-beat` per beat, `prefers-reduced-motion` collapses to `complete` instantly. Playwright waits on `data-reveal-state="complete"`.

Screenshot scoping (proves B3):

```ts
await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="1"]')).toContainText('Drought');
await expect(page.locator('[data-testid="world-band"]')).toContainText(/aftermath/i);
```

### `tableau()` pure function — see K6 above (B9 exact assertion, R1 rows)

### Rulings adopted

- **R2 market card anatomy:** price + Availability + Demand only; `supply` copy "Availability 280" (not "280 grain available"), `base_price`/`responsiveness` not on primary.
- **R5 command_quantity:** requested, not executed — "You ordered: Ship 20" if shown; actual from `domain_effects`/`trace`.
- **R8 start:** `StartScreen` with `Begin` button (not auto `POST`), hosts `R9` label and seed.
- **R9 label:** exactly `Age of Grain · Chapter I` in one constant, presentation-only.
- **R10 completion hierarchy:** hero `Final wealth`, signed `Total change`, `Final estate: Farm 15 · Storage 180 · River secured`, `Run record: Cash low · Peak grain`, `Rivals`, `[Play again]`, `seed · rules`.
- **R11 typography:** stacks + sizes above, no webfonts.
- **R12 footer:** `seed playtest-1 · rules 1.0`.

---

## Work Plan

Ordered; each is a commit-sized unit. Do not start n+1 until n's validation green.

**W0 — Branch + verify baseline**

- Confirm `section/11-mobile-react-playable` from `origin/main` at `dc4c05e` (DECISIONS 024, 150 tests). `git pull --ff-only`. Confirm `frontend/` empty is intentional, backend `make test` 150 green, `make lint/type/format-check` green.

**W1 — Scaffold Vite + TS + Query + proxy + tokens (R11, R3, B3, S1)**

- `npm create vite@latest frontend -- --template react-ts` (or scaffold manually), `npm i @tanstack/react-query`, `vitest`, `jsdom`, `@testing-library/react`, `playwright`, `eslint` flat config, `prettier`. `vite.config.ts` proxy `/api → http://localhost:8000` + `VITE_API_URL` fallback `/api/v1`, `tsconfig` strict, `vitest.config.ts` `environment: jsdom`, `playwright.config.ts` two projects + `webServer` waiting on url, `eslint.config.js` with `no-restricted-syntax` bans (`/1000` outside `format.ts`, `waitForTimeout`). Tokens `tokens.css` with `--market-home/--market-river` identity + atmosphere + font stacks (R11) + `data-pressure` per K3 + `tabular-nums`. `package.json` `engines.node>=22`, pinned `vite ^8.2`, committed `package-lock.json`, `npx playwright install --with-deps chromium` note.
- Validate: `npm run typecheck` (tsc --noEmit), `npm run lint`, `npm run test` (no tests yet), `npm run dev` serves `Begin` placeholder.

**W2 — API client + Query layer + `format.ts` boundary (B4, B7, K2)**

- `src/api/client.ts` (`createGame`, `getGame`, `commitChoice` with `expected_revision: game.revision`), `src/api/queries.ts` (keys, mutations with `isPending` + `committingRef` guard B8), `src/api/types.ts` (minimal `GameView` typing from `schemas.py`), `src/lib/format.ts` + `src/__tests__/format.test.ts` including `/1000`+`/10000` grep and `impact_bps` magnitude check (B7).
- Validate: `npm run test` green; grep assertion fails if `current_price/1000` outside `format.ts`; synthetic `turn 2 revision 7` sends `7`.

**W3 — Layout shell + HeaderBar + WorldBand + MarketPulse/RouteLine + RivalsStrip (R2, R3, R4, R9, B5)**

- `StartScreen` (R8/R9), `HeaderBar` (R9 `Age of Grain · Chapter I` + pips `Turn n of 5` + cash `format.money`), `WorldBand` (serif signal 22px, `data-testid="world-band"`), `MarketPulse` pair side-by-side with `MarketCard` (price large + Availability + Demand per R2) + `RouteLine` (R4 "Current route spread …" quote, river identity, dashed when `!established`, `format.signedPricePerUnit(next_margin)`), `RivalsStrip` (B5: `rival_headlines === null` → "Mira and Daran act after your first decision", else headlines; `data-testid="rivals-strip"`).
- Validate: render measured turn-0 `GameView`; no economy calc; rival empty state visible; `world-band` shows top-level `signal`.

**W4 — Decision surface (B1, B4, B6, B8, R1)**

- `DecisionBlock` grouping by `kind` verbatim quantities, `VerbCard` (`label` authoritative, `cost !== null` check for `0`), `QuantityToggle` (options = `ChoiceView.quantity` values verbatim, payload order), `Commit` (`disabled={!selectedId || isPending}`, `committingRef` guard, `expected_revision: game.revision`, `data-testid="commit"`), `409` handling branches on `completion_summary !== null` (never parse `detail`), toast "The game moved on".
- Validate: mocked `sell {7,999}` renders both; synthetic revision 7 test; `hold` cost `0` visible; `buy`/`sell`/`ship` quantities match payload order.

**W5 — Empire tableau + OutcomeReveal beat sequence + CompletionSummary (B2, B3, B5, B7, B9, R6, R7, R10)**

- `src/lib/tableau.ts` + `src/__tests__/tableau.test.ts` (positive investing + negative passive + exact DOM per B9, R1 three rows); `EmpireTableau` (R1 no arrows); `OutcomeReveal` (B2 phase `decision|reveal|completion`, B5 source matrix, B3 `displayPressure`, R6 "Home price", R7 from 0, B7 drivers no residual/`impact_money` colour, 7 beats with `data-reveal-state`/`data-reveal-beat`, Skip `data-testid="reveal-skip"`); `CompletionSummary` (R10 hierarchy, `seed · rules` R12).
- Validate: tableau exact before/after around `expand_farm` then `build_granary` (S2); reveal scoped to `outcome-reveal`; drought reveal colours vs header aftermath; fifth reveal not skipped (B2).

**W6 — Playwright critical path + screenshots + console-error guard + desktop smoke (B2, B3, B8, B9, S2)**

- `e2e/critical.spec.ts` (mobile 390×844 full 5-turn flow per S2: `expand_farm` then `build_granary` early, hold/sell through drought, with deferred `page.route` for B8; desktop smoke 1280×800). Four screenshots with exact indices: `first-decision` at `turn 0` (`normal`), `drought-warning` at `turn 2` before commit (`worsening_dry`), `drought-reveal` after committing `turn 3` (`latest_outcome drought` inside reveal, header `aftermath`), `final-summary` at `turn 5` (`is_complete`). Collect `console` error + `pageerror` from navigation start; zero `waitForTimeout` (eslint ban).
- Validate: `npx playwright test` green; screenshots committed; `grep -r waitForTimeout frontend/e2e` 0; single POST under `page.route` defer.

**W7 — Docs + gates + graphify + push (S1)**

- Add `DECISIONS 023` with reframed rationale per §4; update `STATE.md` (file tree, Boundaries, `Normal verification` + `Last known green` with observed `make test/lint/type/format-check` + `make check-all` output including frontend gates); add `make check-all` to `Makefile`; ensure `make test && make lint && make type && make format-check && make check-all` green; `graphify update .`; commit regenerated artifacts; push branch `section/11-mobile-react-playable`.

---

## Validation Plan — AC1–AC8 → named tests — grill + review amended (confound analysis)

Backend gates unchanged; frontend gates added via `make check-all`. Every gate runs before push; `STATE.md` copies **observed** output.

| AC | Named test(s) | Confound that makes naive test pass spuriously | What rules it out |
|---|---|---|---|
| **AC1** 5-turn completion | `e2e/critical.spec.ts › completes 5-turn game on mobile` (real backend via proxy, S2 path) | Mocked walk or only `turn===5` without `completion_summary` | Real `POST /api/v1/games` + 5 real `POST …/choices/{id}` with `expected_revision: game.revision`; asserts `completion_summary.is_complete===true` **and** `turn===turn_limit===5` **and** `available_choices===[]` |
| **AC2** no dense table | `e2e › decision surface has no table` | Global `table.count===0` hides off-screen table | Scoped to `[data-testid="decision-block"] table` + `toBeVisible` cost/quantity inside decision block without `<details>` |
| **AC3** what changed and why | `e2e › reveal shows wealth/inventory/price deltas and ≤3 drivers` (scoped) + `outcomeReveal.test.tsx` verbatim labels | Header numbers mimic reveal; re-ranked drivers coincidentally match | Scoped to `[data-testid="outcome-reveal"] [data-reveal-beat="2/3"]` with `latest_outcome` values; `latest_outcome.world==="drought"` while header `aftermath` cross-check; drivers `impact_money` sign not `impact_bps` (B7) |
| **AC4** rivals visible | `e2e › rivals card always visible, empty state on turn 0` | Hidden on turn 0 or fabricated headline | Turn 0 `rivals-strip` visible + "act after your first decision" + no "Mira:"; turn ≥1 `Mira:`/`Daran:` from real API; completion `final_rival_headlines`; no "Mira" string in frontend code outside tests |
| **AC5** empire visibly changes | `src/__tests__/tableau.test.ts` (positive investing, negative passive) + `e2e › empire exact before/after` (B9) | `not.toEqual` passes with any text change; pure function passes while component stale | Three tests: positive `{5,130,false}→{15,180,false}` reached count +1, negative hold×5 equal, E2E asserts exact `Farm capacity 5` → `Farm capacity 15` and tier "Expanded Estate" unreached→reached around known `expand_farm` commit |
| **AC6** no double-submit | (a) `e2e › commit disabled while in-flight` with `page.route` deferred gate + `requestCount===1` & `disabled` (B8) (b) `commit.test.ts › stale revision rejected [200,409]` | `disabled` after response still double-fires; different revision makes second `200` pass | (a) deferred `/choices/` 300ms, two activations while in flight → exactly one POST, `disabled`/busy; (b) synthetic `turn 2 rev 7` sends `7` (B4); committingRef guard covers same-tick clicks |
| **AC7** zero console errors | `e2e › no console errors` with `console` error + `pageerror` from `goto` start | Only `pageerror` misses `console.error` | Both collected; `expect(errors).toEqual([])` and `expect(pageErrors).toEqual([])` after full flow |
| **AC8** Playwright mobile + desktop smoke + screenshots | `playwright.config.ts` two projects `mobile 390×844` full flow + `desktop 1280×800` smoke; `e2e` four screenshots | Reused viewport, `waitForTimeout` hides flake | Full flow + 4 screenshots on mobile (S2 path `expand` then `granary`), smoke `create + 1 commit + reveal` on desktop; waits on `data-reveal-state="complete"`; `grep -r waitForTimeout` 0 via eslint ban |

**Screenshot assertions (browser verification) — grill+review scoped:**

- `first-decision.png` — `turn 0` `pressure_stage==="normal"`, `Begin` gone, 6 verb cards (B1), `Age of Grain · Chapter I` visible (R9), no reveal.
- `drought-warning.png` — **`turn===2` before commit** `pressure_stage==="worsening_dry"` (`worsening_dry` only `next_world_known==="drought"`), world `normal`, signal "The dry spell persists…" .
- `drought-reveal.png` — **after committing `turn===3`** `latest_outcome.pressure_stage==="drought"`/`world==="drought"`/`title==="Drought"` scoped inside `outcome-reveal` `beat 1` in drought colours (B3 `displayPressure`); `world-band` outside shows `aftermath`/`normal` (proves disagreement).
- `final-summary.png` — `turn===5` `completion_summary.is_complete===true`, R10 hierarchy (hero wealth, total change, estate, run record, rivals, `seed · rules`), `[Play again]`.

**Grep / contract assertions:**

- `format.test.ts › no inline price/bps division outside format.ts` — `/\s*1000`+`/\s*10000\b` outside `format.ts` (K2)
- `tableau.test.ts › does not read market prices` — args only `empire_summary` fields
- `decisionBlock.test.tsx › hold cost 0 shown (cost !== null), sell cost null hidden (B6)`
- `decisionBlock.test.tsx › quantities verbatim {7,999} (B1)`
- `commit.test.ts › synthetic turn 2 revision 7 sends 7 (B4)`
- `commit.test.ts › committingRef prevents same-tick double (B8)`

**Gate commands (explicit) — S1:**

```bash
# backend (existing)
make test && make lint && make type && make format-check
# frontend
cd frontend && npm run typecheck   # tsc --noEmit
cd frontend && npm run lint        # eslint flat + prettier --check
cd frontend && npm run test        # vitest run
npx playwright test                 # e2e mobile + desktop (via make front-e2e)
# all
make check-all                      # backend + frontend (required before push, per ORCHESTRATION §4 + review S1)
```

---

## Risks / Rollback — grill+review amended

| risk | likelihood | impact | mitigation |
|---|---|---|---|
| **Proxy misconfig → CORS/404** | medium | blocks all | `vite.config.ts` proxy + `VITE_API_URL` fallback; `webServer.url` wait; e2e `response.ok` |
| **`rival_headlines null` crash/hidden** | medium | AC4 | `=== null` empty state; B5 source matrix; visible every turn |
| **Turn off-by-one → "Turn 6 of 5"** | medium | spec | `turn+1 of turn_limit`, `resolved_turn+1`, `completion_summary !== null` |
| **B2 fifth reveal skipped** | high | silent, every AC still green | Phase machine `decision|reveal|completion`; `latest_outcome` + `completion_summary` both present — reveal before completion |
| **B3 drought reveal in aftermath colours** | high | most important beat wrong | `displayPressure` phase-selected; E2E proves header `aftermath` vs reveal `drought` |
| **B4 revision vs turn invisible** | high | passes happy path | Always `game.revision`; synthetic `turn 2 rev 7` test |
| **Crossing `latest_outcome` vs top-level** | medium | AC3 | Source matrix (B5) + `aftermath` vs `drought` cross-check |
| **B7 residual / bps magnitude** | medium | misleading "100%" bar | No stacked bar; labels + `impact_money`; colour from `impact_money` not `impact_bps` |
| **AC5/AC6 tautological** | high | false green | B9 exact before/after; B8 deferred route + committingRef + `[200,409]` |
| **B6 cost 0 vanishes / proceeds invented** | medium | hold vanishes, sell invents | `cost !== null` check; `label` authoritative; no proceeds calc |
| **Scaffolding drift** | medium | build fails | Pinned vite/eslint/jsdom/playwright, `package-lock.json`, `playwright install` |
| **Choice-count 9 overflow** | low | layout | 6 cards stacked, second quantity inside card (B1) |
| **409 misclassify** | medium | wrong toast / retry | Branch on `completion_summary !== null`, not `detail` string |
| **Playwright `waitForTimeout` flake** | high | AC8 | eslint ban + `data-reveal-state` waits; `grep -r waitForTimeout` 0 |
| **`format.ts` leakage** | medium | 5000 raw | `/1000`+`/10000` grep + snapshot `5.000` |
| **Desktop layout creep** | low | delay | `max-width:480px` centred, same tree |
| **State drift** | medium | handoff | `STATE.md` observed output in same commit (§15) |

**Rollback:** Frontend additive (`frontend/` + proxy), no backend change. Revert `git revert <W1..W6>` or branch delete. Proxy fallback `VITE_API_URL=https://<backend>` with `CORSMiddleware` only via escalation.

---

## Open Questions

- **None that block planning.** Decisions below are adopted per review; owner reversal would be new review.

- **Q1 — literal "2–4 buttons":** Deviation adopted per `DECISIONS 023` (reframed per §4) — grouping + verb cards + Commit protects small legible surface vs hard count against frozen API. Not `DECISIONS` overriding `BUILD_SPEC` (BUILD_SPEC §0.2).
- **Q2 — desktop dashboard:** Single centred 480px, not two-column (R2/R10 hierarchy satisfies legibility without dashboard).
- **Q3 — `next_margin` semantics:** Quote copy fix sufficient (R4) — no backend rename; residual/dashboard not added.

---

## Non-goals reminder

Do not build: auth, Postgres, LLM, `render.yaml`/`alembic`, content DSL, history endpoint, bottom nav, second age, free-text commands, `BUILD_SPEC §31`.

---

## Appendix — Measured payload excerpts

Turn 0 `GameView` (abbrev):

```json
{
  "run_seed": "playtest-1", "revision": 0, "turn": 0, "turn_limit": 5,
  "signal": "The growing settlement keeps food demand high.", "pressure_stage": "normal", "world": "normal",
  "player_summary": {"cash": 1000, "inventory_grain": 20, "farm_capacity": 5, "storage_capacity": 130, "wealth": 1100},
  "empire_summary": {"farm_capacity": 5, "storage_capacity": 130, "route_established": false},
  "home_valley_market": {"supply": 280, "demand": 410, "base_price": 5000, "current_price": 5000, "responsiveness": 4000},
  "river_town_market": {"supply": 80, "demand": 130, "base_price": 5200, "current_price": 5200, "responsiveness": 5000},
  "route_status": {"established": false, "capacity": 20, "transport_cost_per_unit": 300, "reliability_bps": 10000, "next_margin": -100},
  "rival_headlines": null,
  "available_choices": [
    {"id": "hold", "kind": "hold", "cost": 0},
    {"id": "expand_farm", "kind": "expand_farm", "cost": 500},
    {"id": "build_granary", "kind": "build_granary", "cost": 300},
    {"id": "secure_route", "kind": "secure_route", "cost": 400},
    {"id": "buy_grain:55", "kind": "buy_grain", "quantity": 55, "cost": 275},
    {"id": "buy_grain:110", "kind": "buy_grain", "quantity": 110, "cost": 550},
    {"id": "sell_grain:10", "kind": "sell_grain", "quantity": 10},
    {"id": "sell_grain:20", "kind": "sell_grain", "quantity": 20}
  ],
  "latest_outcome": null, "completion_summary": null
}
```

After `expand_farm` (turn 1): `farm 15`, `storage 130`, `route false`, `cash 500`, `inventory 130`, `home 5157`, `river 6240`, `next_margin 783` (quote per R4), `rival_headlines` populated, `latest_outcome {resolved_turn:0, title:"A Growing Settlement", pressure_stage:"normal", world:"normal", wealth_delta:70, inventory_delta:110, price_delta:157}`. Sell now uncapped: at inventory 170 offers `85/170` (not `75/150`).

---

## Grill — Decision-Forcing Questions, Answers, and Consequences (retained per §1)

Headless grill per `ORCHESTRATION.md` §2; changes from grill are marked **grill-amended** elsewhere and remain settled.

See previous revision for Q1–Q7; review round 1 §1 confirms them. Overall grill verdict: four material inaccuracies corrected (choice max 8→9, grep `/100`→`/1000`+`/10000`, AC5/AC6 falsifiability, drought indices). All retained.

---

## Review Round 1 — What Changed (2026-08-10)

Nine blocking (B1–B9) and twelve rulings (R1–R12) applied; `DECISIONS 023` reframed per `BUILD_SPEC §0.2`; S1 `make check-all`, S2 two-milestone e2e path. Design direction banner now says partially superseded — this plan is authority where they disagree. No backend change; `DECISIONS 024` sell uncapped respected.

---

*Plan revised after grill + consolidated review round 1 — no implementation code written. Awaiting Approve / Request changes.*
