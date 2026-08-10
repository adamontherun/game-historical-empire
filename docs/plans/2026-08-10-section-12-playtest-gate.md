# Section 12 — Playtest Gate Instrumentation — Plan

**Date:** 2026-08-10
**Branch:** `section/12-playtest-gate` (already created)
**Status:** DRAFT — awaiting approval (implement in same session per prompt)

## Goal

Close the one replayability gap named in the Section 12 prompt: a written observation
like "turn 3 felt arbitrary" is not actionable without the ordered committed
`choice_id`s. The app already shows `seed · rules` on screen, but the choice
sequence is recorded nowhere. Build the minimum clipboard affordance that makes a
run replayable from an observation sheet.

Per `docs/ORCHESTRATION.md` §8, Section 12 cannot be completed autonomously —
no humans have played yet. This session builds **instrumentation only**, then
Section 12 stays **BLOCKED — AWAITING HUMAN PLAYTEST** and work continues to
Section 13. The facilitator script in `docs/playtest/` is owned by the product
owner and is out of scope.

## Success Criteria

1. Frontend accumulates the ordered list of committed `choice_id`s in local
   component state as the run progresses — exact server-provided ids, same rule
   as B1, never reconstructed from `kind+quantity`.
2. Completion screen shows a **run record** containing `seed`,
   `ruleset_version`, and the ordered choice ids in one copyable line/block,
   plus a "Copy run record" button.
3. Copy uses `navigator.clipboard` with a graceful fallback that does not throw
   or log a console error when the clipboard API is unavailable (AC7).
4. The format is pasteable into an observation sheet and sufficient to replay
   the run (seed + rules + ordered ids).
5. No backend changes, no persistence, no analytics, no network calls, no
   telemetry. All state is local and discarded on reload. No new goods/turns/
   rivals/UI redesign; no touch to decision surface, outcome reveal, or tableau.
6. Tests and verification as in Validation Plan below.

## Context and Current Facts

- **Spec authority:** `BUILD_SPEC.md` §12 (line 1454) — product milestone,
  agent work begins after written playtest observations arrive; forbids
  database/auth/LLMs/more goods/turns/rivals/new age systems/large UI redesigns.
  Go/no-go criteria listed; stop condition is to iterate on existing systems
  if the loop is weak.
- **Orchestration blocker rule:** `docs/ORCHESTRATION.md` §8 — build up to the
  playtest, prepare script + instrumentation, hand over, continue to §13 rather
  than stalling.
- **Current frontend:** `frontend/src/App.tsx` — phase machine
  `start → decision → reveal → completion` (B2), `committingRef` guard (B8),
  `expected_revision: game.revision` (B4). No choice-id accumulation yet.
  `CompletionSummary.tsx` shows `seed · rules` in `data-testid="completion-seed"`
  and `run-record` (Cash low / Peak grain) — neither contains choice ids.
  `frontend/src/api/types.ts` — `GameView` has `run_seed`, `ruleset_version`,
  `ChoiceView.id` is authoritative (B1).
- **Existing tests:** `frontend/src/__tests__/*` — `decisionBlock.test.tsx`
  enforces B1 verbatim `id` handling; `e2e/critical.spec.ts` — 4 tests, full
  5-turn mobile flow (expand_farm → granary → hold → hold → hold), desktop
  smoke, AC2/AC4, B8 double-submit guard, console-error guard (AC7).
- **No backend work:** prompt hard-constraint — local component state only.

## Constraints and Non-goals

- **No backend changes.** No new endpoint, persistence, analytics, network
  calls. (Prompt hard constraint; also matches §12 forbidden list.)
- **No telemetry.** Nothing transmitted. Clipboard affordance only.
- **Do not** add goods, turns, rivals, UI redesign, or touch decision surface /
  outcome reveal / tableau (prompt + §12 forbidden list).
- **Do not** write `docs/playtest/` facilitator script (product owner does).
- **Do not** mark Section 12 COMPLETE. Its status becomes
  `BLOCKED — AWAITING HUMAN PLAYTEST` (prompt). It completes only when real
  observations arrive and the three highest-impact fixes are made.

## Key Decisions

### 1. Where to store the sequence

**Decision:** New `committedIds: string[]` in `App.tsx` via `useState`.

- Set on successful `commitChoice` (after `await commitChoice(...)` resolves) —
  push the exact `selectedId` that was sent to the server. This guarantees
  server-provided ids (B1 rule) and preserves order.
- Reset to `[]` on `handleBegin` (new game) and `handlePlayAgain` (reset to
  start screen). Discarded on reload by definition (no persistence).
- Pass down to `CompletionSummary` as a prop; no context, no global store.

**Rejected:** deriving from `GameView` (backend does not echo history),
reconstructing from `kind+quantity` (violates B1, prompt explicitly requires
failure if reconstructed), using `localStorage` (persistence not requested,
adds surface).

### 2. Run-record format

**Decision:** Single copyable line/block text containing all three parts.

Proposed format (one line, pasteable, deterministic, replay-sufficient):

```
seed=<run_seed> rules=<ruleset_version> choices=<id1>,<id2>,<id3>,<id4>,<id5>
```

Alternative equally acceptable: JSON
`{"seed":"...","ruleset_version":"...","choices":["..."]}`.
Pick one and freeze it in code + tests + e2e. The chosen format must be the
one the copy button writes and the display shows (same string).

**Why this shape:** seed + rules + ordered ids is exactly what the engine
needs to replay (`state + command + world_context + seed` per AGENTS.md §7).
Comma-separated ids preserve order unambiguously; no quoting issues for the
current id charset (`hold`, `expand_farm`, `buy_grain:55`, etc.).

### 3. Completion screen placement

**Decision:** Extend `CompletionSummary.tsx`:

- Add prop `choiceIds: string[]`.
- Compute `runRecord` string from `game.run_seed`, `game.ruleset_version`,
  `choiceIds`.
- Render a block with `data-testid="run-record-replay"` (or similar, not
  colliding with existing `run-record` which is Cash low / Peak grain) that
  contains the full `runRecord` text.
- Render a button `data-testid="copy-run-record"` labelled "Copy run record".

Keep existing `data-testid="completion-seed"` (seed·rules) for backwards
compat; the new block is the replay artefact. Do not remove existing elements
that e2e already asserts.

### 4. Clipboard with graceful fallback (AC7)

**Decision:** On click, try `navigator.clipboard.writeText(runRecord)` if
available; otherwise try a `textarea + execCommand('copy')` fallback; in all
cases `catch` swallows errors with **no `console.error`/`console.warn`** and no
throw. The handler is `async` but never rejects to the caller.

This satisfies "must not throw or log a console error if the clipboard API is
unavailable, since AC7 forbids console errors."

**Rejected:** no fallback (fails silently on older contexts), `console.error`
on failure (violates AC7).

### 5. Testing shape

- **Unit test A:** recorded sequence equals committed choice ids in order,
  using exact server ids — fails if reconstructed from kind+quantity.
  Implement as a component/helper test that asserts `formatRunRecord` or
  `CompletionSummary` renders ids verbatim and in order; include a negative
  case where `kind+quantity` reconstruction would differ (e.g. two ids with
  same kind/quantity but different suffix or exact id string).
- **Unit test B:** copy fallback does not throw and logs no console error when
  `navigator.clipboard` is undefined. Mock `navigator.clipboard` as
  `undefined`, spy on `console.error`, click the button, assert no throw and
  no error call.
- **E2E:** extend existing `e2e/critical.spec.ts` (do not add a new spec file)
  — after `expect(page.getByTestId("completion-summary")).toBeVisible()`,
  assert the run-record element is visible, contains `seed` and `rules`, and
  contains all five committed ids in order (the ids the test itself clicked).
  Keep the existing console-error/page-error guards.

## Recommended Approach

Smallest diff that satisfies the prompt — three files changed, one new test
file, one e2e extension. No new dependencies, no backend, no routing changes.

1. `frontend/src/App.tsx` — add `committedIds` state and wiring.
2. `frontend/src/components/CompletionSummary.tsx` — add `choiceIds` prop,
   `runRecord` string, display block, copy button with safe fallback.
3. `frontend/src/__tests__/runRecord.test.tsx` (new) — unit tests A + B.
4. `frontend/e2e/critical.spec.ts` — extend the completion assertions.

If a tiny helper `frontend/src/lib/runRecord.ts` with
`formatRunRecord(seed, rules, ids)` makes unit testing cleaner, add it; the
component then imports it. Prefer this if it avoids testing through DOM for
test A.

## Work Plan

**Step 1 — App state (App.tsx)**

- Add `const [committedIds, setCommittedIds] = useState<string[]>([]);`
- In `handleBegin` and `handlePlayAgain`, reset `setCommittedIds([])`.
- In `handleCommit`, after `const next = await commitChoice(...)` and
  `setGame(next)`, do `setCommittedIds((prev) => [...prev, selectedId])`
  (capture `selectedId` before it is cleared). Guard: only on success path,
  not on catch.
- In the `phase === "completion"` branch, pass `choiceIds={committedIds}` to
  `CompletionSummary`.

**Step 2 — CompletionSummary (CompletionSummary.tsx)**

- Extend props to `{ game: GameView; onPlayAgain: () => void; choiceIds: string[] }`.
- Compute `runRecord` string (chosen format) — e.g.
  `` `seed=${game.run_seed} rules=${game.ruleset_version} choices=${choiceIds.join(",")}` ``.
- Render a container (e.g. `<div data-testid="run-record-replay">` with the
  text, styled to wrap/break and be selectable). Optionally add a `<pre>` or
  `<code>` for copyability.
- Render `<button data-testid="copy-run-record">Copy run record</button>` with
  the safe clipboard handler described above. No `console.error` on failure.
- Keep existing `completion-seed` and `run-record` elements untouched.

Optional helper: extract `formatRunRecord` to `frontend/src/lib/runRecord.ts`
for unit-testability; if added, import it in `CompletionSummary`.

**Step 3 — Unit tests (frontend/src/__tests__/runRecord.test.tsx)**

- Test A: Given seed/rules and ids `["buy_grain:55","hold","ship_grain:10"]`,
  the formatted run record contains those exact ids in order; a reconstruction
  like `kind + ":" + quantity` would not equal the id for at least one case
  (e.g. `hold` has no quantity) — assert level.
- Test B: Render `CompletionSummary` with `choiceIds`, set
  `(navigator as any).clipboard = undefined`, spy on `console.error`, click
  "Copy run record", assert no throw, no `console.error` call, and the
  component remains mounted.
- Run via `vitest run` (jsdom).

**Step 4 — E2E extension (frontend/e2e/critical.spec.ts)**

- In the "completes 5-turn game on mobile" test, after
  `await expect(page.getByTestId("completion-summary")).toBeVisible()`,
  add:
  - `await expect(page.getByTestId("run-record-replay")).toBeVisible()` (or
    chosen test id)
  - `await expect(page.getByTestId("run-record-replay")).toContainText(seed)`
    and `rules` (read from `completion-seed` or known pattern)
  - Collect the five ids the test committed (expand_farm, build_granary,
    hold, hold, hold — or whatever the actual committed ids are) and assert
    they appear in order in the run-record text. One robust way: read the
    textContent of the run-record element and assert
    `text.indexOf(id1) < indexOf(id2) < ...`.

Do not add a new spec file.

**Step 5 — Gates, graphify, commit, push**

- `make check-all` (backend `test/lint/type/format-check` + frontend
  `front-type/front-lint/front-test/front-e2e` via Makefile) plus
  `npx playwright test` (same as `front-e2e`) — paste observed output into
  `STATE.md` per AGENTS.md §15 freshness contract.
- `graphify update .` and commit regenerated `graphify-out/` artifacts.
- Update `STATE.md` (header, What exists, Boundaries if changed, Normal
  verification / Last known green with actual output, file tree) and
  `BUILD_SPEC.md` Section 12 status to `BLOCKED — AWAITING HUMAN PLAYTEST`
  (not COMPLETE).
- Commit and push `section/12-playtest-gate`.

## Validation Plan

| Check | Command | Expected evidence |
|---|---|---|
| Backend gates | `make test && make lint && make type && make format-check` | 150+ passed, 0 checks, 0 errors, formatted |
| Frontend type/lint | `make front-type && make front-lint` | 0 errors, 0 problems |
| Frontend unit | `make front-test` or `vitest run` | New tests pass (A + B), total 27–28 passed |
| E2E critical path | `npx playwright test` (mobile + desktop) | 4 tests pass, run-record assertions pass, no console errors |
| Full | `make check-all` | All green |
| Manual | Load app, play 5 turns, verify completion shows seed/rules/choices line and Copy button works; with `navigator.clipboard = undefined` in devtools, click Copy — no throw, no console error | Visual check |

Highest-risk validation: the e2e order assertion — ensure it actually fails if
ids are reconstructed or out of order, and that the run-record element is the
one asserted (not the old `run-record` Cash-low element).

## Risks / Rollback

- **Risk:** Copy fallback logs to console → AC7 failure (e2e console-error
  guard). Mitigation: `try/catch` with no `console.*`, tested in unit test B.
- **Risk:** E2E asserts wrong choice ids (e.g. assumes `hold` but actual flow
  commits a different qty). Mitigation: assert on the ids the test actually
  committed (or assert order via indexOf on the live text, not hard-coded
  assumptions about buy quantities which may vary by state).
- **Risk:** STATE.md freshness drift (AGENTS.md §15). Mitigation: update
  STATE.md in the same commit as code, copy actual gate output verbatim.
- **Rollback:** All changes are additive local state + UI; reverting the
  commit restores previous completion screen. No migration, no data loss.

## Open Questions

- None — scope is fully specified in the prompt. Format choice (line vs JSON)
  is the only minor decision; either satisfies "pasteable and sufficient to
  replay" as long as seed + rules + ordered ids are present and tested.

## Non-goals (explicit)

- Facilitator script (`docs/playtest/`) — product owner writes it.
- Any economy, content, or UI redesign beyond the run-record line + button.
- Backend, DB, auth, LLM, telemetry, persistence.
