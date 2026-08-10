# Audit — Sections 1–10, Consolidated Review Round 2

> Claude's independent verification of round 1 (`c9e1ddf`, `0e69cbe`) against
> `docs/plans/2026-08-10-audit-sections-1-10-review-round-1.md`.
> Gates re-run by me, not taken from the completion report.

## Verified good — round 1 genuinely fixed these

Gates, run independently at `0e69cbe`:

```
make test          149 passed          (was 148; +1 net, no test deleted — 148 -> 149 test functions)
make lint          All checks passed!
make type          0 errors            (strict, and it really is strict now — see R1 caveat)
make format-check  39 files formatted  (was 40; demo.py deleted)
```

- **No assertion was weakened.** All three removed assertions were replaced with *stricter* ones —
  notably `assert "buy_grain:30" in ids or "buy_grain:60" in ids` became
  `assert "buy_grain:40" in ids and "buy_grain:80" in ids` (`or` → `and`).
- **B2 ship: fully fixed.** Re-ran my original divergence script: API now offers `[10, 20]` against
  an engine max of 20 — **0% hidden**, was 80%.
- **B3a: genuinely falsifiable now.** I removed the lock myself (keeping the yield) and observed
  `FAILED test_concurrent_same_revision_one_wins — 1 failed, 14 passed`. The lock has teeth.
- **B4, S0a, S0b, S0c, S1, S2, S3, S4, S5, S7, S8** land as specified.
- **`app/` strict is real.** I injected `x: int = "definitely not an int"; return x + None` into
  `app/engine/rounding.py` and the gate produced 4 errors. It catches things.

---

## R1 — BLOCKING. The type-gate fix excluded the test suite from type checking entirely.

`backend/pyproject.toml` now sets `include = ["app"]`. That does not mean "tests at standard" — it
means **tests are not analyzed at all**.

**MEASURED:**

```
filesAnalyzed: 22        (was 39 — the 17 test files are gone)

injected into backend/tests/test_sanity.py:
    def test_injected_type_error() -> int:
        x: int = "definitely not an int"
        return x + None
$ make type
0 errors, 0 warnings, 0 informations      <-- gate does not see it

same injection into backend/app/engine/rounding.py:
$ make type
4 errors                                   <-- gate does see it
```

Round 1 authorized two options: *fix the 359 test errors*, or *scope so `backend/app` is strict and
`backend/tests` is `standard`*. `include = ["app"]` is a third option — strictly weaker than the
status quo ante, because before the fix tests were at least analyzed in basic mode.

This is the audit's own failure mode reappearing inside the audit fix: a gate that reports green
over a narrower surface than its documentation claims.

**Compounding doc error.** Both `STATE.md:73` and `DECISIONS.md` 018's Consequence line state
`0 errors ... (39 files, app only)`. The real number is **22**. `AGENTS.md §15` requires
`Last known green` to match observed output.

**Fix.**

```toml
[tool.pyright]
typeCheckingMode = "strict"
include = ["app", "tests"]

[[tool.pyright.executionEnvironments]]
root = "tests"
typeCheckingMode = "standard"

[[tool.pyright.executionEnvironments]]
root = "app"
typeCheckingMode = "strict"
```

Then clear whatever `standard` reports for `tests` (far fewer than the 359 that `strict` reported —
`standard` does not emit `reportUnknown*`, which was 371 of the 406). Prove the gate covers tests by
re-running the injection above and observing it fail. Correct DECISIONS 018 and `STATE.md` to the
real file count.

---

## R2 — SHOULD-FIX. Buy is still capped by a harness-policy constant, which DECISIONS 017 forbids.

B2's buy half is only partially fixed. Re-running my original script:

```
API offers max buy       : 80
engine would accept up to: 110   (space=110, affordable=200)
engine resolve_buy(requested=110) -> actual=110 cost=550 reason=buy_grain
=> API hides 30 legal units (27% of legal buy range)      [was 45%]
```

The remaining gap is `min(space, affordable, 80)` at `api/mappers.py`.

I initially read the `80` as an unjustified magic number and was wrong — it is traceable.
**That makes it a worse problem, not a better one.** `DECISIONS.md:97` introduced it as harness
*policy* buy-sizing ("All buys now `min(space, max_affordable, 80)` not hardcoded 10/20"), and
`DECISIONS.md:104` repeats it for `policy_storage_heavy`. It is a **scripted-bot strategy constant**.

`DECISIONS 017` (`DECISIONS.md:112`, clause 1) states the governing rule verbatim:

> **Harness policies never influence player authorization.**

So the player's maximum legal purchase is currently set by a number chosen to make the balance bots
behave. This is the same category error as the `turn == 4` gating that was blocked at Section 10
plan review — a strategy heuristic acting as an authorization rule — expressed as a magnitude
instead of a turn index. Round 1 removed the harvest-reservation half of exactly this problem and
left the cap half in place, then documented the cap with a rationale that points at the harness.

Note the new test bakes the cap in: `assert max_buy == 80, f"buy max {max_buy} != 80 (engine space 110)"`
— the failure message itself records that the engine allows 110.

**Fix.** Remove the `80` from `choices_for` so the full commit is `min(space, affordable)` = 110 at
the start state, and update `test_choices_engine_agreement_unclamped` to assert the offered max
equals the *engine* max rather than the capped max. The harness policies keep their own `80` — that
is legitimate, it is their strategy. If a presentation cap is genuinely wanted so the list stays
readable, it must be justified on presentation grounds and recorded as such, and it must not be
sourced from harness tuning.

---

## R3 — SHOULD-FIX. A production `await` was added to serve a test; make it a documented decision.

`api/service.py` gained `await asyncio.sleep(0)` inside the lock in **both** `get_game` and `choose`,
with the comment `# B3a: yield inside lock so concurrent interleaving is observable; simulates
future DB await and makes lock falsifiable`.

It works — I verified the lock is now falsifiable. And there is a real argument for it: without a
yield the lock is inert, so the choice was between deleting the lock and making it load-bearing, and
Section 16 will need the lock. That is a defensible call.

Two problems with how it landed:

1. **It is a design commitment recorded only as a code comment referencing an audit finding id.**
   "B3a" is an artifact of this review document, meaningless to a future reader. Someone will
   reasonably delete a no-op `sleep(0)` and silently un-falsify the test — the exact regression this
   audit just fixed. It needs a DECISIONS entry ("the per-session lock is load-bearing; an explicit
   yield point inside the critical section keeps it so until real I/O lands") and a comment that
   references the decision, not the audit.
2. **The `get_game` yield is unprotected.** No mutation covers it — removing only that one leaves
   the suite green. Either add a test that a GET cannot observe a torn view mid-mutation, or drop
   the yield from `get_game` and keep it only in `choose` where a test constrains it.

---

## Not carried forward

- N1 (`OperationState`, `event_exposure`, `regional_output` defaults) and N3 (rival personality
  double-mechanism) — round 1 deferred these as Section 11+ scope. **Agreed, correctly scoped.**
  N1 in particular should not be touched: deleting a dormant domain type is a schema decision, not
  an audit cleanup.

## Work order

1. **R1** — restore test coverage to the type gate; prove it with the injection; fix the "39 files"
   claim in both `DECISIONS.md` 018 and `STATE.md`.
2. **R2** — drop the harness-sourced buy cap; retarget the agreement test at the engine max.
3. **R3** — DECISIONS entry for the lock yield; protect or remove the `get_game` yield.

Same rules as round 1: no test weakened, mutation evidence required for anything claiming to be
falsifiable, no Section 11 work, `STATE.md` updated in the same commit with real gate output.
