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

---

## 5. Standing decisions (set by the product owner)

- **Fully autonomous.** Run the loop end-to-end without pausing for approval. Post to the
  ChatGPT thread freely. Push WIP section branches to GitHub each round.
- **Claude owns game-design judgment**, not just code correctness. Optimize for the best
  game at the lowest MVP complexity. Prefer the fix that removes a modelling lie or
  reduces complexity over one that adds a mechanic.
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
