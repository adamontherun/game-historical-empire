# Section 10 plan — consolidated review (round 2)

Round 1's B1–B3 and B5–B7 are correctly addressed in the revised plan; I verified each in the
document rather than taking the summary on trust. **B4 was partly wrong and is corrected
below.** The second reviewer then found two blockers neither of us had, both confirmed against
the code.

The organising principle, which should go in DECISIONS verbatim:

> **Section 10 exposes engine capabilities; it does not decide strategy.**
> `available_choices` is a transport/presentation projection of valid command verbs, not a
> recommendation engine. Harness policies never influence player authorization. The API
> supplies economic values and explanations so the frontend does not calculate them, but the
> player remains free to make economically bad, contrarian, or anticipatory decisions.

---

## C1 — Correction to round 1's B4: `OperationState` is not invented

Round 1 claimed `operations: list[{id, kind, capacity, level}]` was invented structure, on the
basis of a grep returning zero hits. **That grep was wrong** — it searched for the lowercase
field name and the word `level`, not the type. `OperationState` exists:

```
backend/app/domain/types.py:40   class OperationState(BaseModel)
  id: str          # "Stable operation id, e.g. 'farm_1'"
  kind: Literal["farm", "granary"]
  capacity: Quantity
  level: int = 1   # "Visible scale level"
```

So Muse mirrored a real domain type, not an invention. The round-1 reasoning was wrong.

**The conclusion still stands, for a different and better reason.** `types.py:59` records that
`OperationState` "exists as a standalone type for future Section 5 use" — it is a **dormant
type, deliberately not embedded in `PlayerState`**, precisely to avoid duplicate sources of
truth. The canonical empire today is `farm_capacity`, `storage_capacity`,
`route.established`. Having the API mapper synthesize `farm_1` / `granary_1` with invented
`level` values would turn a dormant type into fictional canonical-looking state and create a
second source of truth for capacity — worse than inventing a new shape, because it would look
authoritative.

The revised plan's `empire_summary: {farm_capacity, storage_capacity, route_established}` is
correct. Keep it. Record the *reason* as "dormant type, single source of truth", not "type does
not exist".

## C2 — Correction to round 1's B2 reasoning (conclusion unchanged)

Round 1 argued `?trace=1` violated the three-endpoint spec. It does not — a query parameter on
`GET /api/v1/games/{game_id}` is still that same endpoint. Drop that argument.

The conclusion is unchanged and rests on three sound reasons: it prematurely optimizes an
**unmeasured** payload; it creates **two shapes of `GameView`** for the same resource; and it
returns `drivers[*].causal_node_ids` while potentially **omitting the very nodes those IDs
identify**, which makes the reveal unresolvable. Global §14 makes the trace first-class output
and §9 makes the reveal a signature interaction. Latest turn's trace inside `latest_outcome`,
unconditionally — as the revised plan now has it.

---

## C3 — NEW BLOCKER: `completion_summary: StrategicSummary` smuggles a history endpoint into `GameView`

Verified at `prototype.py:137`:

```python
class StrategicSummary(BaseModel):
    initial_state: GameState
    final_state: GameState
    history: tuple[TurnResolution, ...]     # ALL FIVE turns, each with a full causal_trace
    final_wealth / initial_wealth / wealth_delta_total / cash_low / peak_inventory / is_complete
    final_rivals: tuple[RivalState, RivalState] | None
    rival_history: tuple[tuple[RivalTurnResult, RivalTurnResult], ...] | None
```

Returning this directly on turn 5 ships the **entire game history, including five complete
causal traces and the full rival history**, inside `GameView`. Section 10 explicitly excludes a
history endpoint — and this is a history endpoint by another name. It also flatly contradicts
B2's own "latest turn only, not all five" decision: the plan would carefully return one trace
in `latest_outcome` and then five more in `completion_summary`.

**Fix:** define an API-owned `CompletionSummaryView` carrying only what an end screen needs —
`initial_wealth`, `final_wealth`, `wealth_delta_total`, `final_cash`, `final_grain`,
`final_farm_capacity`, `final_storage_capacity`, `cash_low`, `peak_inventory`, `is_complete`,
and optionally final rival headlines as pre-rendered strings. **No `initial_state`, no
`final_state`, no `history`, no raw rival states.**

Add a test asserting the serialized `GameView` at turn 5 contains no `history` key and no
nested `TurnResolution` beyond `latest_outcome`.

## C4 — NEW BLOCKER: current-turn context and latest-outcome context are conflated

After the drought turn resolves, top-level `signal`, `pressure_stage`, and `world` describe the
**next** turn (aftermath) — because the mapper derives them from `pressure_for_turn(len(history))`
— while `latest_outcome` describes the **just-completed drought** turn. A client rendering the
reveal immediately after a POST would show "Aftermath" context next to a drought result, with
no linkage between them.

This is a real legibility bug, and it is exactly the kind that becomes load-bearing once
Section 11 builds the reveal screen on top of it.

**Fix:** `OutcomeView` must carry its own context — `resolved_turn`, `title`, `pressure_stage`,
`world`, and the **submitted command and quantity** — alongside `drivers`, `domain_effects`,
and `causal_trace`. Top-level `signal`/`pressure_stage`/`world` then unambiguously mean "the
decision you are about to make"; `latest_outcome.*` means "the decision you just made".

Add a test: after submitting on the drought turn, assert
`latest_outcome.world == "drought"` while top-level `world` is the aftermath value, and that
`latest_outcome.resolved_turn` is the turn that was just submitted.

## C5 — `GET` must take the same per-session lock, or it can return a torn view

Round 1 said "per-session lock or justify global". Sharper: the plan has `GET` reading without
the lock ("no lock needed for read-only"). That is wrong — the mapper walks
`state`, `history`, and `rivals` while building the view, so a concurrent `POST` can mutate
them **midway through mapping** and produce a response mixing pre- and post-turn values.

Use a **per-session** `asyncio.Lock` owned by `GameSession`; both `choose()` and `get_game()`
acquire it. Unrelated games then proceed independently, which also removes the global
serialization concern.

## C6 — Test dependencies are missing

Verified `backend/pyproject.toml` dev dependencies contain only `pytest>=9.0.2` — **no
`httpx`, no `pytest-asyncio`**. The planned `test_concurrent_same_revision_one_wins` uses
`asyncio.gather` against async handlers, and `TestClient` needs `httpx`. Add both explicitly
rather than relying on transitive resolution, and prefer a genuine async client over
`TestClient` concurrency gymnastics for that one test.

## C7 — Cleanup confirmations

- Drop `revision_history` from `GameSession` — no requirement, no consumer, and it smells like
  persistence scaffolding for Section 16. (Round 1 B7; restated because it is still listed.)
- `created_at` is harmless; keep or drop, but do not add anything else speculative.
- Keep `turn_limit` derived from `prototype.TURN_LIMIT` — especially since Section 14 expands
  the game to 10–12 turns, so a hardcoded 5 has a known expiry date.

---

## Work items

1. **C3** — replace `completion_summary: StrategicSummary` with an API-owned
   `CompletionSummaryView` containing only end-screen values. Add the "no history in GameView"
   test.
2. **C4** — move turn context into `OutcomeView` (`resolved_turn`, `title`, `pressure_stage`,
   `world`, submitted command + quantity). Add the drought/aftermath linkage test.
3. **C5** — per-session `asyncio.Lock` on `GameSession`; **both** `choose()` and `get_game()`
   acquire it.
4. **C6** — add `httpx` and `pytest-asyncio` to dev dependencies.
5. **C7** — drop `revision_history`.
6. **C1** — keep `empire_summary` as the three concrete fields, but correct the stated reason:
   `OperationState` exists and is deliberately dormant and not embedded in `PlayerState`;
   synthesizing operations would create a second source of truth for capacity.
7. Record the "Section 10 exposes engine capabilities; it does not decide strategy" principle
   in `DECISIONS.md` alongside the two-quantity choice decision.

Once C3–C6 are reflected, the plan is approved for implementation. The architecture outside
these issues is right: API-owned schemas and mappers outside `domain`/`engine`, exactly three
routes, in-memory sessions, optimistic revision, `game.submit()` as the only turn-mutation
path, reverse-dependency purity tests, and no DB/auth/LLM work.
