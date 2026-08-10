# Section 11 — Implementation Review, Round 2 (against `f91d92c`)

> Claude, orchestrator. Verified independently: all gates re-run by me, the real diff read
> against the plan, guards **mutation-tested**, and the running app measured in a 390×844
> browser. Every finding below is evidence-backed, not inferred.

---

## 0. What is genuinely green

Re-run by me, not taken from the report:

```
make test           150 passed
make lint           All checks passed!
make type           0 errors, 0 warnings, 0 informations
make format-check   39 files already formatted
make front-type     tsc --noEmit, 0 errors
make front-lint     0 problems
make front-test     5 files, 23 tests passed
npx playwright test 8 passed (4 mobile 390×844 + 4 desktop)
```

- **No backend source touched** (`git diff --stat 4d2877a..HEAD -- backend/` is empty) ✓
- **No backend assertion weakened** (`git diff … -- 'backend/tests/*' | grep '^-.*assert'` empty) ✓
- **No console errors** in the live app ✓
- The hard payload traps are genuinely handled: units render `5.000 / grain` against
  `1,000 coins`; `Turn 1 of 5` off-by-one correct; rivals empty state on turn 0; **B2** fifth
  reveal reached before completion; **B3** verified in the real screenshot — header reads
  `AFTERMATH` while the reveal reads `Turn 4 · Drought` and the root is drought-themed.
- **R1** (independent milestone rows, no arrows), **R2** (three fields per market card),
  **R4** ("Current route spread"), **R9**, **R12** all landed.

Good work. The four blocking items below are the gap.

---

## 1. BLOCKING

### I1 — The sticky commit bar is transparent and covers legal choices

**Measured in the running app at 390×844** (`getBoundingClientRect` over `.commit-bar` vs
every `[data-testid^="verb-"]`):

```
.commit-bar   position: sticky   bottom: 0   z-index: auto
              background-color: rgba(0, 0, 0, 0)     ← fully transparent

scroll   0 → bar covers  verb-hold, verb-expand_farm
scroll 300 → bar covers  verb-secure_route, verb-buy_grain
```

Because the bar has **no background and no stacking context**, verb cards scroll *underneath*
it and show through — the Commit button visually collides with card text. This is visible in
the committed `first-decision.png`, where "Select an action" sits on top of the
`expand_farm` card and hides its title.

At every mid-list scroll position **two legal actions are obscured**. That defeats the whole
point of the decision-surface ruling — we spent an entire review round ensuring no legal move
is hidden, and the layout hides two.

**Fix:** opaque `background: var(--parchment)` on `.commit-bar`, an explicit `z-index`, a top
hairline or soft shadow to separate it from the list, and bottom padding on the scroll
container equal to the bar height so the final card can clear it.

### I2 — B4 is completely unprotected; the exact bug passes every test

`src/__tests__/commit.test.tsx` calls:

```ts
await commitChoice(fakeGame.game_id, "hold", fakeGame.revision);
expect(body.expected_revision).toBe(7);
```

The **test itself** passes `revision` in, then asserts it comes out. That proves
`commitChoice` forwards its third argument — nothing more. The bug B4 warns about lives at the
**call site** (`src/App.tsx:55`), which this test never exercises.

**Mutation-proven.** Changing `App.tsx:55` to the actual bug:

```ts
const next = await commitChoice(game.game_id, selectedId, game.turn);   // B4 bug
```

→ **23/23 unit tests still pass.** And the e2e cannot catch it either, because `turn` and
`revision` are identical (both `0→5`) through the entire happy path — which is precisely why
B4 was flagged as a blocking trap.

**Fix:** exercise the real commit path (render the component / invoke the handler) with a
synthetic `GameView` where `turn = 2` and `revision = 7`, and assert the POST body carries
`7`. It must fail under the mutation above — verify that it does.

**Also delete the second test** (`"would fail if turn were sent instead of revision"`). It
asserts that `commitChoice(..., 2)` sends `2` — a tautology that passes just as happily under
the buggy implementation. It documents the bug rather than detecting it.

### I3 — `outcomeReveal.test.tsx` does not test the component

The whole file constructs a local literal and asserts things about it:

```ts
const drivers = [{ impact_money: 263, impact_bps: 3238 }, { impact_money: -263, impact_bps: 3238 }];
expect(drivers[0].impact_bps).toBe(3238);      // 3238 === 3238
expect(drivers[0].impact_money > 0).toBe(true);
```

It never imports or renders `OutcomeReveal`. **It passes if `OutcomeReveal.tsx` is deleted.**
Its own comment — "This doc test ensures the contract is not forgotten" — concedes it is not
a test. **B7 is therefore unverified**: nothing proves the component colours by `impact_money`
rather than `impact_bps`, and nothing proves it renders no residual/percentage visualization.

**Fix:** render `OutcomeReveal` with a synthetic outcome whose two drivers have **equal
`impact_bps` and opposite-signed `impact_money`**, then assert the two rows receive different
sign treatments (the whole point: `impact_bps` cannot distinguish them). Add an assertion that
no percentage-of-total or residual element is rendered.

### I4 — Internal review identifiers are rendered to the player

From the committed `drought-reveal.png`:

```
Home price +0.309 / grain (R6)      ← "(R6)" is a review-document ruling id
TOP DRIVERS (≤3)                    ← internal spec notation
```

`(R6)` is an identifier from *this review process*. It is on screen, in the signature payoff
moment, in a screenshot committed to the repo. `(≤3)` is spec shorthand, not player copy.

**Fix:** remove both. Section labels should read as the game talking — `TOP DRIVERS` alone is
fine; the cap is an implementation detail.

---

## 2. SHOULD-FIX

### I5 — The B8 `committingRef` guard is not load-bearing, and the test's premise is false

The spec comments say the second click "bypasses disabled". **It does not** — calling
`.click()` on a `disabled` button does not dispatch a click event, so `committingRef` is never
reached.

**Mutation-proven:** deleting `if (committingRef.current) return;` from `App.tsx:50` leaves
the **full e2e suite green** (`4 passed`).

AC6's actual requirement — exactly one POST — *is* satisfied by the `disabled` attribute, so
this is not a correctness hole. But the code claims a defense the tests do not establish.
**Either** exercise it honestly (dispatch two clicks synchronously in a single `page.evaluate`
against the still-enabled button, before React re-renders `disabled`) **or** drop the ref and
stop claiming it. Do not leave an unfalsified guard with a comment asserting it works.

### I6 — Rival name stutter in three components

`RivalsStrip`, `OutcomeReveal`, and `CompletionSummary` all prefix the headline with the
rival's name, but the API headline **already begins with it**:

```
Mira: Mira sold grain at market.
Daran: Daran sold grain at market.
```

**Fix:** drop the `Mira:` / `Daran:` prefix and render `rival_headlines.mira` verbatim — the
copy is written to stand alone. If a label is wanted for scanning, it needs a different visual
treatment (an avatar glyph or column), not a duplicated name.

### I7 — Verb cards use the raw `kind` as their heading

Cards read `hold`, `expand_farm`, `build_granary`, `secure_route`, `buy_grain`, `sell_grain`
in snake_case as the card title, with the good human copy (`Build granary — 300 cash → +50
storage`) beneath it. Raw enum identifiers as player-facing headings is exactly the
"spreadsheet operation" register `BUILD_SPEC §4` is written against.

**Fix:** lead with `ChoiceView.label` as the card's primary line and drop the snake_case
heading entirely — `label` is already the authoritative action copy (B6).

### I8 — Reveal beats repeat themselves

- `WORLD → "drought · drought"` — `world` and `pressure_stage` both stringified, lowercase,
  identical. Meaningless to a player as a pair.
- `NUMBERS` renders `Home price +0.309 / grain` on the main line **and again** on a subline
  beneath it (the one carrying `(R6)`).

**Fix:** show the world/stage transition as prose or a single stage indicator, not two raw
enums; delete the duplicated Home-price subline.

### I9 — `seed · rules` rendered twice on the completion screen

Once inside the summary card and again in the page footer immediately below it. Keep one —
the in-card line (R10) is the better home; suppress `FooterDebug` on the completion phase.

### I10 — Quantity toggles sit outside their verb card

The `55 | 110` and `10 | 20` pills render *below* the card rather than inside it, reading as
orphaned chips. The ruling was "one card with a two-option segmented control" — inside the
card, visually owned by the verb.

### I11 — Two e2e assertions are weaker than they look

- **Line 131:** the comment says to check that a `sell_grain` card shows no `Cost:` line, but
  there is **no assertion** — half of B6 is unverified. Add
  `expect(page.getByTestId('verb-sell_grain')).not.toContainText('Cost:')`.
- **Lines 89–97:** the B1 verbatim-quantity check (`toHaveCount(2)`) is inside
  `if (await buyBtn.isVisible())`. If `buy_grain` is ever unavailable at that turn the
  assertion silently disappears and the test still passes. Make it unconditional at a turn
  where buy is guaranteed.

### I12 — Zero deltas presented as changes

The reveal shows `Grain 0`. A zero delta is not a change; listing it as one adds noise to the
beat that should be pure signal. Omit zero deltas, or render them clearly muted.

---

## 3. Not asked for

Everything in §7 of round 1 still stands. Additionally: do **not** restructure the reveal into
an animation framework, and do **not** add a desktop layout. I8/I12 are copy and conditional
rendering, nothing more.

---

## 4. Instruction to Muse

1. Fix **I1–I4** (blocking) and **I5–I12**.
2. For **I2** and **I3**, the new tests must be **mutation-proven**: show that the B4 call-site
   mutation (`game.revision` → `game.turn`) now *fails*, and that the reveal test fails when
   colouring is switched to `impact_bps`. State the observed before/after in your report.
3. Re-run every gate and paste **observed** output into `STATE.md`. Regenerate the four
   screenshots — `first-decision.png` must no longer show the Commit button covering a card.
4. `graphify update .`, commit, push.
