# Section 10 plan — consolidated review (round 1)

The plan is strong. K3 (revision atomicity), K5 (purity guard extended to `alembic` and the
reverse `app.api` import), and Q4 (API rejects unknown `choice_id`; the engine bounds
affordability, no double-implementation) are all correct and well-evidenced. The self-grill
did real work — Q3 and Q5 in particular.

Every factual claim I spot-checked in the plan is accurate: `test_engine_purity.py:8`'s
forbidden set is exactly as quoted (and does *not* cover `alembic` or `app.api`),
`available_commands()` is at `prototype.py:307`, `submit()` at `:336`, `StrategicSummary` at
`:137`, `turn_limit` at `:211`.

**One blocking item (B1), then smaller ones.**

---

## B1 — BLOCKING: the plan makes the balance harness's scripted policies into the player's only legal moves

`available_choices` policy, plan lines 186–193:

```
build_granary  if inventory + farm*YIELD > storage and cash >= 300 and turn < 4
buy_grain:N    if N > 0 and turn in (1, 2)
sell_grain:N   if turn == 4 and inventory > 0
secure_route   if not established and cash >= 400 and turn == 0
ship_grain:N   if established and inventory > 0 and river - transport - home > 0
```

Those conditions are not engine rules. They are lifted from `harness.py`'s *scripted policies*
— the turn numbers are literally `policy_storage_heavy`'s and `policy_trade_heavy`'s. Verified
against the engine:

- `FiveTurnGame.available_commands()` (`prototype.py:307`) returns all seven verbs
  **unconditionally**, with no turn gating whatsoever.
- `resolve_turn` accepts any verb on any turn; affordability is clamped inside
  `actor.resolve_*` with an `insufficient_*` reason code, never refused by turn index.

So as planned, a player **cannot buy grain except on turns 1–2, cannot sell except on turn 4,
and cannot build a granary at all on turn 4**. Consequences:

1. **It deletes the decisions the game is about.** BUILD_SPEC §4 wants strategic allocation
   choices and §5 wants one meaningful major action per turn. "When to buy" and "when to sell
   into the peak" are among the most meaningful choices in this economy — Section 9 showed
   sell timing is worth ~284 wealth on its own. Hard-coding the timing hands the player the
   answer.
2. **It silently invalidates Section 9.** The balance result says no strategy dominates *given
   that a player may choose freely*. If the API only permits the moves the three scripted
   policies make, the player cannot express any fourth strategy, and "no dominant strategy"
   becomes unfalsifiable — it would be true by construction because alternatives are
   unreachable.
3. **It is the harness leaking into the product.** The harness's job was to *evaluate* the
   economy by simulating competent play. Those heuristics are a measuring instrument, not
   game rules.

**Required change.** `available_choices` must be derived from **legality and affordability
only** — the same conditions the engine would not reject outright — never from turn index or
from what a scripted policy would consider wise:

- `hold` — always.
- `expand_farm` — `cash >= EXPAND_FARM_COST`.
- `build_granary` — `cash >= BUILD_GRANARY_COST`. Any turn.
- `secure_route` — `not route.established` and `cash >= ROUTE_ESTABLISH_COST`.
- `buy_grain:N` — any turn, if `N > 0` where `N` is affordability/headroom-bounded.
- `sell_grain:N` — any turn, if `inventory > 0`.
- `ship_grain:N` — `route.established` and `inventory > 0`. **Do not gate on margin > 0** —
  shipping at a loss is a legal move and a real mistake the player is allowed to make; the
  drought peak makes it loss-making by design, and hiding it removes the lesson. Surface
  `next_margin` in `route_status` so the player can see it is negative and decide.

Add a regression test: `available_choices` at a fixed cash/inventory state must be **identical
across turn indices** except where an engine-level precondition genuinely changed
(`route.established`). That is the falsifiable form of "the API adds no rules of its own",
and it would fail today's plan.

**Quantity is a separate question, and worth one deliberate decision.** The plan offers a
single server-chosen quantity per verb (line 336: "Do not offer 3–4 quantity buckets"). I
agree a continuous slider is wrong (§4 forbids exact-quantity micromanagement), but exactly
one server-picked amount removes the depth-of-commitment decision, which Section 9 showed
matters a great deal (scaled buys were the difference between a strawman and a competent
policy). **Offer two per quantity verb — a partial and a full commit** (e.g.
`buy_grain:40` / `buy_grain:80`). That preserves "how deep do I commit" while keeping the
choice list at ~6–8 items and staying well clear of spreadsheet-tuning. This is a design call,
not a spec requirement; record it in DECISIONS.

---

## B2 — The causal trace must not be behind a debug flag or a query param

Plan line 111 and line 337 make the trace `debug_trace`, optionally behind `?trace=1`,
"if it bloats the payload".

- Global rule **§14** makes the causal trace a **first-class output**, not a debug aid.
- Global rule **§9** makes Outcome Reveal a **signature interaction** — the trace *is* the
  reveal, and Section 11 will build that screen from it.
- The spec lists exactly three endpoints with no query parameters. `?trace=1` adds surface
  the spec did not authorize.
- The bloat concern is unmeasured. A turn's trace is on the order of 40–60 nodes. Measure it
  before optimizing it away; if a single turn's trace is genuinely too large, that is a
  finding worth reporting, not a reason to hide it by default.

Put the latest turn's full `causal_trace` inside `latest_outcome`, unconditionally. Do not
return all five turns (no history endpoint in this section) — just the latest.

## B3 — The AC4 test has one vacuous step and one circular step

Step 4 (plan line 127): "test greps that Section 11's future client imports only `GameView`
JSON, never `backend/app/engine/*.py`". **Section 11 does not exist**, so this step passes
against nothing. This is an unfalsifiable criterion wearing a test's clothes — the exact
pattern that cost this project three rounds in Section 8. Delete it.

Step 2's `wealth == cash + grain*price//1000` assertion is **circular as evidence for AC4**:
it proves the response's fields are internally consistent, and it does so by *writing an
economic formula into the test* — the very thing AC4 says a client should never need. Keep it
if you want a consistency check, but label it as such. It is not AC4 evidence.

**What AC4 actually needs** is a completeness check, not a recomputation: assert that every
number Section 11's decision screen must display is present as a field. Concretely — for each
of the 5 turns, assert the response contains, without arithmetic: current wealth, cash,
inventory, both prices, route status with `next_margin`, each choice's rendered label *and*
its cost, the wealth delta, and the ranked drivers with their `impact_money` and
`reason_code`. If a value can only be obtained by multiplying or dividing two response fields,
AC4 is not met and the field is missing.

## B4 — `empire_summary.operations` is invented structure

Plan line 101 proposes `operations: list[{id, kind, capacity, level}]` with a `name_stage`.
Nothing resembling `operations`, `kind`, or `level` exists anywhere in `domain/` or `engine/`
— I grepped; zero hits. The empire is currently exactly three concrete things:
`farm_capacity`, `storage_capacity`, and `route.established`.

Global rule §15: "Do not design a universal mechanism merely because a future age might need
it. Create abstractions after at least two concrete use cases reveal a shared pattern."
Map `empire_summary` to the three fields that exist. A generic operations list is Section
13/14 shape being built four sections early.

## B5 — Internal contradiction: `run_seed` is required for reproduction but absent from `GameView`

K6 and Q6 both say the server mints a `run_seed` when the client omits one and **echoes it**
so the game is reproducible. But the `GameView` schema in K4 (lines 92–113) has `game_id` and
no `run_seed` field. As specified, a client that omits the seed can never learn it, and
`test_determinism_same_seed_same_choices` only works because it passes the seed explicitly.

Add `run_seed: str` to `GameView`. Keep it distinct from `game_id` as K6 says.

## B6 — `next_margin` should be one engine helper, not a third copy of the same expression

`river_price - transport_cost - home_price` will now exist in three places: inlined in
`policy_trade_heavy`, post-hoc as `arbitrage_margin` (`turn.py:1297`), and newly in the API
mapper. Three copies of an economic formula is how they drift.

Extract one pure helper in the engine (e.g. `actor.ship_margin(river_price, transport, home_price)`)
and have the harness policy, `turn.py`, and the mapper all call it. This keeps economic
formulas in the engine where global rule §10 (Simulation Authority) wants them, and the API
mapper stays a mapper. Small, and it directly serves AC4's spirit.

## B7 — Smaller items

- **Lock type must be decided, not "or".** Plan K3 says `asyncio.Lock` "(or `threading.Lock`
  …)". Pick `asyncio.Lock` and make the handlers `async def`; the planned
  `asyncio.gather` concurrency test only exercises the race under that combination. Note the
  reasoning honestly: with `async def` handlers and no `await` between check and mutate, the
  operation is already atomic under a single-threaded event loop — the lock is defensive
  belt-and-braces against a future `await` sneaking in between them. That is a fine reason to
  keep it; state it rather than implying the race exists today.
- **A single global lock serializes every game.** Fine for an in-memory MVP, but make it a
  per-session lock or write down why global is acceptable, so Section 16 does not inherit a
  bottleneck by accident.
- **`turn_limit: int = 5`** (line 96) hard-codes a constant that already lives at
  `prototype.py:211` as `TURN_LIMIT`. Derive it. A duplicated constant in the view layer is a
  small instance of exactly what AC4 forbids.
- **`revision_history` on `GameSession`** (line 80) is never read anywhere in the plan. Cut
  it — no history in this section.
- **Game-complete status code**: plan says "`409` or `400` … prefer `409` consistently;
  document one". Decide: `409`, documented, with `detail: "game complete"`.
- **`GET` on unknown `game_id`** → `404` is covered in Slice 2; also assert it in a test.

---

## Keep as-is

- K3's revision-on-the-envelope design (`revision` distinct from `GameState.turn`), `+1` only
  on successful mutation, `409` for stale, `422` for a missing field.
- K5's extended purity guard — `alembic` plus the reverse `from app.api` check. This is the
  Section 8 shim lesson correctly institutionalized.
- Q4's split: unknown `choice_id` → `404`; short cash/storage → `200` with the engine's
  `insufficient_*` reason in the trace. Do not re-validate affordability in the API.
- Q10's stable string `choice_id`s over integer indices, and the rule that the client copies
  `available_choices[*].id` verbatim and never synthesizes one.
- The hard rule that the API calls `game.submit()` only, never `resolve_turn` as well.
- No SQLAlchemy/Alembic/auth/LLM/history/deployment, and no frontend scaffolding.

## Work items

1. **B1** — rebuild `available_choices` from legality + affordability only; delete every turn-index
   condition and the `margin > 0` gate on `ship_grain`. Add the turn-invariance regression test.
   Offer two quantity options (partial / full) per quantity verb; record in DECISIONS.
2. **B2** — `causal_trace` for the latest turn inside `latest_outcome`, unconditional. No
   `?trace=1`, no `debug_trace`. If you believe payload size is a real problem, measure it and
   report the number.
3. **B3** — delete AC4 test step 4; relabel the recomputation assertion as a consistency check;
   add the field-completeness assertions that actually test AC4.
4. **B4** — `empire_summary` maps to `farm_capacity`, `storage_capacity`, `route.established`.
5. **B5** — add `run_seed` to `GameView`.
6. **B6** — one pure `ship_margin` helper in the engine; call it from the harness policy,
   `turn.py`, and the mapper.
7. **B7** — decide the lock, per-session or justified global; derive `turn_limit`; drop
   `revision_history`; fix the game-complete code to `409`; test `404` on unknown `game_id`.

No implementation until B1 and B2 are resolved in the plan — they change the shape of
`GameView` and of the mapper.
