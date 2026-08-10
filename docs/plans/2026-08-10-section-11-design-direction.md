# Section 11 — Design Direction (Claude, design authority)

> Input to the Section 11 plan, not the plan itself. Authority: `docs/ORCHESTRATION.md` §5
> — "Claude owns game-design judgment" and "when UI sections arrive (11, 20), actively drive
> visual design and consistency."
>
> Everything below is derived from **measured API output**, not from intent. The reference
> capture is a real 5-turn run (`run_seed="playtest-1"`) against `create_app()`.

---

## 0. Non-negotiable facts about the payload (measured, not assumed)

These are the traps. Each one silently produces a wrong-but-plausible UI.

### 0.1 Prices are milliunits; cash is whole coins

`BUILD_SPEC §12` declares `PriceMilliunits`. `actor.cost_for_quantity` is
`(quantity * price_milli) // 1000`.

| Field | Unit | Raw value at start | Correct display |
|---|---|---|---|
| `player_summary.cash` | `Money` | `1000` | `1,000` coins |
| `player_summary.wealth` | `Money` | `1100` | `1,100` coins |
| `ChoiceView.cost` | `Money` | `275` | `275` coins |
| `*_market.current_price` | `PriceMilliunits` | `5000` | `5.000` coins/unit |
| `*_market.base_price` | `PriceMilliunits` | `5200` | `5.200` coins/unit |
| `route_status.transport_cost_per_unit` | `PriceMilliunits` | `300` | `0.300` coins/unit |
| `route_status.next_margin` | `PriceMilliunits` | `-100` | `-0.100` coins/unit |
| `OutcomeView.price_delta` | `PriceMilliunits` | `157` | `+0.157` coins/unit |
| `*_market.responsiveness`, `reliability_bps`, `OutcomeDriver.impact_bps` | `BasisPoints` | `4000` / `10000` | `40%` / `100%` |
| `OutcomeDriver.impact_money`, `wealth_delta` | `Money` | `-500` | `−500` coins |

**Directive.** One `format.ts` module owning `money()`, `pricePerUnit()`, `percent()`,
`signedMoney()`, `signedPricePerUnit()`. No inline `/1000` or `/100` anywhere else.
Unit-tested with vitest. A grep for `/ 1000` or `/1000` outside `format.ts` should return
nothing — make that an actual assertion in the test file, not a code-review hope.

**Falsifiability.** A test must fail if `current_price` is rendered as `5000`.

### 0.2 `rival_headlines` is `null` on turn 0

Measured: `turn_0_initial.rival_headlines === null`. Rivals have not acted yet. From
`after_turn_1` onward it is populated every turn, and `completion_summary.final_rival_headlines`
carries them on the end screen.

AC4 says "rivals remain visible throughout the run." Satisfy it with a **persistent rivals
card that renders an explicit empty state** ("Mira and Daran act after your first decision"),
not by hiding the card and not by fabricating headlines client-side. Fabricating a headline
would be inventing canonical-looking state — the same error `DECISIONS 017` clause 8 blocked
for `empire_summary`.

### 0.3 `turn` is a 0-based index of the *upcoming* decision

Measured: initial `turn: 0`; after one commit `turn: 1`; final view `turn: 5` with
`available_choices: []` and `completion_summary` non-null. `turn_limit: 5`.

- Decision header reads `Turn {turn + 1} of {turn_limit}`.
- `OutcomeView.resolved_turn` is also 0-based (`0` for the first resolved turn) — the reveal
  header reads `Turn {resolved_turn + 1}`.
- Completion is `completion_summary !== null`, **not** `turn === turn_limit`. Do not derive it.
- Never render "Turn 6 of 5".

### 0.4 Choice count is 6–8, not 2–4

Measured at start: 8 choices across 5 verbs. `BUILD_SPEC §11` asks for "2–4 action buttons";
`DECISIONS 017` forbids hiding any legal choice. Both cannot be satisfied literally. See §3.

### 0.5 `latest_outcome` context ≠ top-level context

`after_turn_3`: top-level `world="drought" / pressure_stage="drought"` (the decision you are
about to make) while `latest_outcome.world="normal" / pressure_stage="worsening_dry"` (the
turn that just resolved). This is `DECISIONS 017` clause 5 and it exists specifically for this
screen. The reveal must read from `latest_outcome.*`; the decision screen must read from
top-level. Crossing them produces a reveal that describes the wrong weather.

---

## 1. Mood and visual language

**Illuminated ledger, not a spreadsheet and not a fantasy RPG.** The player is a grain
merchant in an ancient river settlement keeping accounts. Warm, tactile, hand-kept. Every
number should feel like it was written down by someone who cares about it.

### 1.1 Palette

Semantic roles matter more than exact hexes; tune by eye, but keep the roles.

```
--ink            #1F1A14   body text, primary
--ink-soft       #5C5245   secondary text
--parchment      #F5EDE0   page ground
--parchment-hi   #FFFAF1   raised card
--rule           #DCCFBA   hairlines, dividers

--grain          #C8912F   Home Valley identity, grain, prosperity
--river          #2F7B78   River Town identity, route, water
--drought        #A6412B   pressure, loss, drought
--gain           #4A7C43   positive deltas
```

**Two market identity colours are load-bearing.** Home Valley is always `--grain`; River
Town is always `--river` — in the market cards, in the route line that connects them, in the
outcome reveal, in the empire tableau. The player learns "ochre = home, teal = river" in one
turn and never has to read a label again. Use the same colour for the same place *everywhere*
or the whole device fails.

### 1.2 Pressure drives the atmosphere

`pressure_stage` moves `normal → early_dry → worsening_dry → drought → aftermath`.

This is the single best opportunity in the whole game and it is currently just a string.
**Bind it to a CSS custom-property theme on the page root** so the screen itself dries out as
the arc builds: parchment warms and desaturates toward bone, the grain accent bleaches, a
faint heat-haze vignette rises, hairlines get drier. `aftermath` cools back but does not
return to `normal` — it looks *recovered*, not untouched.

`BUILD_SPEC §6` is "Signals Before Consequences". A tinted screen is the signal being *felt*
one turn before the number arrives. This is the cheapest possible way to make the pressure
arc legible, and it costs one `data-pressure` attribute plus a block of CSS variables.

**Directive:** exactly one source — `data-pressure={pressure_stage}` on a root element,
themed in CSS. No per-component conditionals, no JS colour maths.

### 1.3 Typography

- **Display serif** for the world's voice: age/chapter label, `signal`, `OutcomeView.title`,
  rival headlines. This is the game talking.
- **Sans** for UI chrome and all numbers.
- **All numerals `font-variant-numeric: tabular-nums`.** Non-negotiable — the outcome reveal
  animates numbers and proportional digits make them jitter and look cheap.
- Signal text is the largest non-title text on the screen. It is the reason the turn exists.

### 1.4 Motion

- Every transition respects `prefers-reduced-motion: reduce` — and reduced motion must reach
  the same end state, never a broken half-state.
- Motion budget: reveal beats ~250–400ms each, everything else ≤200ms.
- No motion on anything that isn't communicating a state change.

---

## 2. Layout — single column, 390×844, no tabs, no bottom nav

`BUILD_SPEC §11`: "no multi-tab dashboard maze", "required decision information is visible on
the main screen", "detail views are optional depth, not homework".

**Decision screen**, top to bottom:

1. **Sticky header bar** (compact, ~56px): age/chapter label · `Turn n of 5` as filled pips ·
   cash. Pips make progress ambient instead of arithmetic.
2. **World band** — pressure-tinted, holds the display-serif `signal`. This is the hero /
   world-state area; placeholder art is fine but the *tint* is not a placeholder.
3. **Empire tableau strip** — see §4.
4. **Market pulse pair** — Home Valley and River Town **side by side**, not stacked. They are
   only meaningful in comparison; stacking them destroys the arbitrage read, which is the
   entire point of two markets. At 390px, two cards at ~175px each is comfortable.
   Between/under them: the **route line** — a connector rendered in `--river`, dashed and
   greyed when `established: false`, solid when true, labelled with `next_margin` per unit and
   coloured by its sign.
5. **Rivals strip** — Mira and Daran, one line each, display serif, with the turn-0 empty
   state from §0.2.
6. **Decision block** — see §3.

**Desktop** (`≥900px`): the same single column, `max-width: 480px`, centred, on a wider
parchment ground. Do not build a second layout. "Desktop remains usable", not "desktop is a
dashboard". A two-column desktop variant is scope creep and doubles the Playwright surface.

---

## 3. The decision surface — resolving the 2–4 vs 6–8 conflict

`BUILD_SPEC §11` wants "2–4 action buttons". The API returns 6–8 `ChoiceView`s over 5–7 verbs,
and `DECISIONS 017` forbids hiding any legal one. **The literal reading of both is impossible.**

**Ruling: group by verb, choose quantity inside the verb, commit explicitly.**

- One **verb card** per distinct `kind` — `hold`, `expand_farm`, `build_granary`,
  `secure_route`, `buy_grain`, `sell_grain`, `ship_grain`. Typically 5–6 cards, max 7.
- Verbs with two quantities (`buy_grain:55` / `buy_grain:110`) render **one card with a
  two-option segmented control**, not two cards. 8 choices collapse to 5 cards at start.
- Each card shows the verb, its cost or proceeds in coins, and its one-line consequence.
  Never a table.
- Selecting a card selects; a single **Commit** button at the bottom submits. The commit beat
  is in the spec's primary flow ("choose one major action → commit") and it is also the
  natural home for the AC6 double-submit guard.

**This is a deliberate, documented deviation from the "2–4 action buttons" line.** Record it
in `DECISIONS.md` with this rationale: the spec line and `DECISIONS 017` are in direct
conflict; `DECISIONS 017` is the more recent and more specific authority, and its principle
("the player remains free to make economically bad, contrarian, or anticipatory decisions")
is load-bearing for the game. What the "2–4" line is actually protecting against is a dense
table of micro-operations — verb cards with an explicit commit honour that intent while
keeping every legal move reachable. Do not silently ignore the line; do not silently obey it
by hiding moves either.

**Never** compute cost, margin, or affordability client-side. `ChoiceView.cost` and
`route_status.next_margin` are supplied precisely so the frontend does not. `DECISIONS 017`
clause 7 and `BUILD_SPEC §10`.

---

## 4. Empire tableau

`BUILD_SPEC §11` wants a lightweight visual of compounding; AC5 requires it to **visibly
change during the run**.

Only three real fields exist (`EmpireSummary`: `farm_capacity`, `storage_capacity`,
`route_established`). `DECISIONS 017` clause 8 forbids synthesizing operations with invented
levels.

**Ruling:** a pure presentation function `tableau(empire) -> Tier[]` mapping the three real
fields to named tiers, rendered as a vertical chain exactly like the spec's example:

```
Family Farm  →  Expanded Grain Estate  →  Granary Network  →  River Trade Access
```

- Thresholds derived from real gameplay ranges, not invented. Measured reference run:
  `farm_capacity` 5 → 15 → 25 → 35; `storage_capacity` 130 (start) with `+50` per granary;
  `route_established` false → true on `secure_route`.
- Pure function, unit-tested, **including a test that the label set changes** across the
  measured 5-turn capture — that is AC5 made falsifiable rather than asserted.
- Reached tiers in `--ink` with their identity colour; unreached tiers ghosted. The chain is
  always fully visible so the player can see what is ahead — that is the compounding hook
  (`BUILD_SPEC §8`).

---

## 5. Outcome reveal — the signature interaction

`BUILD_SPEC §9`. This is the payoff moment and it is where a merely-correct implementation
will feel worst. It is a **staged sequence**, not a results panel that appears at once.

Beats, in order, each reading from `latest_outcome.*` (never top-level — §0.5):

1. **Time advances.** `Turn {resolved_turn + 1}` and the display-serif `title`.
2. **The world changes.** `latest_outcome.world` / `pressure_stage` — if this differs from the
   previous turn's, that transition is the beat. Drought arriving should land visually.
3. **The numbers.** `wealth_delta`, `inventory_delta`, `price_delta` — count up/down from the
   previous value with tabular numerals, sign-coloured `--gain` / `--drought`.
4. **Top drivers, ≤3.** `drivers` is already ranked and capped by the engine (`trace.py`
   top-3 + residual). Render the supplied `label` verbatim with its `impact_money`. Do not
   re-rank, re-word, or recompute.
5. **Why — progressive disclosure.** `causal_trace` is ~40 nodes. It must be *available*, not
   *homework*: a collapsed "Show the full chain" that expands into the node list. Closed by
   default. The three drivers are the answer; the trace is the proof.
6. **Rivals.** What Mira and Daran did this turn.
7. **The next threat.** The *new* top-level `signal` — this is the hand-off back into the loop
   and the reason the player taps Continue.

**Requirements:**
- A **Skip / reveal-all** affordance. Five turns means five reveals; the fifth must not feel
  like a toll.
- `prefers-reduced-motion` collapses beats to their end state instantly, still in order,
  still complete.
- A stable test hook (e.g. `data-reveal-state="complete"`) so Playwright waits on a real
  signal, not on `waitForTimeout`. Timeout-based waits in the critical-path test are a
  flakiness generator and will be rejected in review.

---

## 6. Correctness requirements the UI must not get wrong

1. **`expected_revision` on every commit.** On `409`, refetch and show a non-destructive
   "the game moved on" state. Never silently overwrite, never silently swallow.
2. **AC6 double-submit.** Disable the commit control on the in-flight request *and* rely on
   `expected_revision` as the real guard. Both — the UI guard is UX, the revision is truth.
   Test it by firing two commits.
3. **No economy in the frontend.** No recomputation of cost, margin, wealth, affordability, or
   capacity. Consume `GameView`.
4. **Zero console errors on the critical path** (AC7) — asserted in Playwright by collecting
   `console` events and failing on any error, not by eyeballing.
5. **`run_seed` visible somewhere unobtrusive** (footer/debug line). Determinism is the
   project's spine; being able to read the seed off the screen makes a playtest report
   reproducible, which Section 12 needs.

---

## 7. Wiring, kept minimal

- Dev + test talk to the backend through the **Vite dev-server proxy** (`/api` →
  `http://localhost:8000`). This means **no CORS middleware is added to the backend in
  Section 11** — no backend change at all. Deployment cross-origin is Section 16/18's problem.
- `VITE_API_URL` is supported with default `/api/v1`, per `frontend/AGENTS.md`.
- TanStack Query per the stack decision; `GameView` is the single server-state source.

---

## 8. What is out of scope (do not build ahead — `BUILD_SPEC §31`)

Auth, database, LLM, real art pipeline, bottom navigation, multiple age screens, free-text
commands, a history/replay screen, a desktop dashboard layout, sound, i18n, animation
libraries beyond what the reveal needs.
