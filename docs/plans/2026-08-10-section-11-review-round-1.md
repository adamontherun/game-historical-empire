# Section 11 — Consolidated Plan Review, Round 1

> Reconciled by Claude (orchestrator) from three independent reviews: my own against the
> measured API, Muse's self-grill, and ChatGPT's. **This is the only document Muse acts on.**
> Overlapping findings are merged; scope creep into Sections 12+ is dropped.
>
> Targets: `docs/plans/2026-08-10-section-11-mobile-react-playable.md` (the plan) and
> `docs/plans/2026-08-10-section-11-design-direction.md` (my design direction — **it contains
> errors, corrected below; this document supersedes it wherever they disagree**).

---

## 0. Status

The plan is good and close to implementable; the grill materially improved it. But the
review turned up **nine blocking issues**, and four of them are errors in *my own* design
direction that would have propagated straight into the code. Everything here is measured or
quoted from the repo, not asserted.

---

## 1. Settled by the grill — confirmed, do not relitigate

| Item | Resolution |
|---|---|
| Drought-warning screenshot | Decision screen at raw **`turn === 2`** (`pressure_stage === "worsening_dry"`). Displays as "Turn 3 of 5" — key the test on the raw index. |
| Drought-reveal screenshot | The view after committing turn 2, raw **`turn === 3`**, where `latest_outcome.world === "drought"` while the header shows the next decision. |
| 409 handling | Never string-parse `detail`. Refetch, then branch on `completion_summary !== null`. |
| Units enforcement | Narrowed regex **plus** an eslint `no-restricted-syntax` rule. |
| Tableau | A passive (`hold×5`) run correctly stays flat — needs the negative test as well as the positive one. |
| Toolchain pinning | `engines.node>=22`, `vite ^8.2`, committed lockfile, flat eslint config, `jsdom`, `playwright install chromium`, `webServer.url` wait. |

**Corrected:** the simultaneous choice maximum is **9 choices across 6 verbs**; turn 0 is
**8 choices across 6 verbs** (not 5 — my design-direction §0.4 undercounted). Seven verb
groups is unreachable because `secure_route` and `ship_grain` are mutually exclusive. Layout
budget: **6 stacked verb cards**.

---

## 2. BLOCKING

### B1 — The frontend must never derive choice quantities or reconstruct choice ids

Plan lines 276–278 specify quantity toggles as formulas: `{min//2, min}`,
`{n//2, n} with n=min(inventory,150)`, `{cap//2, cap}`.

1. It recomputes what the payload already contains (`ChoiceView.quantity`), breaking "no
   economy in the frontend" (`DECISIONS 017` clause 7) inside the decision surface itself.
2. `min(inventory, 150)` **re-implements a backend bug I have just removed** (`DECISIONS 024`,
   §5). The frontend would have faithfully reproduced a lie the server no longer tells.
3. It silently diverges the moment a clamp changes, and nothing fails.

**Required:** group by `kind`; render exactly the `quantity` values present in
`available_choices`, in payload order (1 → no toggle, 2 → toggle, 3+ → N options). Measured
quantities vary run to run (`55/110`, `30/60`, `65/130`, `35/70`, `10/20`).

**Also required:** submit the **exact server-provided `ChoiceView.id`**. Never reconstruct an
id from `kind + quantity` — `buy_grain:55` is an implementation detail of the mapper, not
part of the contract.

**Falsifiable:** a mocked `available_choices` with `sell_grain` quantities `{7, 999}` must
render `7` and `999`.

### B2 — The fifth commit returns an outcome *and* a completion summary

Measured on the final response: `latest_outcome != null` **and** `completion_summary != null`
**and** `available_choices == []`.

So the obvious implementation —

```tsx
if (game.completion_summary) return <CompletionSummary />
```

— **silently skips the fifth outcome reveal entirely.** The player commits their last
decision and never sees what it did. Every AC would still appear satisfied.

**Required:** an explicit presentation phase machine, with `GameView` remaining the only
server-state source:

```
decision --commit--> reveal --Continue--> decision
                       └----(after turn 5, "Finish")----> completion
```

`decision | reveal | completion` is presentation state, not server state.

### B3 — Root pressure theming renders the drought reveal in the aftermath theme

This is an internal contradiction in **my** design direction. §1.2 says "exactly one source —
`data-pressure={pressure_stage}` on a root element", while §0.5 and §5 say the reveal must
read `latest_outcome.*`. Both cannot hold: immediately after the drought turn commits,
`latest_outcome.pressure_stage === "drought"` while top-level is `"aftermath"`. Root theming
off the top level paints the drought reveal in recovery colours — the single most important
visual beat in the run, wrong.

**Required — still one source, phase-selected:**

```tsx
const displayPressure =
  phase === "reveal" && game.latest_outcome
    ? game.latest_outcome.pressure_stage
    : game.pressure_stage;
```

then `data-pressure={displayPressure}` on the root. No per-component weather logic.

### B4 — `revision` is not `turn`, and the bug is invisible on the happy path

`GameView` carries both. Measured: they advance together through the entire normal five-turn
run and both end at `5`. So this —

```tsx
expected_revision: game.turn   // WRONG
```

— passes every Playwright run, every screenshot, every AC.

**Required:** always send `expected_revision: game.revision`; never derive it from `turn`.
**Falsifiable:** a unit test with a synthetic view where `turn = 2, revision = 7` asserting
the POST body contains `7`.

### B5 — Reveal beat 5 cites a data source that does not exist

Plan line 311 reads rivals from *"`rival_headlines` at next `turn` or stored
`RivalTurnResult`"*. `RivalTurnResult` is an **engine** type, never exposed; `OutcomeView` has
no rival field. As written the beat is unimplementable and invites invention.

The correct source is top-level `rival_headlines`, and the reason belongs in the plan:

> **Top-level `rival_headlines` is resolved-turn context, not next-decision context** —
> unlike `signal` / `world` / `pressure_stage`, which are next-decision context.

Evidence: `null` at turn 0 (nothing resolved yet); populated from turn 1; and
`completion_summary.final_rival_headlines` carries the same values at completion when no
further turn will resolve. **`GameView` mixes two context kinds at the top level** — write it
down or someone will "fix" the reveal to read the wrong thing.

**Reveal source matrix, to be stated explicitly in the plan:**

| Content | Source |
|---|---|
| turn / title / world / pressure / deltas / drivers / trace | `latest_outcome.*` |
| Mira + Daran | top-level `rival_headlines` |
| next threat (hand-off) | top-level `signal` |

### B6 — `ChoiceView.cost` cannot express "cost or proceeds", and `0` is not absent

My design direction §3 says each card shows "its cost or proceeds in coins". **The frozen API
cannot do that.** Measured: `cost` is a real number for `buy`/`expand`/`build`/`secure`,
**`0` for `hold`**, and **`null` for `sell` and `ship`**. There is no proceeds field and no
shipment revenue field. Computing proceeds in React would violate the no-economy rule.

**Required:** render `ChoiceView.label` as the authoritative action copy; show `cost` only
when non-null; never derive a missing transaction value. And test for absence with
`choice.cost !== null`, **not** `if (choice.cost)` — `hold` legitimately has `cost === 0` and
would vanish.

### B7 — `drivers` are top-three with the residual NOT represented

My design direction §5 says "top-3 + residual". **Measured across a 5-turn run,
`sum(driver.impact_money) !== wealth_delta` in 2 of 5 turns** (turn 2: `286` vs `239`;
turn 3: `263` vs `271`). The residual is genuinely unrepresented.

**Required:** no "100% explained by these three" visualization — no full-width stacked bar, no
percentage-of-total. Render the three supplied labels with their `impact_money`. Never invent
a residual client-side.

**Related, measured:** `impact_bps` is a **magnitude** (turn 3 shows `[3238, 3238, 3238]`
against `impact_money` `[263, 263, -263]`). Drive red/green from `impact_money`, never from
`impact_bps`.

### B8 — AC6 is not falsifiable as specified

Two independent properties are being conflated:

1. **UX guard** — one rapid double activation produces exactly **one** HTTP mutation.
2. **Server truth** — even if duplicates escape, only one revision wins.

The backend already guarantees (2). A frontend with **no disabling at all** would emit
`POST → 200` and `POST → 409`, leaving turn and revision each advanced once — so a test that
only checks turn/revision passes while the intended guard is entirely missing.

**Required Playwright assertion:** hold the first `/choices/` request open with an explicit
`page.route` deferred gate, fire two activations while it is in flight, then assert:

- exactly **one** `/choices/` POST left the page,
- the commit control was `disabled`/busy while pending,
- final `revision` incremented exactly once.

That is a controlled race, not a `waitForTimeout`.

**Implementation warning:** TanStack's `isPending` may not stop two clicks dispatched in the
same JavaScript turn. Use a synchronous `ref` guard in the handler (`if (committingRef.current)
return; committingRef.current = true;`) reset on settle, **in addition to** the disabled state.

### B9 — AC5 passes with a component that never updates

The `tableau()` unit test has teeth against the pure function, but this component passes it
while the browser indicator never changes:

```tsx
const initial = useRef(tableau(firstEmpire));
return <EmpireTableau tiers={initial.current} />;
```

AC5 says **visibly** changes. **Required:** a Playwright assertion around a known
empire-changing commit, asserting exact visible before/after state (`Farm capacity 5` /
"Expanded Estate" unreached → `Farm capacity 15` / reached), not
`expect(after).not.toEqual(before)`.

---

## 3. Design rulings — the vague spots, now decided

These were flagged as under-specified. I am ruling on them so nothing gets invented.

### R1 — The tableau must not imply prerequisites it does not have

The spec's example is a chain, but **the game does not enforce that order** — a player can
secure the river route before ever building a granary. Arrows would assert a tech tree that
does not exist: a modelling lie, and the exact class of error `DECISIONS 017` clause 8 blocked.

**Ruling:** keep the vertical stack (it matches the spec's "lightweight visual representation
of growth"), but **no directional arrows and no implied ordering**; reached states may be
non-contiguous. Group as three independent milestone rows:

```
Estate     Family Farm  →  Expanded Estate          (farm_capacity >= 15)
Storage    Granary  130 → 180 → …                   (storage_capacity >= 180)
Trade      River access: Closed → Secured           (route_established)
```

Each lights independently. Exact thresholds go in the plan, not "derived from gameplay
ranges" — that phrasing is an invitation to invent.

### R2 — Market card anatomy

`MarketView` has five fields and no ruling means five numbers per card — the dense readout
AC2 forbids.

**Ruling — primary screen shows exactly three, identically for both markets:**

```
Home Valley
5.000 / grain          ← primary, large, tabular
Availability   280
Demand         410
```

`base_price` and `responsiveness` do **not** appear on the primary screen this section.
`responsiveness` is an internal elasticity coefficient; "Responsiveness 40%" is meaningless to
a player.

**Copy constraint:** `supply` is an availability signal/index, **not** conserved stock
(`DECISIONS 010`). Never write "280 grain available" — write "Availability 280".

### R3 — Token split: market identity is invariant under pressure

My §1.1 says Home is *always* `--grain` while §1.2 says pressure *bleaches* the grain accent.
Those conflict, and a positive Home price tinted green would stop reading as Home.

**Ruling — two token families:**

```css
/* identity — NEVER altered by pressure */
--market-home:  #C8912F;
--market-river: #2F7B78;

/* atmosphere — pressure themes alter only these */
--page-ground, --page-rule, --world-accent, --ink
```

Layering rule: card border / title / place glyph use the market identity colour; the
**signed number itself** uses `--gain` / `--drought`.

### R4 — Route line copy

`next_margin` is computed from pre-turn prices (`mappers.py:275`) while a shipment settles
after the turn resolves both prices. It is a **quote, not a prediction**.

**Accuracy note:** the audit claims a canonical sign flip (`+597` quoted → `−588` resolved).
**I could not reproduce it** — my run went quoted `12` → resolved spread `597`, both positive.
**Treat the flip as unverified; do not repeat it as fact** in the plan or `DECISIONS.md`. The
structural point stands without it.

**Ruling:** label it **"Current route spread +0.597 / grain"**. Never "margin", "profit",
"expected", or "you will earn". Sign colouring stays as a directional cue. No backend change.

### R5 — `command_quantity` is requested, not executed

`OutcomeView.command_quantity` is the submitted command; shipment can be partially clamped.

**Ruling:** never render "You shipped 20 grain." If shown at all, phrase as "You ordered:
Ship 20". Actual executed amounts come from `domain_effects` / `drivers` / trace text.

### R6 — `price_delta` is the Home Valley price

River has its own resolved price but no second shorthand delta. Given that market identity is
load-bearing, an unlabelled "Market price +0.157" is misleading.

**Ruling:** label it **"Home price +0.157 / grain"**.

### R7 — Reveal numbers animate from zero

My §5 said "count up/down from the previous value". These fields are **deltas**.
`wealth_delta = -500` animates `0 → −500`, not `1,100 → 600` (which would need before/after
values from elsewhere).

**Ruling:** animate deltas from `0`.

### R8 — Start experience

**Ruling:** a one-screen opening with a **Begin** button, not an automatic `POST` on mount.
It gives the age/chapter label and the run seed a home, makes "Start game" in the spec's
primary flow a real beat, and avoids creating a server session for anyone who merely opens the
page.

### R9 — Age / chapter label

Required screen content with no API field. **Ruling — a presentation constant, exactly:**

```
Age of Grain · Chapter I
```

Declared in one place, commented as presentation-only. Do not synthesize it from turn or
pressure; do not omit it.

### R10 — Completion summary hierarchy

Required by the spec and currently undirected, which would yield ten fields in a grid.

**Ruling — this hierarchy (copy may be refined, structure may not):**

```
YOUR FIVE-TURN LEDGER
  Final wealth        2,345          ← hero number
  Total change        +1,245         ← signed, coloured

Final estate          Farm 25 · Storage 180 · River secured
Run record            Cash low 300 · Peak grain 180
Rivals                Mira … / Daran …
                      [ Play again ]
                      seed playtest-1 · rules 1.0
```

### R11 — Typography must be an implementable stack

"Display serif + sans" is art direction, not a system. **No webfonts** — they add a network
dependency the Playwright run and the CSP do not need.

**Ruling:**

```css
--font-display: ui-serif, Georgia, "Iowan Old Style", "Palatino Linotype", serif;
--font-ui: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
```

| role | family | size / weight |
|---|---|---|
| signal | display | 22px / 500, the largest non-title text |
| outcome title | display | 28px / 600 |
| rival headline | display | 15px / 400 italic |
| section labels | ui | 11px / 600, letterspaced, uppercase |
| body + numbers | ui | 15px / 400 |
| hero numbers | ui | 32px / 600 |

All numerals `font-variant-numeric: tabular-nums`.

### R12 — Reproduction footer needs seed **and** ruleset

A seed alone stops reproducing once rules change; the schema exposes both deliberately.

**Ruling:** `seed playtest-1 · rules 1.0`, unobtrusive.

---

## 4. Correction to the DECISIONS 023 rationale — my argument was wrong

My design direction §3 justified the deviation as *"`DECISIONS 017` is the more recent and
more specific authority."* **That is not this repo's authority order.** `BUILD_SPEC §0.2`
states precedence explicitly:

> 1. The currently active numbered build section in this file
> 2. Accepted decisions recorded in `DECISIONS.md`, if present

The active numbered section **outranks** `DECISIONS.md`. My rationale is indefensible as
written and would be dismantled by any later reviewer.

**Required reframing for `DECISIONS 023`** — the ruling itself is unchanged and correct:

> Section 11's "2–4 action buttons" cannot be implemented as 2–4 direct legal actions against
> the frozen Section 10 API, which exposes up to six simultaneous legal verbs and
> intentionally preserves two commit depths per quantity verb. Section 11 therefore interprets
> the requirement as protecting a **small, legible decision surface** rather than imposing a
> hard count on server-supplied choices. All legal choices remain directly visible; quantity
> variants are grouped within one verb control; a single explicit Commit preserves "one
> meaningful major action per turn". Recorded as an orchestrator-approved reconciliation of a
> requirement that cannot be satisfied literally, not as `DECISIONS` overriding `BUILD_SPEC`.

Rejected alternative, for the record: three category controls (Invest / Trade / Hold) hiding
the real choices behind expansion would hit "2–4" literally but makes legal actions less
legible and pushes required decision information off the main screen — a semantic loophole
that violates the same section's other requirements.

---

## 5. Context change — rebase required

Landed on this branch **after** the plan was written:

- **`DECISIONS 024` — the `sell_grain` 150 cap is removed** (`mappers.py`). Full commit is now
  actual inventory. Measured: at inventory 170 the API offered `75/150`, hiding 20 legal units
  the engine accepted. `test_sell_choices_uncapped_above_150` is mutation-proven (fails with
  the cap restored). **150 tests**, four gates green.

**Audit closeout, not Section 11 work.** Section 11 itself stays frontend-only: **no further
backend changes.** Pull before implementing; do not reintroduce `150` anywhere (B1).

---

## 6. Remaining should-fix

### S1 — Gate drift

`docs/ORCHESTRATION.md` §4 defines verification as exactly `make test && make lint && make
type && make format-check`, so after this section a completely broken frontend passes "the
gates". **Required:** keep the proposed `front-type/front-lint/front-test/front-e2e` targets,
add **`make check-all`** running everything, and list the frontend commands in `STATE.md`
**"Normal verification"** with real observed output.

### S2 — Make the e2e run deliberately cross two milestones

Commit `expand_farm` then `build_granary` early (cash 1000 → 500 → 200, both affordable) so
the tableau crosses two thresholds, then hold/sell through the drought. Makes AC5 real rather
than an accident of which choice the test clicked, and gives `final-summary.png` an empire
that visibly grew.

---

## 7. Explicitly NOT being asked for

- Renaming `next_margin` in the backend schema — copy fix is sufficient (R4).
- Remaining Sections 1–10 audit backlog (River causal parentage, CLI numeric menu, harness
  policy validation, blocked-shipment trace labels, T1–T5 test strengthening). Real, tracked
  separately, none block a correct UI.
- Any Section 12 concern; desktop two-column layout; sound; i18n; animation libraries.

---

## 8. Instruction to Muse

1. Pull the branch (`DECISIONS 024` landed).
2. Revise the plan for **B1–B9**, adopt rulings **R1–R12**, fix the `DECISIONS 023` rationale
   per §4, and address **S1–S2**. Keep everything §1 settled.
3. Implement per the revised Work Plan.
4. Gates before push: the four backend gates **and** the frontend gates, with observed output
   copied into `STATE.md`.
5. `graphify update .`; commit regenerated artifacts.
