# Section 12 — First Human Playtest: Facilitator Script

> **This section cannot be completed by the coding agent.** `BUILD_SPEC §12` is a *product*
> milestone: it needs real people playing and saying what they expected. Everything the agent
> could build is built. What remains is one or more human sessions run from this script.
>
> Run 3–5 players. Budget ~25 minutes each. Then hand the filled observation sheets back to
> the agent, which will classify them and fix **only the three highest-impact problems**.

---

## 1. Before you start

**Setup**

```bash
make check-all          # confirm green
cd backend && PYTHONPATH=. uv run uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

Open `http://localhost:5173` on a **phone**, or in a desktop browser at a 390×844 viewport.
A real phone is strongly preferred — mobile usability is one of the things under test.

**Recruit players who have not seen this game.** A player who has watched someone else play,
or who has heard you explain the economy, cannot answer question 1 honestly.

**The one rule for you, the facilitator:** *do not explain the game.* Not the markets, not the
drought, not what the buttons do. If the player asks "what does securing the river route do?",
write the question down and say "what do you think it does?". Go/no-go criterion 1 is
**"a fresh player completes the run without developer explanation"** — every explanation you
give invalidates that criterion for that session.

Silence is data. Confusion is data. Let it happen.

---

## 2. The three questions

Ask these verbatim. Do not paraphrase, do not lead.

**Before each of the 5 decisions:**

> What do you expect will happen, and why?

**After each outcome reveal:**

> Why do you think that happened?

**At the very end, after the completion summary:**

> Did you want one more decision?

That last one is the single most informative question in the whole session. Ask it, then say
nothing and let them answer fully.

**Also note, without asking:** where they scrolled back to, what they re-read, what they
tapped that wasn't tappable, where they hesitated, and anything they said unprompted.

---

## 3. Observation sheet

One per player. Copy this block.

```
PLAYER ___   DATE ___   DEVICE (phone model / browser) ___
RUN RECORD (copy from the completion screen — button is on the final screen):
___________________________________________________________________

TURN 1  (normal — "The growing settlement keeps food demand high")
  Expected before:
  Chose:
  Explanation after:
  Correct causal read?   yes / partly / no

TURN 2  (early_dry — "the rains have begun to fail")
  Expected before:
  Chose:
  Explanation after:
  Correct causal read?   yes / partly / no
  Did they notice the warning?   yes / no

TURN 3  (worsening_dry — "Farmers warn the next harvest is at risk")
  Expected before:
  Chose:
  Explanation after:
  Correct causal read?   yes / partly / no
  Did they change behaviour because of the warning?   yes / no

TURN 4  (drought — "Drought cuts farm output")
  Expected before:
  Chose:
  Explanation after:
  Correct causal read?   yes / partly / no
  Did the drought feel earned or arbitrary?   earned / arbitrary

TURN 5  (aftermath — "Markets adjust")
  Expected before:
  Chose:
  Explanation after:
  Correct causal read?   yes / partly / no

END
  "Did you want one more decision?"  →
  Did they mention Mira or Daran unprompted at any point?   yes / no
  Did a rival change a decision?   yes / no  — which turn:
  Did the empire feel bigger at the end?   yes / no
  Did they open "Show the full chain"?   yes / no  — did it help?
  What was their strategy, in their words:

VERBATIM QUOTES (most useful artifact — capture exact wording):
  -
  -
  -

FRICTION LOG (scrolling, mis-taps, hesitation, re-reading, anything broken):
  -
  -
```

---

## 4. Classification — do this after each session, while it is fresh

`BUILD_SPEC §12` requires every observation to be classified into exactly one of these. Tag
each line of your notes:

| tag | means |
|---|---|
| `decision-clarity` | they didn't understand what a choice would do |
| `consequence-clarity` | they didn't understand what just happened or why |
| `strategic-depth` | the choice felt obvious, pointless, or one-dimensional |
| `rival-legibility` | Mira/Daran were noise, invisible, or misread |
| `empire-growth` | growth felt absent, invisible, or unearned |
| `mobile-usability` | layout, tap targets, scrolling, text size |
| `pacing` | too slow, too fast, too long, over too soon |
| `technical-defect` | it is broken — a real bug |
| `deferred-feature-request` | "it should also have X" — **record and do not build** |

The last tag is a trap for the unwary. Most player suggestions are `deferred-feature-request`
and `BUILD_SPEC §12` explicitly forbids acting on them. A player asking for more goods, more
turns, or more rivals is usually reporting a *depth* problem in the systems that already exist.
Log the request, then classify the underlying feeling.

---

## 5. Go / no-go

Tally across all players. Proceed to Section 13 only when **most** are true.

| # | criterion | met? | evidence |
|---|---|---|---|
| 1 | Fresh player completes the run with no developer explanation | | |
| 2 | Before committing, player can describe a plausible expected outcome | | |
| 3 | After resolution, player can explain the primary causal chain | | |
| 4 | At least three strategic approaches feel defensible in some state | | |
| 5 | A rival changes at least one player decision | | |
| 6 | The empire feels larger at the end | | |
| 7 | The drought feels consequential but not arbitrary | | |
| 8 | Players disagree about the best strategy | | |
| 9 | At least some players want to continue | | |

Criteria 4 and 8 need **multiple** players — a single session cannot establish either. If you
only run one player, mark them "insufficient data" rather than guessing.

**If the loop is not working, stay in Section 12 and iterate on the systems that exist.**
`BUILD_SPEC §12`: *"Do not advance by adding features to hide a weak decision loop."*

---

## 6. Handing back to the agent

Give the agent the filled sheets and say roughly:

> Here are N playtest observation sheets for Section 12. Classify every observation per
> `BUILD_SPEC §12`, identify the three highest-impact problems, fix only those three, and
> re-run the go/no-go tally.

The agent will then, per the spec: classify → rank → fix exactly three → re-verify. It will
**not** add goods, turns, rivals, a database, auth, LLMs, new ages, or a large UI redesign,
because Section 12 forbids all of them unless one is literally required to fix a critical
blocker.

---

## 7. What is already true, so you needn't test for it

Verified by the agent; do not spend session time here:

- The five-turn run completes on mobile 390×844 and on desktop, with zero console errors.
- Every turn's reveal shows wealth / inventory / price deltas, up to three ranked drivers, and
  the full causal chain behind a collapsed disclosure.
- Rivals are on screen every turn (with an explicit empty state before they have acted).
- The empire indicator crosses two thresholds in a normal investing run.
- A committed action cannot be double-submitted.
- Prices display as coins-per-grain, correctly scaled from the engine's milliunits.

What is **not** verified, and is exactly what this playtest is for: whether any of it is
*understood*, and whether anyone wants a sixth turn.
