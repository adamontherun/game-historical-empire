# Orchestration Guide — how BUILD_SPEC sections get built

> **Purpose:** hand-off doc so a fresh Claude Code session (or a human) can pick this up
> and continue without re-deriving the process. Read this plus `STATE.md` and
> `BUILD_SPEC.md` and you have everything.

Three participants:

| Who | Role |
|---|---|
| **Claude Code** | Orchestrator. Reviews, reconciles, verifies gates independently, merges, owns design calls. |
| **Muse Code** (Meta) | Implementer. Plans and writes all the code, driven headlessly. |
| **ChatGPT** | Second independent reviewer, in a long-running browser thread with full project history. |

---

# ⚠️ STAGE DISCIPLINE — READ BEFORE ANYTHING ELSE

**This is a POC. The goal is to get a playable game in front of humans, not to perfect one.**

Every rule further down this document is subordinate to that sentence. The loop, the gates, and
the verification discipline exist to keep the thing *correct and shippable* — not to make it
optimal. When rigor and shipping conflict at this stage, ship.

## The failure mode this section exists to prevent

In Section 13 the orchestrator spent three review rounds tuning economic constants so that a
200-seed scripted-policy harness would produce a particular rank ordering. It succeeded. The
cost: the epilogue ended up destroying **24–38% of wealth for three of four strategies**, best
case **+0.7%** — a wealth tax instead of a hook. A ranking no human would ever see was optimized
until the actual game got worse.

The product owner's words: *"this feels like a tweak on a highly mature product, not the push to
launch a game and test it."*

## Rules

1. **Prove the mechanism, don't tune the distribution.** Making an acceptance criterion
   falsifiable is right. Reaching for a heavy statistical instrument to arbitrate it is often
   wrong. One deterministic scenario test that shows *the thing happens* beats a multi-seed
   sweep that tunes *how often it happens*. Ask: "what is the smallest test that would fail if
   this mechanism didn't exist?" — then write that one.
2. **If a metric only moves by making the product visibly worse, the metric is wrong.** Stop
   and say so. Do not keep tuning. This is the single clearest signal that a proxy has been
   mistaken for the goal.
3. **Separate structural design fixes from balance knobs.**
   - *Structural* — e.g. giving the scarce resource to the strategy that did **not** dominate,
     making an old mastery not transfer, deleting a "legacy" that everyone earns. **Do these
     now.** They are the actual design content.
   - *Balance* — exact prices, decay curves, thresholds, yields. **Defer these until humans have
     played.** Tuning them without human signal is guessing with extra steps.
4. **A blocked human-feedback gate is a reason to SHIP, not to substitute more machine
   measurement.** Section 12 is blocked on real players. That makes getting there faster the
   priority. It does not license replacing human judgment with a harness.
5. **Two rounds on a balance question is the limit.** If an acceptance criterion has not been
   satisfied after two rounds of numeric tuning, it is the wrong criterion *for this stage*.
   Downgrade it to a mechanism test, record honestly what is proven and what is deferred, and
   move on. Do not spend a third round.
6. **"Good enough to learn from" is the bar.** A player finding the epilogue slightly
   unbalanced is a *successful playtest*. A player never seeing the epilogue because it is
   still being tuned is a failure.

## What this does NOT relax

Stage discipline is about **scope and polish**, never about honesty:

- Gates still all pass. Tests are never weakened or deleted to move faster (`BUILD_SPEC §0.4`).
- Falsifiability still matters — a *smaller* test, not a *fake* one.
- Silent omissions are still the worst outcome. Under-deliver openly; never over-claim.
- `STATE.md` and `DECISIONS.md` must say plainly what is proven and what is deferred. "Deferred
  until playtest" is a fine thing to write. "AC met" when it isn't, is not.

---

## 1. The loop, per section

```
1. Muse:    /skill plan  ->  docs/plans/<date>-section-N-<slug>.md
2. Muse:    /skill grill on its own plan (headless: it answers its own questions)
3. Claude:  independent review against BUILD_SPEC + the real code
   ChatGPT: independent review (in parallel — push the branch, give it the URL)
4. Claude:  RECONCILE both into ONE consolidated doc:
            docs/plans/<date>-section-N-review-round-K.md
5. Muse:    revise plan -> repeat 3-4 until no blocking items
6. Muse:    implement + gates + STATE.md + DECISIONS.md + graphify + commit/push
7. Claude:  re-run gates INDEPENDENTLY, review the real diff
   ChatGPT: review the pushed branch
8. Claude:  reconcile -> one fix instruction -> repeat until clean
9. Claude:  merge to main, fresh Muse session for the next section
```

Reconciliation is a real step, not a relay. Claude decides what actually goes back to
Muse: dedupe overlapping findings, resolve disagreements, and **drop anything that is
scope creep into a later section** (BUILD_SPEC §31 forbids building ahead).

---

## 2. Driving Muse headlessly

Muse Code is at `~/.local/bin/muse`. Everything runs through `muse exec` from Bash.

```bash
MUSE=/Users/adamsmith/.local/bin/muse
SID=$(uuidgen)          # ONE session id per BUILD_SPEC section
echo "$SID" > /path/to/scratchpad/s<N>_session.txt

"$MUSE" exec --yolo \
  --model muse-spark-1.2-contributor \
  --reasoning-effort high \
  --session-id "$SID" \
  --prompt-file /path/to/prompt.txt
```

Run it with `run_in_background: true` — these take minutes.

**Verified mechanics:**

- **`--session-id` gives true multi-turn continuity.** Reuse the same UUID across separate
  `muse exec` calls and Muse remembers the whole conversation. This is what lets
  plan → grill → revise → implement → fix all share one context, exactly like the
  interactive TUI. Use a **fresh** id per section.
- **Slash commands work headlessly.** `/skill plan`, `/skill grill` etc. inside the prompt.
- **`grill` normally interviews a human.** Headless, instruct Muse to write out its own
  decision-forcing questions, answer them from code/computed evidence, and mark anything
  genuinely product-owner-level as `ESCALATE`. This works well — it caught two real bugs
  in its own Section 8 plan unaided.
- **There is no `goal` skill** in this build. `/goal` is a TUI-only command. Not needed:
  one `--session-id` per section already provides the continuity.
- **Shell alias gotcha:** `muse` is aliased to `muse --yolo`, which breaks subcommand
  parsing (`muse skills list` fails). Call the full binary path for subcommands.
- `--json` emits structured JSONL events if you need to inspect a run programmatically.

---

## 3. Driving ChatGPT

Long-running thread, already has full project history:
`https://chatgpt.com/c/6a789e14-f2a0-83e8-a101-e01cc66e5e7b`

Use the **`mcp__claude-in-chrome__*`** tools (real Chrome, already logged in) — *not* the
in-app browser, which has no session. `browser_batch` for click/type/Return in one call.

- **ChatGPT reads GitHub branch URLs directly** and reviews real code. This is far better
  than pasting diffs, so **push the section branch before asking for review**.
- Reading its reply: `get_page_text` is reliable. The `javascript_tool` route sometimes
  trips a content filter; screenshots work as a fallback. The DOM is virtualized, so a
  stale `lastLen` usually means you're looking at an old message — scroll to the bottom.
- It reasons for 1–5 minutes at Extra High. Do other work meanwhile, don't block.
- **Correct it if you gave it a bad premise.** Its review is only as good as the framing.

---

## 4. Verification discipline (non-negotiable)

- **Always re-run the gates yourself.** Never merge on Muse's completion report alone.
  ```bash
  make test && make lint && make type && make format-check
  ```
- **Read the diff against the plan.** Gates cannot catch a planned step that was silently
  skipped — this happened in Section 8 (the CLI stage display was never implemented while
  the report said COMPLETE with all checks PASS).
- **Check that assertions weren't weakened.** After a change that moves numbers:
  ```bash
  git diff <base>..HEAD -- 'backend/tests/*' | grep '^-.*assert'
  ```
  Updating an expected number because the economy intentionally changed is legitimate.
  Deleting an assertion, loosening an equality, or removing a test is not (BUILD_SPEC §0.4).
- **Prefer measuring over arguing.** Several of the biggest findings came from running the
  real engine in a throwaway script rather than reasoning about it. Do that.
- **But measure to answer a question, not to tune a distribution.** This rule has a failure
  mode: it reads as "more measurement is always better", and it is not. Measure to find out
  whether something is *true* (does the mechanism exist? is this test falsifiable? does this
  claim hold?). The moment you are re-running a sweep to nudge a number toward a threshold, you
  have left verification and entered balance tuning — see **Stage Discipline** at the top of
  this document, and stop after two rounds.

---

## 5. Standing decisions (set by the product owner)

- **Fully autonomous.** Run the loop end-to-end without pausing for approval. Post to the
  ChatGPT thread freely. Push WIP section branches to GitHub each round.
- **Claude owns game-design judgment**, not just code correctness. Optimize for the best
  game at the lowest MVP complexity. Prefer the fix that removes a modelling lie or
  reduces complexity over one that adds a mechanic.
- **Ship the POC; do not perfect it.** The priority is a playable game in front of humans.
  Design authority is authority to make a call and move on — not a licence to iterate on
  numbers until they are ideal. Make the call, write down why, ship it, and let the playtest
  argue back. See **Stage Discipline** at the top of this document.
- **After Section 10 completes, pause for a full-codebase audit** (consistency, quality,
  bugs across Sections 1–10) using this same loop, *then* continue to Section 11.
- **When UI sections arrive (11, 20), actively drive visual design and consistency** —
  give real style direction, not just correctness review. Muse's `/skill taste` is one
  input, not the whole answer.

---

## 6. Recurring failure patterns to watch for

These have each bitten more than once:

1. **Tests that pass for the wrong reason.** The worst offenders compare two things that
   differ in more than the one variable under study. Section 8's AC1/AC3 test needed three
   rounds: first it would have passed with the feature deleted; then its two arms diverged
   *before* the warning existed; then one arm changed farm capacity, so the two runs
   weren't even facing the same drought. Always ask: *what confound could make this pass
   spuriously, and what rules it out?*
2. **Silent omissions.** A planned step skipped while the report says COMPLETE. Diff the
   plan against the work.
3. **Unfalsifiable acceptance criteria.** "No dominant strategy" means nothing until you
   state the operational pass/fail rule.
4. **Compatibility shims that reopen a closed door.** Section 8 removed the bare-`world`
   API, then a `PressureState | str` shim quietly reinstated it. Watch for "backward compat"
   that undoes the section's own thesis.
5. **Docs drifting from reality.** `STATE.md` claiming behavior the code cannot produce.
   Re-verify handoff docs against observed output, not against intent.
6. **Optimizing a proxy until the product gets worse.** Section 13: three rounds of tuning
   economic constants to flip a rank ordering in a 200-seed harness, ending with an epilogue
   that took 24–38% of the player's wealth. The harness was a *proxy* for a feel question, and
   the human gate that would have answered it properly (Section 12) was blocked. **Tell:** you
   are re-running a sweep to nudge a number toward a threshold, and the product is degrading as
   the number improves. **Fix:** stop, downgrade the criterion to a mechanism test, record what
   is deferred, ship. See **Stage Discipline**.
7. **Rigor applied at the wrong altitude.** Related but distinct from #6: the work is correct
   and well-tested, but it is the wrong work *for this stage*. Before a deep pass on any
   number, ask whether a human has ever seen this system. If not, that is the next task.

---

## 7. Where things live

```
BUILD_SPEC.md                     implementation authority; section Status lines
STATE.md                          handoff snapshot — must match reality
DECISIONS.md                      durable decisions (numbered)
AGENTS.md                         binding repo rules (graphify, git safety, conventions)
docs/plans/<date>-section-N-*.md  plans + consolidated review rounds
docs/ORCHESTRATION.md             this file
```

Branch per section: `section/<N>-<slug>`, merged to `main` with `--no-ff` when green.
Run `graphify update .` after touching `backend/` or `docs/` (required by `AGENTS.md`) and
commit the regenerated `graphify-out/` artifacts.

---

## 8. Known upcoming blockers

- **Section 12 — First Human Playtest.** Requires real humans playing and reporting
  expectations vs. outcomes. Cannot be completed autonomously. Build up to it, prepare the
  playtest script and instrumentation, hand it over, and continue to Section 13+ rather
  than stalling.
- **Section 19 — Authentication.** Requires a deliberate 13+ vs. reviewed child-privacy
  decision before public release. Implement and document; the product owner ratifies.
