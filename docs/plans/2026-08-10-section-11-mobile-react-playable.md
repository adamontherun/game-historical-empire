# Section 11 — Mobile-First React Playable — Plan

**Date:** 2026-08-10
**Branch:** `section/11-mobile-react-playable` (from `origin/main` at Section 10 COMPLETE — `STATE.md` 149 tests green)
**Spec Authority:** `BUILD_SPEC.md` Section 11 (line 1345, Status NOT STARTED) + global §§6–11 + `AGENTS.md` + `frontend/AGENTS.md`
**Design Authority:** `docs/plans/2026-08-10-section-11-design-direction.md` (Claude, per `docs/ORCHESTRATION.md` §5) — binding input derived from measured `GameView` payload (`run_seed="playtest-1"`). Where this plan quotes numbers, they are measured, not assumed; regeneration command is in §Context.
**Related:** `backend/app/api/schemas.py` (`GameView`, `ChoiceView`, `OutcomeView`, `CompletionSummaryView`, `MarketView`, `RouteStatus`), `backend/app/api/mappers.py` (`choices_for`, `actor.ship_margin`), `backend/app/engine/prototype.py` (`TURN_LIMIT=5`, `default_start_state`), `backend/app/engine/pressure.py` (`PRESSURE_ARC` 5 stages), `backend/app/domain/trace.py`, `DECISIONS.md` 017/019/020/022, `STATE.md` Boundaries, `BUILD_SPEC §31` (no building ahead)

---

## Goal

Ship the first browser-playable vertical slice: a phone-excellent (390×844) single-column React app that lets a new player **start → read signal → inspect markets/rivals/route → choose one major action → commit → see time advance → see outcome reveal → understand why → continue** for exactly 5 turns, consuming `GameView` truthfully, with zero economy recomputation in the frontend, and passing `BUILD_SPEC §11` AC1–AC8 plus Playwright critical path with four screenshots and zero console errors.

---

## Success Criteria (maps to AC1–AC8 + gates)

Each AC has a falsifiable rule in Validation; summary:

1. **AC1 — 5-turn completion on phone.** Mobile viewport 390×844: new player can `POST /api/v1/games` → 5 × `POST …/choices/{id} {expected_revision}` → `completion_summary.is_complete === true` with no dead-end or missing choice.
2. **AC2 — No dense table required.** Decision surface is verb cards + quantity + commit; choosing never requires opening a detail table. Assertion: no `<table>` in decision surface; all required info (cost, consequence, margin sign) visible on main screen.
3. **AC3 — Every result says what changed and why.** After each commit, reveal shows `wealth_delta`, `inventory_delta`, `price_delta` with sign-colour, ≤3 verbatim `drivers`, and collapsed `causal_trace` proof. Fails if drivers re-ranked or recomputed.
4. **AC4 — Rivals visible throughout.** Persistent rivals card rendered every turn; turn 0 shows explicit empty state, turns ≥1 show `mira`/`daran` headlines and completion shows `final_rival_headlines`. Fails if card hidden or headline fabricated.
5. **AC5 — Empire visibly changes.** `tableau()` pure function maps the three real fields to named tiers; measured 5-turn capture proves label set changes. Fails if tier labels identical at turn 0 and turn 5. See Falsifiable rule below.
6. **AC6 — No double-submit.** Commit disabled while in-flight **and** server `expected_revision` rejects stale retry. Fails if two rapid taps produce two `200`s or two state mutations. See Falsifiable rule below.
7. **AC7 — Zero console errors on critical path.** Playwright collects `console` error events; any error fails.
8. **AC8 — Playwright 5-turn mobile + desktop smoke.** One spec file covers mobile full flow (with 4 screenshots) and desktop smoke; both green.

**Gates remain green:** `make test` (149 backend), `make lint`, `make type`, `make format-check` plus new frontend gates (`npm run typecheck`, `npm run lint`, `npm run test`) — see §Validation.

---

## Context And Current Facts

- **`frontend/` empty.** Only `.gitkeep` + `AGENTS.md`. This section scaffolds Vite + React + TypeScript + TanStack Query from scratch. No backend change — dev/test hit API via Vite proxy.
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
  | `ChoiceView.cost` (hold 0, expand 500, granary 300, route 400, buy 275 for 55) | `Money` | whole coins |
  | `home_valley_market.current_price` | `5000` | `PriceMilliunits` (→ 5.000) |
  | `river_town_market.current_price` | `5200` | milliunits |
  | `route_status.transport_cost_per_unit` | `300` | milliunits (→ 0.300) |
  | `route_status.next_margin` | `-100` | milliunits (→ -0.100; after `expand_farm` becomes `783` = +0.783) |
  | `home_valley_market.responsiveness` | `4000` | bps (40%) |
  | `OutcomeView.price_delta` | e.g. `157` | milliunits (+0.157) |
  | `OutcomeView.wealth_delta`, `impact_money` | e.g. `-500`, `550` | `Money` |

  After one `expand_farm`: `farm 5→15`, `storage 130`, `route false`, `cash 500`, `inventory 130` (capped), `home price 5157`, `river 6240`, `supply 380`, `choices` collapse from 8 to 6 (no buy when cash low + inventory full). `pressure_stage` sequence: `normal → early_dry → worsening_dry → drought → aftermath`; `world` only `drought` at idx 3 (`PRESSURE_ARC`).

- **Traps measured (design direction §0, re-measured in grill):**
  - `rival_headlines === null` at turn 0 only; thereafter 2 strings; `completion_summary.final_rival_headlines` at end.
  - `turn` is 0-based upcoming decision; `turn+1 of turn_limit` for display; `resolved_turn` 0-based for reveal; completion is `completion_summary !== null` (never `turn===turn_limit`).
  - **Choice count re-measured:** turn 0 is **8** choices (6 distinct `kind`s: `hold, expand_farm, build_granary, secure_route, buy_grain×2, sell_grain×2`). After `secure_route` (cash 600, inv 70, route true) it is **9** choices (`hold, expand_farm, build_granary, buy_grain×2, sell_grain×2, ship_grain×2`) — the true maximum is **9**, not 8. Distinct verbs max **6** (`hold|expand_farm|build_granary|buy_grain|sell_grain|ship_grain`; `secure_route` disappears after establishment, so never 7 together). Cards must hold 6 verb cards (see K4). Spec's "2–4 buttons" conflicts with `DECISIONS 017` — cannot both be literal.
  - `latest_outcome.world/pressure_stage` is resolved turn; top-level `world/pressure_stage/signal` is next decision. Crossing them describes wrong weather — verified: at `turn=4` top is `aftermath/normal` while `latest_outcome` is `drought/drought`.
  - `empire_summary` exactly 3 fields `{farm_capacity, storage_capacity, route_established}`; `OperationState` dormant per `types.py:59`.
  - `river_town_market` and `home_valley_market` each have `supply/demand/base_price/current_price/responsiveness`; route has `established/capacity/transport_cost_per_unit/reliability_bps/next_margin`.

- **Existing gates:** `Makefile` `make test` (`uv run --project backend pytest -v`), `lint` (`ruff check`), `type` (`cd backend && uv run pyright` strict app + standard tests, 38 files), `format-check`. All green (149 passed). No `render.yaml` change this section.

---

## Constraints And Non-goals

**Must satisfy:**

- No backend edits. `frontend/` talks via Vite proxy `/api → http://localhost:8000`; `VITE_API_URL` defaults to `/api/v1` per `frontend/AGENTS.md`. If a schema shape change looks unavoidable, escalate — don't edit `backend/`.
- `GameView` is presentation — no frontend recompute of cost/margin/wealth/affordability/capacity. Use `ChoiceView.cost`, `route_status.next_margin`, `player_summary.wealth`.
- `expected_revision` on every commit; `409` handling non-destructive.
- `DECISIONS 017` principle honoured — every legal choice remains reachable; economic bad moves remain choosable.
- Desktop is centered single column, not a second layout / dashboard.

**Out of scope — do NOT build (`BUILD_SPEC §31`, design direction §8):**

- Auth, DB/Postgres, LLM/advisor, real art pipeline, history/replay screen, bottom-nav architecture, multiple age screens, free-text commands, sound, i18n, animation libraries beyond reveal beats, two-column desktop dashboard.

---

## Key Decisions

### K1 — Vite + React + TypeScript + TanStack Query, proxy-only backend reach

- **Decision:** Scaffold with `npm create vite@latest` (react-ts), add `tanstack/react-query`, `react-router` not needed — single game route with local state. Vite `server.proxy` `{ "/api": "http://localhost:8000" }` for dev and Playwright. `VITE_API_URL` env read with fallback `/api/v1`. No CORS addition.
- **Rejected:** Next.js/SSR, Redux/Zustand (overkill; server state is just `GameView`), direct `fetch` without Query (loses cache/invalidation/isPending).
- **Evidence:** `frontend/AGENTS.md` stack; `backend/app/main.py` mounts `/api/v1`; no CORS today.

### K2 — Unit-conversion boundary is `format.ts` only

- **Decision:** Single module `src/lib/format.ts` exporting `money(n: Money): string`, `pricePerUnit(milli: PriceMilliunits): string`, `signedMoney`, `signedPricePerUnit`, `percent(bps)`. Every other file imports from it. No inline `/1000` or `/100`. Test file asserts grep finds no ` / 1000` outside `format.ts`.
- **Thresholds:** `money` renders `1000 → "1,000"` (coins), `pricePerUnit(5000) → "5.000"`, `signedPricePerUnit(-100) → "−0.100"`. `percent(4000) → "40%"`.
- **Falsifiability:** if `current_price` rendered as `5000`, test fails.

### K3 — Pressure drives theming via single `data-pressure` source

- **Decision:** Root `<div data-pressure={game.pressure_stage}>` with CSS custom properties for `--parchment`, `--ink`, `--grain`, `--river`, `--drought`, `--gain`, `--rule`. Stages `normal|early_dry|worsening_dry|drought|aftermath` each set a block of variables (parchment warms/desaturates toward bone, grain bleaches, faint vignette; `aftermath` cools but not back to `normal`). No per-component `if (stage)`. `prefers-reduced-motion` in CSS.
- **Rejected:** JS colour maths per component.

### K4 — Decision surface: verb cards + quantity + explicit commit — documented deviation

- **Decision:** Group `ChoiceView`s by `kind`. One verb card per distinct `kind` (typically 5–6, max 7). Verbs with two quantities (`buy_grain`, `sell_grain`, `ship_grain`) render one card with a two-option segmented control (`55 | 110`), not two cards. 8 choices → 5 cards at start. Each card shows label, `cost`/proceeds, one-line consequence. Selection is local state; single **Commit** button submits `{ expected_revision }`. Disable semantics cover AC6.
- **Conflict:** `BUILD_SPEC §11` "2–4 action buttons" vs `DECISIONS 017` "do not hide any legal choice" (measured 6–8). Ruling: honour 017; deviation recorded in `DECISIONS.md` (text below). Intent preserved (no dense table of micro-ops; verb cards + commit keep one major action).

**`DECISIONS.md` entry text (to be added verbatim on implementation):**

> ### 023 — Section 11 Decision Surface — Verb Cards With Quantity + Explicit Commit (2026-08-10)
> - **Context:** `BUILD_SPEC §11` requires "2–4 action buttons" while `backend/app/api/mappers.py:choices_for` returns 6–8 `ChoiceView`s (5–7 verbs × 2 quantities for `buy_grain:55/110`, `sell_grain`, `ship_grain`) and `DECISIONS 017` clause 1 forbids hiding any legal choice. Both cannot be satisfied literally.
> - **Decision:** Group `ChoiceView` by `kind` into one verb card per distinct `kind` (typically 5–6, max 7). Verbs with two quantities render a single card with a two-option segmented control, not two cards, so 8 choices collapse to ~5 cards without removing any legal move. A single explicit Commit button submits the selected `choice_id` with `expected_revision`; the commit control is disabled while the mutation is in-flight and the server's `expected_revision` remains the truth for `409` handling (`DECISIONS 021`). Never compute cost/margin/affordability client-side.
> - **Rationale:** The "2–4" line protects against a dense table of micro-operations, which verb cards + commit satisfy, while `DECISIONS 017`'s principle — "the player remains free to make economically bad, contrarian, or anticipatory decisions" — is load-bearing for the game's anticipatory thesis. Hiding moves would silently violate that principle and would also re-introduce the `DECISIONS 022` error (harness `80` cap).
> - **Consequence:** The UI exposes every `available_choices` entry without duplication; presentation grouping is not authorization. AC2 satisfied without tables; AC6 guarded at both UX and revision layers.

### K5 — Outcome reveal is a staged sequence, not a panel

- **Decision:** Beats in order, reading from `latest_outcome.*` (never top-level), handing off to top-level `signal` for next threat. Each beat is a DOM element with `data-reveal-beat="k"`; container exposes `data-reveal-state="complete"` at end, `data-reveal-state="revealing"` during, and `data-reveal-state="idle"` before. Skip/reveal-all button sets state to `complete` instantly (still in order, still complete, respects `prefers-reduced-motion`).

### K6 — `tableau()` pure function

- **Decision:** `src/lib/tableau.ts` pure `tableau(empire: EmpireSummary) -> Tier[]` with thresholds justified from measured `default_start_state` (`farm 5`, `+10` per `expand_farm`, `storage 130 +50`, `route established false→true`). Four tiers matching spec example, each reachable within 5 turns, tested that label set changes across measured capture.

### K7 — Frontend gates and Makefile integration

- **Decision:** Frontend scripts: `typecheck` (`tsc --noEmit`), `lint` (`eslint` + `prettier --check` or `ruff`-equivalent for TS), `test` (`vitest run`), `e2e` (`playwright test`). Makefile adds `front-type`, `front-lint`, `front-test` that `cd frontend && npm run ...`. `make type` remains backend pyright; `make lint`/`format-check` remain backend; frontend gates run separately until CI joins them. Plan states this explicitly so gate drift is visible.

---

## Recommended Approach

### File layout for `frontend/` (scaffolded from scratch)

```
frontend/
  index.html
  vite.config.ts              # proxy /api → 8000, VITE_API_URL fallback
  tsconfig.json               # strict
  package.json                # vite, react, @tanstack/react-query, vitest, playwright, eslint, prettier
  public/
  src/
    main.tsx                  # createRoot + QueryClientProvider
    App.tsx                   # game state machine: idle → playing → revealing → complete
    api/
      client.ts               # fetch wrappers: createGame, getGame, commitChoice (expected_revision)
      queries.ts              # TanStack Query keys + mutations (useGame, useCommit), revision-aware invalidation
      types.ts                # re-exported GameView shapes (generated or hand-typed from schemas.py, kept minimal)
    lib/
      format.ts               # money/pricePerUnit/percent — ONLY place with /1000 and /100
      tableau.ts              # tableau(empire) -> Tier[]
      pressure.ts             # pressureStages type + css helper (optional, mostly data-pressure)
    components/
      HeaderBar.tsx           # age/chapter · Turn pips · cash (via format.money)
      WorldBand.tsx           # display-serif signal, pressure-tinted via CSS inheritance
      EmpireTableau.tsx       # vertical chain 4 tiers, ghosted vs reached
      MarketPulse.tsx         # Home/River pair side-by-side + route connector
      MarketCard.tsx          # supply/demand/price (price via format.pricePerUnit)
      RouteLine.tsx           # river-coloured connector, dashed when !established, label with format.signedPricePerUnit(next_margin)
      RivalsStrip.tsx         # empty state at turn 0, headlines thereafter, serif
      DecisionBlock.tsx       # verb cards grouping + quantity segmented control + Commit
      VerbCard.tsx
      QuantityToggle.tsx
      OutcomeReveal.tsx       # staged beats, Skip, data-reveal-state
      CompletionSummary.tsx   # final wealth/cash/grain/farm/storage + rival headlines
      FooterDebug.tsx         # run_seed, revision, turn
    styles/
      tokens.css              # --ink/--parchment/--grain/--river/--drought/--gain + [data-pressure] overrides
      app.css                 # layout: single column max-width 480 centred, cards, typography, motion
    __tests__/
      format.test.ts
      tableau.test.ts
      outcomeReveal.test.tsx  (optional, but recommended)
  e2e/
    critical.spec.ts          # mobile + desktop
  playwright.config.ts
  eslint.config.js
  vitest.config.ts
```

**Component tree (render order on Decision screen):**

```
App
 ├─ HeaderBar            (sticky, pips Turn n/5, cash)
 ├─ WorldBand            (signal, serif, pressure CSS)
 ├─ EmpireTableau        (4-tier chain)
 ├─ MarketPulse
 │   ├─ MarketCard (Home Valley — grain)
 │   ├─ RouteLine (next_margin, established?)
 │   └─ MarketCard (River Town — river)
 ├─ RivalsStrip          (Mira/Daran or empty state)
 ├─ DecisionBlock
 │   ├─ VerbCard × (hold|expand_farm|build_granary|secure_route|buy_grain|sell_grain|ship_grain)
 │   │   └─ QuantityToggle (when verb has 2 quantities)
 │   └─ CommitButton     (disabled when !selected || isPending, data-testid="commit")
 ├─ OutcomeReveal        (overlay/modal or inline section, data-reveal-state, beats, Skip)
 ├─ CompletionSummary    (when is_complete)
 └─ FooterDebug          (run_seed)
```

Desktop: same tree, `max-width: 480px` centred on wider parchment ground via `tokens.css`; no second layout.

### Exact unit-conversion boundary (`format.ts`)

```ts
// src/lib/format.ts — ONLY file allowed to divide by 1000 or 100 (for bps/price)
export function money(n: number): string          // 1000 → "1,000"  (NBSP-free, en-US)
export function signedMoney(n: number): string    // -500 → "−500" (U+2212 minus)
export function pricePerUnit(milli: number): string       // 5000 → "5.000"
export function signedPricePerUnit(milli: number): string // -100 → "−0.100", 157 → "+0.157"
export function percent(bps: number): string      // 4000 → "40%"
```

All other files must import these. Grill finding: a naive `/\s*100` grep false-alarms on legitimate `width / 100 * pct`, `Date.now()/1000`, `opacity` maths. The contract is narrower: **no raw price/money arithmetic outside `format.ts`**, not "no division by 100 anywhere". Two enforcement layers:

1. **Vitest grep assertion (falsifiable):** scan `src/` excluding `format.ts` for `/\s*1000` (price milliunits) **and** for `/\s*10000\b` (bps denominator) — not bare `/100`. Proved effective: backend scan found 40 hits, all in engine/tests, none needed in frontend. Test:

```ts
// format.test.ts — fires if price is rendered raw
test('no inline price/bps division outside format.ts', async () => {
  const hits = await grepOutside('src', 'format.ts', /\/\s*1000|\/\s*10000\b/);
  expect(hits, `raw price/bps maths outside format.ts: ${hits.join('; ')}`).toEqual([]);
});
```

   This would fail if any component did `current_price / 1000` or `responsiveness / 100`.

2. **ESLint rule (belt-and-braces):** `no-restricted-syntax` forbidding `BinaryExpression[operator="/"][right.value=1000]` outside `format.ts` (checked in code review; not a hard build break if regex covers it).

Tests for correctness (vitest, strict):

- `money(1000) === "1,000"`, `money(0) === "0"`
- `pricePerUnit(5000) === "5.000"`, `pricePerUnit(5200) === "5.200"`, `pricePerUnit(300) === "0.300"`
- `signedPricePerUnit(-100) === "−0.100"`, `signedPricePerUnit(157) === "+0.157"`, `pricePerUnit` never shows `5000` — regression would render `5000` and test fails
- `percent(4000) === "40%"`, `percent(10000) === "100%"`
- `signedMoney(-500) === "−500"`; `money` round-trips through `Intl.NumberFormat`

### Pressure theming — single source

- `App.tsx` (or top layout) renders `<div data-pressure={game.pressure_stage}>` where `pressure_stage ∈ {normal, early_dry, worsening_dry, drought, aftermath}` (typed from `schemas.py`).
- `tokens.css`:

```css
:root { --parchment:#F5EDE0; --parchment-hi:#FFFAF1; --ink:#1F1A14; --grain:#C8912F; --river:#2F7B78; --drought:#A6412B; --gain:#4A7C43; --rule:#DCCFBA; }
[data-pressure="normal"]       { --parchment:#F5EDE0; }
[data-pressure="early_dry"]    { --parchment:#F0E6D3; --grain:#C59A3E; }
[data-pressure="worsening_dry"]{ --parchment:#E8DDC8; --grain:#BC9B55; }
[data-pressure="drought"]      { --parchment:#E0D5BE; --ink:#2A1F14; filter: saturate(0.9); }
[data-pressure="aftermath"]    { --parchment:#EDE8DC; --grain:#B8964A; }
@media (prefers-reduced-motion: reduce) { * { transition:none !important; animation:none !important; } }
```

No per-component `if (pressure_stage === "drought")` colour branches.

### Decision surface (see K4 + DECISIONS 023) — **grill-amended: max is 9 choices / 6 cards**

- `DecisionBlock` receives `available_choices: ChoiceView[]`. Groups by `kind` — **measured maxima: 9 choices collapse to 6 cards** (the plan's earlier "8→5" was low by one; re-measured after `secure_route` is 9 choices: `hold, expand_farm, build_granary, buy×2, sell×2, ship×2`; `secure_route` disappears, so never 7 kinds together):

```
hold          → 1 card (no quantity)
expand_farm   → 1 card (cost)         — hidden when cash<500
build_granary → 1 card (cost)         — hidden when cash<300
secure_route  → 1 card (cost)         — hidden when established or cash<400
buy_grain     → 1 card with QuantityToggle {min//2, min} e.g. {55,110} at start, {30,60} after route when headroom smaller
sell_grain    → 1 card with QuantityToggle {n//2, n} with n=min(inventory,150)
ship_grain    → 1 card with QuantityToggle {cap//2, cap} e.g. {10,20} (only when route established & inventory>0)
```

- Card layout must comfortably hold **6 verb cards** at 390px (stacked vertically; each card ~56px + 8px gap → ~400px total, scrollable within single column). The extra 9th choice does not create a 7th card — it is the second quantity inside the same verb card.
- Selection: clicking a verb card selects it; if it has quantities, default to the larger (full commit) but allow toggle. Selected card gets `data-selected="true"`.
- Commit button: `Commit — <verb label> <quantity?>` + cost via `format.money(cost)` when present; `disabled={!selectedId || commit.isPending}`; `data-testid="commit"`. On click, calls `commitMutation.mutate({ choice_id: selectedId, expected_revision: game.revision })`. Double-click guard is both `disabled` and the `isPending` state.
- **409 handling (grill-verified, no string parsing):** backend returns `409` in two cases, both with `409` but distinguishable without parsing `detail`:
  - stale revision → `409 {"detail":"conflict: expected_revision X != current Y"}` — refetch `GET /api/v1/games/{id}`, show toast "The game moved on — your view was stale", re-enable commit with new `revision`.
  - already complete (even with current `expected_revision`) → `409 {"detail":"game complete"}` — do **not** refetch as conflict; instead transition to `CompletionSummary` (which is already reachable via `completion_summary`). A stale rev on a complete game also returns conflict, not "game complete" — the revision check fires first, so client must check `game.completion_summary !== null` before classifying the 409. Handle by **status code + local state**, not by `detail.includes("complete")`:

### Outcome-reveal beat sequence + test hooks — **grill-amended with measured indices**

Beats consume `latest_outcome.*`; hand-off consumes top-level `signal`/`pressure_stage`. Measured `PRESSURE_ARC` with `hold` path:

| turn idx | before `pressure_stage` | after `pressure_stage` | after `latest_outcome` |
|---|---|---|---|
| 0 | `normal` "The growing settlement…" | `early_dry` | `normal` / "A Growing Settlement" |
| 1 | `early_dry` "Grain remains abundant…" | `worsening_dry` | `early_dry` / "Surplus" |
| 2 **warning decision** | `worsening_dry` "The dry spell persists…" | `drought` | `worsening_dry` / "Warning Signs" |
| 3 **drought commit** | `drought` "Drought cuts farm output…" | `aftermath` | `drought` / "Drought" ← **drought reveal** |
| 4 | `aftermath` "Markets adjust…" | `aftermath` | `aftermath` / "Aftermath" |

So:
- **Drought warning screenshot = `turn===2` before commit** (`pressure_stage==="worsening_dry"`, `signal` contains "dry spell persists").
- **Drought outcome reveal screenshot = after committing at `turn===3`**, reading `latest_outcome.pressure_stage==="drought"` / `world==="drought"` / `title==="Drought"` while the **header/world band** outside the reveal already shows `aftermath/normal` — they deliberately disagree per `DECISIONS 017` clause 5. A screenshot assertion that only checks the page header would prove nothing about the reveal; it must scope to the reveal container.

| beat | `data-reveal-beat` | reads | note |
|---|---|---|---|
| 0 time | `0` | `resolved_turn +1`, `title` (serif) | `Turn {resolved_turn+1}` inside reveal — not `turn+1` |
| 1 world | `1` | `latest_outcome.world/pressure_stage` | `data-pressure` on this beat when `drought` — highlight. Must compare to `latest_outcome`, not top-level. |
| 2 numbers | `2` | `wealth_delta`, `inventory_delta`, `price_delta` | `format.signedMoney/signedPricePerUnit`, tabular-nums, +green/−red |
| 3 drivers | `3` | `drivers[0..2]` verbatim label + `impact_money` | do not re-rank; test asserts `driver.label` equals engine label |
| 4 why | `4` | `causal_trace.nodes` (~40 nodes) | collapsed `<details>` "Show the full chain" closed by default; nodes ~40, edges derived |
| 5 rivals | `5` | rival headlines for that `resolved_turn` (derived from `rival_headlines` at next `turn` or stored `RivalTurnResult`) | what Mira/Daran did |
| 6 next threat | `6` | top-level `signal` / `pressure_stage` | hand-off to next decision — this is the only beat reading top-level |

Container: `data-reveal-state="idle" | "revealing" | "complete"` on `data-testid="outcome-reveal"`. Sequence advances via `requestAnimationFrame` + `setTimeout(300)` per beat; `prefers-reduced-motion` collapses to `complete` instantly (still ordered, still complete). Playwright waits on `locator('[data-testid="outcome-reveal"][data-reveal-state="complete"]')` — never `waitForTimeout`.

Skip: button `data-testid="reveal-skip"` sets state to `complete`.

**Screenshot scoping (prevents header/reveal cross-contamination):**

```ts
// drought-reveal must assert INSIDE reveal, not header
await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="1"]'))
  .toContainText(/drought/i);
await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="1"]'))
  .toContainText('Drought');
await expect(page.locator('[data-testid="world-band"]'))
  .toContainText(/aftermath/i); // proves they disagree, per spec
```

### `tableau()` pure function + thresholds justified from measured ranges — **grill-amended**

Measured start: `farm 5`, `storage 130`, `route false`. Constants: `EXPAND_FARM_COST 500 → +10`, `BUILD_GRANARY_COST 300 → +50`, `ROUTE_ESTABLISH_COST 400`. Walk observed: T0 `expand_farm` → farm 15; storage stays 130 until `build_granary`; route flips on `secure_route`; inventory measured 20→130→capped. **Grill re-measurement:** 5×`hold` across 5 seeds leaves `empire {5,130,false}` unchanged — inventory still rises 20→130 via harvest, but empire does not. So a passive player CAN finish 5 turns with tableau never moving. AC5 is therefore **not** "any run moves the tableau"; it is "a run that invests visibly moves it, and a run that does not stays flat". A test that only checks a hand-picked investing run would pass even if the tableau were hard-coded to always show progress.

```ts
// src/lib/tableau.ts
export type Tier = { id: string; label: string; reached: boolean };
export function tableau(empire: { farm_capacity:number; storage_capacity:number; route_established:boolean }): Tier[]
// thresholds (boolean, not level):
 // 0 Family Farm           — reached always (farm >=5) — starting tier, proves render works
 // 1 Expanded Grain Estate — reached when farm >=15 (one expansion) — measured: one expand_farm lands here
 // 2 Granary Network       — reached when storage >=180 (one granary) — measured 130→180
 // 3 River Trade Access    — reached when route_established === true — measured false→true
```

- Four tiers exactly as spec example order; glyph/colour uses `--grain` then `--river` for trade access.
- Tier is boolean, not level — farm 25 still tier 1, storage 230 still tier 2; keeps function simple and avoids inventing `OperationState.level` (DECISIONS 017).

**Tests (AC5 made falsifiable both ways):**

1. **Positive — investing run changes:** load two measured `GameView`s via `TestClient(create_app())`: initial `{5,130,false}` and post-investing `{15,180,false}` (expand+granary, as in grill capture). Assert `expect(reachedCount(final) > reachedCount(initial))` and `expect(labels(final)).not.toEqual(labels(initial))`. This is the Playwright path's trigger (E2E will click `expand_farm` then `build_granary` within 5 turns).

2. **Negative — passive run does NOT change:** `tableau({5,130,false})` vs `tableau({5,130,false})` after 5×`hold` (same empire). Assert `expect(tableau(holdInitial)).toEqual(tableau(holdFinal))` — proves tableau is not spuriously animating or always-progressing.

3. **E2E:** capture `[data-testid="empire-tableau"]` text at turn 0; after committing `expand_farm` (or `secure_route`) assert `expect(tableauEl).not.toHaveText(initialText)`. A broken `useMemo` dependency or stale prop would keep old text and fail.

If any threshold exceeds reachable range (e.g. `farm>=25` requiring two expands, unaffordable in 5 turns with other investments) the positive test fails — threshold choice is constrained by measured 5-turn economy.

---

## Work Plan

Ordered; each is a commit-sized unit. Do not start unit n+1 until n's validation is green.

**W0 — Branch + exploit-free verification baseline (no code yet)**

- Create `section/11-mobile-react-playable` from `origin/main`; confirm `frontend/` empty, backend green (`make test/lint/type/format-check`).

**W1 — Scaffold Vite + TS + Query + proxy + tokens — grill-pinned**

- `npm create vite@latest frontend -- --template react-ts` equivalent; `npm i @tanstack/react-query`; add `vite.config.ts` proxy `/api → http://localhost:8000`, `VITE_API_URL` read, `index.html`, `tsconfig` strict, `vitest.config.ts` (`environment: jsdom`), `playwright.config.ts`, `eslint` (flat config) + `prettier`. Import parched `tokens.css` with `data-pressure` blocks and base typography (serif for signal/headlines, sans for UI, `tabular-nums` on numerals).
- **Grill — pinning to prevent scaffolding drift (measured `node v26.5.0 / npm 11.17.0 / vite 8.2.1` today):** set `frontend/package.json` `engines.node >=22` (or `>=20`), pin `vite ^6.4` or `^8.2` with exact `packageManager` (`npm@11`), add `overrides`/`resolutions` only if needed. **Do not** use `latest` tag blindly in CI — `package-lock.json` is committed. Most likely failures: (1) `eslint` flat config (`eslint.config.js` required since v9, not `.eslintrc.json` — validate `npm run lint`); (2) `vitest` needs `jsdom` separate dep; (3) `playwright` needs `npx playwright install --with-deps chromium` (browser download) — add to `frontend/README` and CI step; (4) Vite proxy only works in `dev` — e2e must start `vite preview` or `vite dev` and wait on `webServer.url` (playwright `webServer` config). Verify with `npm run build && npm run preview` locally.
- Validate: `npm run typecheck`, `npm run lint`, `npm run test` (no tests yet), `npm run dev` serves `/` with placeholder; `npx playwright install --dry-run` shows chromium present.

**W2 — API client + Query layer + `format.ts` boundary**

- `src/api/client.ts` (`createGame`, `getGame`, `commitChoice`), `src/api/queries.ts` (keys, mutations with `isPending`), `src/api/types.ts` (minimal `GameView` typing matching `schemas.py`), `src/lib/format.ts` + `src/lib/__tests__/format.test.ts` including the `/1000` grep assertion.
- Validate: `npm run test` green; grep assertion passes; manual `createGame` via dev proxy.

**W3 — Layout shell + HeaderBar + WorldBand + MarketPulse/RouteLine + RivalsStrip**

- Implement header (pips `Turn n of 5`, cash via `format.money`), WorldBand (serif signal, pressure tint), MarketPulse pair side-by-side (each `MarketCard` shows supply/demand/price via `format.pricePerUnit`), `RouteLine` (river colour, dashed/grey when `!established`, label `format.signedPricePerUnit(next_margin)`), `RivalsStrip` with turn-0 empty state "Mira and Daran act after your first decision".
- Validate: render against measured turn-0 `GameView`; no economy calc; `rival_headlines === null` shows empty state, not hidden card.

**W4 — Decision surface (verb cards + quantity + commit) + commit flow**

- `DecisionBlock` grouping, `VerbCard`, `QuantityToggle`, `Commit` with `disabled`+`isPending`, `expected_revision` wiring, `409` refetch toast ("the game moved on") and re-enable, `FooterDebug` seed line.
- Validate: choose 5 turns locally; 409 path tested by double-fire in test; no cost recomputation.

**W5 — Empire tableau + OutcomeReveal beat sequence + CompletionSummary**

- `src/lib/tableau.ts` + `src/__tests__/tableau.test.ts` (tiers + capture delta test); `EmpireTableau` vertical chain; `OutcomeReveal` staged beats with `data-reveal-state` + Skip; `CompletionSummary` (wealth/cash/grain/farm/storage + rival headlines + `is_complete`).
- Validate: `tableau` capture test passes; reveal waits on `data-reveal-state="complete"`; trace collapsed by default.

**W6 — Playwright critical path + screenshots + console-error guard + desktop smoke — grill-scoped**

- `e2e/critical.spec.ts` (mobile 390×844 full 5-turn flow, screenshot helper, console error collector; desktop smoke at 1280×800). Four screenshots with exact indices (see Validation): `first-decision` at `turn 0` (`normal`), `drought-warning` at `turn 2` before commit (`worsening_dry`), `drought-reveal` after committing `turn 3` (`latest_outcome drought` inside reveal, header `aftermath`), `final-summary` at `turn 5` (`is_complete`).
- `playwright.config.ts`: two projects (`mobile: {viewport:{width:390,height:844}}`, `desktop:{viewport:{width:1280,height:800}}`), `webServer: {command:'npm run dev', url:'http://localhost:5173', reuseExistingServer:!process.env.CI}` with proxy to `8000`; `expect` timeout 10s; no `waitForTimeout` anywhere (eslint ban). Collect `console` + `pageerror` from navigation start.
- Validate: `npx playwright test` green on CI-like run; screenshots committed to `frontend/e2e/screenshots/` or `docs/` as configured; `grep -r waitForTimeout frontend/e2e` returns 0.

**W7 — Docs + gates + push**

- Add `DECISIONS 023` text; update `STATE.md` (file tree, Boundaries, verification output); ensure `make test/lint/type/format-check` + `npm run typecheck/lint/test` all green; `graphify update .`; push branch.

---

## Validation Plan — AC1–AC8 → named tests — **grill-amended with confound analysis**

Backend gates unchanged; frontend gates added. Every gate runs before push; `STATE.md` `Last known green` copies observed output. For each AC, the grill lists the confound that would make a naive test pass spuriously and what rules it out (pattern #1/#3).

| AC | Named test(s) | Confound that makes naive test pass spuriously | What rules it out (in this plan) |
|---|---|---|---|
| **AC1** 5-turn completion | `e2e/critical.spec.ts › completes 5-turn game on mobile` (real backend via proxy) + `src/api/__tests__/queries.test.tsx` not as primary (mocked tests cannot prove completion) | Mocked `GameView` walk or stubbed `createGame` that always returns `completion_summary` after 5 calls — passes without ever hitting real API. Also, a test that only checks `turn===5` but not `completion_summary !== null` would pass one turn early. | E2E hits real `POST /api/v1/games` + 5 real `POST …/choices/{id}` with `expected_revision` from live `GameView`. Asserts `completion_summary.is_complete===true` **and** `turn===turn_limit===5` **and** `available_choices.length===0`. No mocks on critical path. |
| **AC2** no dense table | `e2e/critical.spec.ts › decision surface has no table` + visual check | Test scopes to `page.locator('table').count===0` globally — passes even if a table is hidden off-screen or rendered outside decision block but still required to decide (false negative). | Scope to `page.locator('[data-testid="decision-block"] table')` and also assert all required info (cost, quantity, margin sign) is **visible** inside decision block without opening `<details>` (`toBeVisible` + text contains `format.money` value). |
| **AC3** what changed and why | `e2e › reveal shows wealth/inventory/price deltas and ≤3 drivers` (scoped to `data-reveal-beat`) + unit `outcomeReveal.test.tsx` asserting driver `label` equals engine label verbatim | Test reads header numbers (top-level `player_summary.wealth`) instead of `latest_outcome.wealth_delta` — passes even if reveal is empty, because header also changes. Or re-ranks drivers client-side and happens to match engine order on one seed. | Each beat asserts scoped to `[data-testid="outcome-reveal"] [data-reveal-beat="2"]` contains `format.signedMoney(wealth_delta)` from `latest_outcome`, and `beat="3"` contains engine `drivers[0].label` verbatim (mock with distinct engine labels to catch re-wording). Cross-check: `latest_outcome.world==="drought"` while header is `aftermath` — header text would mismatch, exposing top-level vs outcome confusion. |
| **AC4** rivals visible | `e2e › rivals card always visible, empty state on turn 0` | Test checks `rivals-strip` exists after first turn only — passes if card is hidden on turn 0 (null case) or if frontend fabricates a headline client-side ("Mira is preparing…") to always show something. | Turn 0 asserts `data-testid="rivals-strip"` visible **and** `toContainText("act after your first decision")` **and** not containing "Mira:" headline. Turn ≥1 asserts `toContainText("Mira:")` and `toContainText("Daran:")` from real API. Completion asserts `final_rival_headlines` presence. No headline string is ever constructed in frontend code (grep for "Mira" only in tests). |
| **AC5** empire visibly changes — **falsifiable both ways** | Naive: compare `tableau(initial)` vs `tableau(hand-picked investing final)` — passes even if `tableau()` is `() => always [true,true,true,true]` (always-progress) or if component ignores `empire_summary` but test reads the function directly without DOM. Hold-only run proves it: `hold×5` leaves empire `{5,130,false}` — a naive "any run moves" test would falsely fail for hold, or falsely pass if hand-picked. | Three tests: (1) positive investing run `{5,130,false}→{15,180,false}` must increase reached count; (2) negative passive run `{5,130,false}→{5,130,false}` (hold×5) must stay equal (catches always-progress); (3) E2E DOM: `empire-tableau` text changes after a real `expand_farm` click (catches stale prop/`useMemo` bug). Thresholds validated against measured 5-turn economy — `farm>=15` reachable with one expand (cost 500, affordable), `storage>=180` with one granary (cost 300), route with one `secure_route`. |
| **AC6** no double-submit — **falsifiable both ways** | Naive: `fireEvent.click(commit)` once then assert `disabled` — passes if button disables after response but not during flight (still double-fires). Or test that fires two `fetch` from different `expected_revision` — passes even without guard because second revision is already different. | Two layers, both load-bearing: (a) **UI guard:** `page.route` delays `/choices` 300ms, click Commit twice within 50ms, assert `requestCount===1` **and** `button` is `disabled` while `isPending` (TanStack `isPending`). Removing `disabled` or `isPending` makes second `fetch` fire → fails. (b) **Revision guard:** real `TestClient` fires two `POST …/choices/{id}` with identical `expected_revision` concurrently → must be `[200,409]` (as in `test_concurrent_same_revision_one_wins`). If frontend omitted `expected_revision`, both return `200` → fails. Also handles `409 "game complete"` vs stale: check `completion_summary` not string parse. |
| **AC7** zero console errors | Collect `page.on('pageerror')` but not `console` `error` type — passes while `console.error()` still fires. Or run E2E with `headless: false` where some errors are swallowed. | Collect both `page.on('console', m=> m.type()==='error')` **and** `page.on('pageerror')` from navigation start before `goto`; `expect(errors).toEqual([])` and `expect(pageErrors).toEqual([])` at end of full 5-turn flow. Fail on any entry. |
| **AC8** Playwright mobile + desktop smoke | Desktop test reuses mobile viewport or only checks `goto` without interaction — passes even if layout breaks at 1280px or commit path is phone-only. `waitForTimeout` hides flake. | Two Playwright projects: `mobile` (390×844) runs full 5-turn flow + 4 screenshots + all ACs; `desktop` (1280×800) runs smoke `create + 1 commit + reveal` and asserts header + market pair side-by-side still visible (`toBeVisible`). Both use `expect(locator('[data-testid="outcome-reveal"][data-reveal-state="complete"]')).toBeVisible()` waits, zero `waitForTimeout` (eslint `no-restricted-syntax` ban). |

**Screenshot assertions (browser verification) — grill-scoped:**

- `first-decision.png` — `turn 0` `pressure_stage==="normal"`, `signal` "The growing settlement…", **6 verb cards** visible (hold + 5, collapsed to 6), no reveal.
- `drought-warning.png` — **`turn===2` before commit** `pressure_stage==="worsening_dry"`, `signal` "The dry spell persists…" (`worsening_dry` is the only turn where `next_world_known==="drought"` per `pressure.py:114`), world still `normal`.
- `drought-reveal.png` — **after committing at `turn===3`** `latest_outcome.pressure_stage==="drought"` / `world==="drought"` / `title==="Drought"` scoped inside `[data-testid="outcome-reveal"]`; header/`world-band` outside shows `aftermath/normal` (proves disagreement; header-only check would be vacuously wrong).
- `final-summary.png` — `turn===5` `completion_summary.is_complete===true`, `final_wealth`/`final_cash`/`final_grain`/`final_farm_capacity`/`final_storage_capacity` from `CompletionSummaryView`, `final_rival_headlines` present.

**Grep / contract assertions — grill-corrected:**

- `format.test.ts › no inline price/bps division outside format.ts` — scans for `/\s*1000` and `/\s*10000\b` (not bare `/100`), fails if any `current_price/1000` outside `format.ts`. See K2 for false-positive analysis.
- `tableau.test.ts › does not read market prices` (ensures no economy leakage — `tableau` args are only `empire_summary` fields)
- `decisionBlock.test.tsx › shows cost from ChoiceView.cost, not computed` (mock `cost: 275` with `price: 9999` to catch recomputation; renders "275")

**Gate commands (explicit):**

```bash
# backend (existing)
make test && make lint && make type && make format-check

# frontend (new — whether/how they join Makefile)
cd frontend && npm run typecheck   # tsc --noEmit
cd frontend && npm run lint        # eslint + prettier --check
cd frontend && npm run test        # vitest run
npx playwright test                 # e2e, mobile + desktop

# repo Makefile additions (W1):
# front-type:  cd frontend && npm run typecheck
# front-lint:  cd frontend && npm run lint
# front-test:  cd frontend && npm run test
# front-e2e:   cd frontend && npx playwright test
# Proposal: `make test` stays backend-only; CI runs `make front-test` separately until Section 12 joins them into `make check-all`. State this in plan so gate drift is explicit — do not silently merge frontend into `make test`.
```

---

## Risks / Rollback — **grill-amended**

| risk | likelihood | impact | mitigation |
|---|---|---|---|
| **Proxy misconfig → CORS or 404 in dev/e2e** | medium | blocks all flows | Validate `vite.config.ts` proxy early (W1); `VITE_API_URL` fallback; e2e asserts `response.ok` on `POST /api/v1/games`. No backend CORS change. `webServer` url wait ensures backend up before tests. |
| **`rival_headlines null` mishandled → crash or hidden card** | medium | AC4 fail, hidden defect | Explicit `if (rival_headlines === null)` branch with empty state text; unit test for null vs `{mira,daran}`. |
| **Turn off-by-one → "Turn 6 of 5"** | medium | spec violation | Display `turn+1 of turn_limit`; reveal `resolved_turn+1`; completion when `completion_summary !== null`, not `turn===turn_limit`. Unit test with measured `turn 5` final. |
| ** Crossing `latest_outcome` vs top-level → wrong weather in reveal** | medium | AC3 fail, subtle | Reveal reads only `latest_outcome.*` for world/pressure/title/deltas/trace; top-level only for post-reveal `signal`. E2E asserts `latest_outcome.world==="drought"` while top-level is `"aftermath"` on turn after drought (header vs reveal scoped separately). |
| **AC5/AC6 tautological tests (patterns #1/#3)** | high | false green, rerun as Section 12 relies on it | AC5: positive investing + negative passive + E2E DOM (see Validation); AC6: UI `disabled`+`isPending` **and** revision `[200,409]` both must be asserted. Both are now dual tests. |
| **Playwright flake from `waitForTimeout`** | high | blocks AC8 | Forbid `waitForTimeout` in `e2e/` via eslint `no-restricted-syntax`; wait on `data-reveal-state="complete"` and `data-testid` selectors. Grill adds `grep -r waitForTimeout` gate in CI. |
| **`format.ts` leakage → 5000 rendered raw** | medium | trust erosion | Grep for `/1000`+`/10000` not `/100`; snapshot showing `5.000`. False-positive risk for `/100` addressed by narrowing pattern (see K2). |
| **Scaffolding drift (vite/eslint/jsdom/playwright)** | medium | build fails, e2e no browser | Pin `vite`, `eslint` flat config, `jsdom`, `playwright` chromium; commit `package-lock.json`; add `npx playwright install --with-deps chromium` to setup. See W1. |
| **Choice-count overflow (9 vs 8)** | low | layout overflow at 390px | Layout stacks 6 verb cards vertically with scroll; 9 choices still 6 cards (second quantity inside card). Tested after `secure_route`. |
| **409 misclassification (stale vs complete)** | medium | wrong toast, or infinite retry on complete | Do not parse `detail` string; check `game.completion_summary !== null` first, then treat `409` as conflict iff not complete. Measured: stale `409` with conflict message, complete `409` with "game complete", stale on complete also `409` conflict — revision check fires first. |
| **Desktop second layout creep → scope + e2e ×2** | low | delay | Enforce `max-width:480px` centred, no second layout; review diff for desktop-only components. |
| **State drift (`STATE.md` stale)** | medium | handoff break | `STATE.md` updated in same commit as code per `AGENTS.md` §15; copy observed `make test`/`npm run test` output. |

**Rollback:**

- Frontend is additive and isolated (`frontend/` + proxy). Revert is `git revert <W1..W6>` or branch delete; backend untouched so no DB/migration rollback. If proxy approach fails in CI, fallback is `VITE_API_URL=https://<backend>` with backend adding `CORSMiddleware` — escalate before doing, as it is the only backend change that could become unavoidable.

---

## Open Questions

- **None that block planning.** The three product-adjacent choices below are decided as stated; only a product-owner reversal would change them — marked `ESCALATE` if owner wants different intent.

- **Q1 — ESCALATE only if owner insists on literal "2–4 buttons":** Do we hide legal moves to hit 4, or document deviation as in `DECISIONS 023`? **Recommendation:** deviation (verb cards + quantity + commit). Hiding moves violates `DECISIONS 017` and would reintroduce `DECISIONS 022`-class bug; alternative "more" disclosure still violates "2–4 visible". No further options without breaking a higher decision.

- **Q2 — ESCALATE only if owner wants desktop dashboard:** Confirm centred 480px single column is acceptable for desktop (per design direction §2) vs a two-column variant. **Recommendation:** single column; two-column doubles e2e surface and contradicts "no multi-tab dashboard maze".

- **Q3 — ESCALATE only if backend change looks needed:** If `route_status.next_margin` semantics prove insufficient for a loss-at-peak lesson, do we add a separate `affordability_hint` field or keep current `cost`/`next_margin` only? **Recommendation:** keep current; `DECISIONS 017` clause 7 says supply values, not advice. No backend change.

---

## Non-goals reminder

Do not build: auth, Postgres, LLM, `render.yaml`/`alembic`, content DSL, history endpoint, bottom nav, second age, free-text commands. `AGENTS.md` §14 and `BUILD_SPEC §31` forbid it.

---

## Appendix — Measured payload excerpts (for reviewer convenience)

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

After `expand_farm` (turn 1): `farm 15`, `storage 130`, `route false`, `cash 500`, `inventory 130`, `home 5157`, `river 6240`, `next_margin 783`, `rival_headlines` populated, `latest_outcome {resolved_turn:0, title:"A Growing Settlement", pressure_stage:"normal", world:"normal", wealth_delta:70, inventory_delta:110, price_delta:157}`.

---

---

## Grill — Decision-Forcing Questions, Answers, and Consequences

Headless grill per `docs/ORCHESTRATION.md` §2: the plan was questioned as if by a second reviewer, answered from measured payload or computed experiment, and changed in place above. Changes are marked **grill-amended** inline.

### Q1 — Tests that pass for the wrong reason (pattern #1/#3) — AC1–AC8 confounds

**Question:** For each AC, what confound makes your named test pass spuriously, and what rules it out? Be specific for AC5/AC6.

**Answer:** See Validation table "Confound that makes naive test pass spuriously → What rules it out". Key amendments from grill:
- AC1: mocked walk cannot prove completion — E2E must hit real `TestClient` via proxy and assert `completion_summary.is_complete===true` plus `turn===turn_limit===5` plus `available_choices===[]`.
- AC3: header numbers move even if reveal empty — must scope to `outcome-reveal` and assert `latest_outcome` vs top-level disagreement.
- AC5: investing-only test passes if tableau hard-coded to always-progress; added negative passive-run test (`hold×5` stays flat) plus E2E DOM check.
- AC6: single-click disabled test passes if disable happens after response; added `page.route` delay + `requestCount===1` plus real `[200,409]` concurrency test.
- AC7: `pageerror` alone misses `console.error`; collect both from navigation start.

**Consequence:** Validation rewritten as confound table; no mock on critical path.

### Q2 — Tableau thresholds actually move?

**Question:** You chose `farm>=15`, `storage>=180`, `route_established`. Run engine across seeds and show tier set changes for a typical investing run, and find a pattern where it does NOT change.

**Experiment:** `uv run python3` with `TestClient(create_app())` across seeds `playtest-1`, `seed-001`, `seed-xyz`, `another-seed`, `test-seed-99`, all `hold×5` → empire consistently `{farm 5, storage 130, route false}` — tableau never moves (inventory 20→130 still, empire flat). Investing run `expand_farm → build_granary → buy 55 → hold → sell` on `playtest-1` → `{farm 15, storage 180, route false}` — reaches tiers 0+1+2. Route path `secure_route` alone → tier 3 reachable in 1 turn.

**Answer:** Thresholds are reachable within 5 turns (one expansion cost 500 affordable at start, one granary 300, one route 400). But hold-only proves AC5 is **not** universal — it is conditional on investing. The original plan's single positive test would pass even if tableau were always-true.

**Consequence:** `tableau` section amended to boolean tiers with three tests (positive investing, negative passive, E2E DOM).

### Q3 — Units grep: does it fire, and does it false-alarm?

**Question:** Prove grep assertion fires; what legitimate ` / 100` or `/1000` might trip it falsely? Lint vs grep?

**Experiment:** Backend grep for `/\s*1000|/\s*100\b` found 40 hits — all legitimate engine/tests (`qty*price//1000`, `//10000`, `status_code//100`, `alpha/100` in vendored `pydantic`). Frontend will have `Date.now()/1000`, `width/100*pct`, `opacity` — all would false-alarm on `/\s*100`.

**Answer:** Narrow grep to `/\s*1000` (price milliunits) and `/\s*10000\b` (bps) — not bare `/100`. Still falsifiable (any `current_price/1000` outside `format.ts` trips). Add eslint `no-restricted-syntax` as belt-and-braces but keep grep as hard gate.

**Consequence:** K2 rewritten: pattern is `/1000` + `/10000\b`, not `/100`.

### Q4 — 409 stale vs 409 complete: distinguishable without string parsing?

**Experiment:** `TestClient` — stale `expected_revision 0 != current 1` → `409 {"detail":"conflict: expected_revision 0 != current 1"}`. Complete with current rev → `409 {"detail":"game complete"}`. Stale on complete also returns `{"detail":"conflict: expected_revision 0 != current 5"}` (revision check fires before complete check per `service.py` order). `422` for missing `expected_revision`.

**Answer:** Both are `409` but distinguishable by **local** `game.completion_summary !== null` — not by `detail.includes("complete")`. Client must check completion before classifying conflict, and must not parse `detail` string.

**Consequence:** Decision surface section adds explicit 409 handling note: check `completion_summary` first, use status+local state, show non-destructive "game moved on" toast only for stale.

### Q5 — Which turn is warning vs reveal? Does screenshot prove reveal shows drought?

**Experiment:** Full `hold` walk with `pressure_stage` before/after table (see Outcome section). Indices: warning decision `turn===2` (`worsening_dry`, signal "The dry spell persists…", `next_world_known==="drought"` per `pressure.py:114`), drought reveal after committing `turn===3` (`latest_outcome.pressure_stage==="drought"` / `world==="drought"` / `title==="Drought"` while top-level already `aftermath/normal`).

**Answer:** Original plan said "Turn 3 decision" ambiguously — now pinned to `turn===2` for warning, `resolved_turn===3` for reveal. A header-only assertion would check `aftermath` and vacuously pass; must scope to `[data-testid="outcome-reveal"] [data-reveal-beat="1"]`.

**Consequence:** Outcome section adds measured index table and scoped Playwright assertion for drought reveal proving header/reveal disagreement.

### Q6 — Scaffolding risk from nothing

**Question:** What in toolchain fails most likely?

**Answer:** Measured `node 26.5 / npm 11.17 / vite 8.2.1`. Risks: eslint v9 flat config (`eslint.config.js` required), `vitest` needs separate `jsdom`, `playwright` needs `npx playwright install --with-deps chromium`, Vite proxy only in `dev` (e2e `webServer` must wait on url), `latest` tag drift. No mitigation in original plan.

**Consequence:** W1 amended with pinning (`engines.node`, committed `package-lock.json`), flat-config note, `jsdom` dep, `playwright install` step, `webServer` config, and `npm run build && preview` check.

### Q7 — Choice-count maximum with route early

**Question:** Re-measure max `available_choices` including route path — does layout hold?

**Experiment:** Random walk 600 games + targeted `secure_route` then `buy`. Measured turn 0: 8 choices (6 kinds). After `secure_route` (cash 600, inv 70, route true): 9 choices (`hold, expand_farm, build_granary, buy×2, sell×2, ship×2`) — 6 distinct kinds, not 7 because `secure_route` disappears. Random max across seeds also 9 with same 6 kinds.

**Answer:** Original plan said "8→5 cards" — off by one. True max is 9→6 cards (the extra is second quantity inside same verb). Layout of 6 stacked verb cards at 390px (~56px each + gap → ~400px scrollable) still holds.

**Consequence:** Context and Decision sections corrected to 9/6; card layout note updated; `BUILD_SPEC "2–4 buttons"` deviation now measured against 9.

---

### Overall grill verdict

The plan was structurally sound (single source for pressure, verb cards, staged reveal, proxy) but had **four material inaccuracies** corrected in place: (1) choice max 8→9, (2) grep over-broad `/100` → `/1000`+`/10000`, (3) underspecified AC5/AC6 that would pass for wrong reason, (4) ambiguous drought screenshot indices that would allow a header-only check. All are now falsifiable with measured indices and dual tests. No product-owner escalation — decisions remain as in K4 (`DECISIONS 023`).

---

*Plan revised after headless grill — no implementation code written. Awaiting Approve / Request changes.*
