# Section 10 implementation — review round 3

Implementation verified independently: `148 passed`, ruff clean, pyright `0 errors`, format
clean. No assertion was removed or weakened (`git diff` over `backend/tests/*` shows no deleted
`assert`). Engine purity holds — zero `fastapi` or `app.api` references under `engine/` or
`domain/`. C3, C4, C5, C6, C7 all landed and the C3/C4 tests are genuinely discriminating.

**One blocking defect**, found by mutation testing rather than by reading.

## D1 — BLOCKING: `test_available_choices_turn_invariant` cannot detect the defect it exists for

This is the guard for B1, the section's blocking finding. I re-introduced the exact original
defect — `build_granary` gated on `turn < 4` — into `choices_for`, and **the test still passed**.

Cause: the test compares only two sampled turn indices, `0` and `3`
(`test_api.py:352-355`). Any gate whose boundary does not fall between those two is invisible.
Against the four gates the original plan actually had:

| original defect | present @0 | present @3 | caught by {0,3} | caught by 0..4 |
|---|---|---|---|---|
| `build_granary if turn < 4` | yes | yes | **no** | yes |
| `buy_grain if turn in (1,2)` | no | no | **no** | yes |
| `sell_grain if turn == 4` | no | no | **no** | yes |
| `secure_route if turn == 0` | yes | no | yes | yes |

The test catches **one of four**, and misses the three that motivated B1 in the first place.
This is orchestration failure pattern #1 — a test that passes for the wrong reason — sitting on
top of the most important invariant in the section.

**Fix:** sweep **every** turn index `0..TURN_LIMIT-1` and assert all produce an identical
choice-id set, rather than sampling two. Then re-run the mutation above and confirm the test
**fails**; a guard that has never been observed failing is not yet a guard.

## D2 — Secondary

- `test_api.py:333` fakes history with `g._history = [None] * n`, poking a protected attribute
  with values of the wrong type. It happens to work because `choices_for` only reads
  `session.game.state`, but it is fragile and it type-lies. Prefer building the differing turn
  indices through real `submit()` calls on a state contrived so cash/inventory/route do not
  move, or pass the turn index into `choices_for` explicitly if that is cleaner.
- `test_api.py:133-135`: `assert '"history"' not in raw or raw.count('"history"') == 0` — both
  sides of the `or` are the same condition. Reduce to the single clear assertion; the following
  key checks are the ones doing real work.
