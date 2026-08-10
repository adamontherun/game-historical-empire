# Audit — Sections 1–10, Consolidated Review Round 1

> **Reconciled by Claude** from three independent passes: Claude (measurement-first),
> Muse (`docs/plans/2026-08-10-audit-muse-findings.md`), and ChatGPT (branch review).
> Mandated by `docs/ORCHESTRATION.md` §5: full-codebase audit after Section 10, before Section 11.
>
> Baseline verified independently at `audit/sections-1-10`:
> `148 passed` · `ruff All checks passed!` · `pyright 0 errors` · `40 files already formatted`.

## How to read this

Every finding below is either **MEASURED** (a script was run, observed output pasted) or
**PROVEN** (exhaustive enumeration) or **REVIEW** (read-only judgement). Nothing is speculation.
Findings are ranked by what they cost us if we carry them into Section 11.

Scope discipline: no finding proposes Section 11+ work. `BUILD_SPEC §31` forbids building ahead.
No fix weakens, loosens, or deletes a test (`BUILD_SPEC §0.4`).

---

## BLOCKING

### B1 — `make type` has never run pyright in strict mode. The type gate is not the gate we think it is.

**MEASURED.** `Makefile:11` runs `uv run --project backend pyright` **from the repo root**.
Pyright resolves configuration from the *current working directory*, not from `--project`.
There is no `pyrightconfig.json` and no root `pyproject.toml`, so the
`[tool.pyright] typeCheckingMode = "strict"` block in `backend/pyproject.toml:31` is **never loaded**.
The gate has been running in default *basic* mode for all ten sections.

```
$ uv run --project backend pyright            # what `make type` does, from repo root
0 errors, 0 warnings, 0 informations          # filesAnalyzed: 39

$ cd backend && uv run pyright                # same 39 files, config actually loaded
406 errors, 0 warnings, 0 informations        # filesAnalyzed: 39
```

Same 39 files both times — the difference is purely the strictness setting.

Breakdown of the 406:

| area | errors |
|---|---|
| `backend/app/` | 47 |
| `backend/tests/` | 359 |

| top rule | count |
|---|---|
| `reportUnknownMemberType` | 165 |
| `reportUnknownVariableType` | 131 |
| `reportUnknownArgumentType` | 75 |
| `reportUnusedVariable` | 9 |
| `reportUnusedImport` | 6 |
| `reportUnknownParameterType` | 6 |
| `reportUnusedFunction` | 4 |

`app/` errors by file: `api/mappers.py` 23, `engine/rivals.py` 9, `domain/pressure.py` 7,
`engine/turn.py` 4, `api/sessions.py` 1, `cli.py` 1, `engine/harness.py` 1, `engine/prototype.py` 1.

**Why blocking.** `AGENTS.md §8` states "**`pyright` strict**. These are Section 1 gates — CI fails on
violations." `BUILD_SPEC` Section 1 lists strict typing as an acceptance gate. `STATE.md` reports
`make type → 0 errors` as evidence of health. All three describe a gate that has not been enforced
since Section 1. This is the same class of defect as ORCHESTRATION §6.2 (silent omission) but at
the gate level: it silently un-verifies every section's type claims.

It also directly explains the untyped-parameter and `dict[str, object]` patterns in
`api/mappers.py` (below) — those would not have survived a strict gate.

**Fix.** Make the gate load the config it claims to use, then clear the errors it surfaces:

1. `Makefile`: `type: cd backend && uv run pyright` (or add `pyrightconfig.json` at the root that
   includes `backend` and sets `typeCheckingMode = "strict"`).
2. Fix the **47 `app/` errors** — these are production code and must be clean.
3. For the 359 test errors: fix them, or scope strictness so `backend/tests` runs at `standard`
   while `backend/app` runs `strict`. Do **not** silence with blanket `# type: ignore`.
4. Update `STATE.md` `Last known green` with the real post-fix numbers.

This is a prerequisite for the other fixes — several findings below are things strict mode reports.

---

### B2 — The API hides legal moves from the player. `choices_for` models the coming harvest for `buy` and ignores it for `ship`, under-offering in both directions.

**MEASURED.** `available_choices` is documented in `STATE.md:7` and `api/mappers.py:45` as
"**Legality + affordability ONLY (B1). No turn gating, no margin>0 gating.**" It is not.

**Buy** — `api/mappers.py:87-89` reserves room for a *full normal* harvest:

```python
headroom = s.player.storage_capacity - (
    s.player.inventory.grain + s.player.farm_capacity * YIELD_PER_CAPACITY
)
```

At the real default start state:

```
start state: cash=1000 grain=20 farm=5 storage=130 price=5000
API offers max buy       : 60
engine would accept up to: 110   (space=110, affordable=200)
engine resolve_buy(requested=110) -> actual=110 cost=550 reason=buy_grain
=> API hides 50 legal units (45% of the legal buy range)
```

The engine's `resolve_buy` clamps on `storage_capacity - inventory` (110) at *command* time.
Reserving harvest room is a **strategy judgement** — "don't buy grain the harvest will overflow" —
exactly the class of rule DECISIONS 017 and the Section 10 review round 1 removed from this
function. It is also wrong under drought, where harvest is 60%, so it over-reserves hardest in the
turn where buying matters most.

**Ship** — `api/mappers.py:122-123` caps on *pre-harvest* inventory:

```python
cap = min(s.player.inventory.grain, s.route.capacity)
```

But `TURN_ORDER` settles harvest **before** shipment
(`... command -> production -> ... -> settlement -> route_settlement -> ...`), so the engine ships
from post-harvest inventory:

```
inventory at decision time = 4, farm_output = 200
inventory when shipment settles = 130   (harvest lands BEFORE shipment)
API offers ship quantities : [2, 4]
engine would ship up to    : 20   (route capacity 20)
=> API hides 16 shippable units (80%)
```

So the mapper **assumes the harvest will land when computing `buy`, and assumes it will not when
computing `ship`** — two different models of the same turn, in adjacent blocks of one function,
both under-offering.

**Why blocking.** Section 9 spent four review rounds and a retune making trade a viable archetype
(route repays +174, 43.5% on its 400 cost). Through the API a player cannot express a full load.
This is the exact principle ChatGPT and the product owner blocked the Section 10 plan on —
"Section 10 exposes engine capabilities; it does not decide strategy" (DECISIONS 017, verbatim in
`STATE.md:46`) — reintroduced through arithmetic instead of through `if turn == ...`. It bakes into
the UI contract right before Section 11 builds on it.

**Fix.**
- `ship`: `pre_ship = min(storage_capacity, inventory + farm_output_estimate)`, then
  `cap = min(pre_ship, route.capacity)`. Use `actor.compute_farm_output(farm_capacity, world)` so the
  estimate respects drought instead of raw `farm_capacity * YIELD_PER_CAPACITY`.
- `buy`: clamp on the engine's actual rule, `storage_capacity - inventory`, via
  `actor.affordable_quantity` for the cash side. If we *want* to keep a harvest-aware suggestion,
  it belongs in a separate advisory field, not in what the player is allowed to submit — and that
  is a Section 11 presentation decision, not this audit's.
- Replace the inlined affordability formula at `mappers.py:92` with `actor.affordable_quantity`
  (see C1).
- Add a test asserting: for each verb, the largest offered quantity is one the engine resolves
  **unclamped** (`actual == requested`) from the same state. That test fails today for both verbs.

---

### B3 — Two acceptance tests are non-falsifiable. Both survive deletion of the feature they name.

**MEASURED by mutation.** Not read-only judgement — each mutation was applied, the suite run, and
the source restored.

**B3a — the per-session lock is untested.** `tests/test_api.py:196`
`test_concurrent_same_revision_one_wins` is the only evidence for `STATE.md:45`'s claim that the
per-session `asyncio.Lock` "prevents torn views".

```
MUTATION: delete `async with session.lock:` from BOTH get_game and choose (service.py:44, 52)
RESULT:   14 passed
```

The whole suite still passes with the lock entirely removed. The reason is structural: the critical
section in `choose()` contains **no `await`**, so under asyncio it is already atomic — the lock
cannot be observed to do anything. The `[200, 409]` outcome the test asserts is produced by the
revision check alone.

The lock is not *wrong* — it is correct insurance for Section 16, when a DB `await` lands inside
that block. The defect is the test claiming to prove something it cannot, and `STATE.md` reporting
that claim as verified.

**B3b — price movement is untested.** `tests/test_invariants.py:44`
`test_bounded_price_monotonic_with_supply`:

```
MUTATION: make _bounded_price return current_price unconditionally (never move)
RESULT:   1 passed
```

The test only asserts `p_low >= p_high` and never asserts the price *moves*, so a completely inert
price function satisfies it. Lines 53-56 also contain a dead loop
(`for _supply in reversed(supplies): pass`) with an unresolved comment (`# start low supply?`).

**B3c — `test_secure_route_creates_trade_access` has a tautological assertion.**
`tests/test_two_markets_route.py:336-338` (found by Muse, confirmed):

```python
assert (
    res2.next_state.player.cash == res2.next_state.player.cash
)  # no further cost aside from possibly 0
```

`x == x`. The stated intent — "Second secure when already established should not charge again" — is
not tested. Making the second `secure_route` charge 400 again would not fail this test. (The
following `reason_code == "already_established"` assertion does have teeth, so the behaviour is
partially covered; the cash claim is not.)

**B3d — the balance harness never checks that it measures the swing.** *(raised by ChatGPT,
confirmed by mutation.)* `tests/test_balance_harness.py:98` `test_largest_swing_bounded` only asserts
upper bounds (`<= 2500`), which `0` satisfies trivially. Its own comment admits it:
`# we trust harness, but check it is not huge`.

```
MUTATION: harness.py:378  largest_swing=largest  ->  largest_swing=0
RESULT:   148 passed
```

The entire suite passes with the swing measurement disabled.

ChatGPT additionally flagged that the price-envelope check omits the initial→Turn-1 transition. On
inspection `test_balance_harness.py:83-94` does read `max_movement_bps` from state and has no `+500`
loosening (both were fixed in Section 9); the remaining gap is only the first transition. Minor —
folded into the B3d fix.

**Fix (strengthen, never weaken).**
- B3d: recompute the expected swing in the test from `per_seed` wealth deltas and assert
  **equality** with the reported `largest_swing`, plus at least one seed where the swing is
  non-zero. Extend the envelope check to cover the initial→Turn-1 transition.
- B3a: force a yield inside the critical section in the *test* (e.g. an `await asyncio.sleep(0)`
  seam the test can exercise) so removing the lock produces `[200, 200]` and `revision == 2`. If a
  genuinely falsifiable async test is not achievable without contorting production code, then
  relabel the test to what it actually proves (optimistic revision rejects the stale writer) and
  correct `STATE.md:45` to stop claiming the lock is verified.
- B3b: delete the dead loop; add a strict assertion that the price actually moves, e.g.
  `assert _target_price(5000, 20, 120, 5000) > _target_price(5000, 200, 120, 5000)` and at least one
  `p_low > p_high` pair.
- B3c: `assert res2.next_state.player.cash == res.next_state.player.cash`.

---

### B4 — Rival headlines report total failure on partial fills. The rival sold, and the game says it didn't.

**MEASURED** (raised by ChatGPT, verified independently). `HEADLINES_BY_REASON`
(`engine/rivals.py:168`) keys only on `reason_code`, so any partially-filled command reads as a
complete failure:

```
PARTIAL SELL: rival inventory before = 5, requested sell = 10
   after          : cash=1025  (was 1000, so +25 == 5 units sold at 5000 milli)
   cash_delta     : 25
   reason_code    : insufficient_inventory
   headline       : 'Mira wanted to sell grain but had insufficient grain.'
```

Mira sold every unit she had. The headline says she could not sell. `cash_delta = +25` proves the
sale executed.

This generalises: `insufficient_cash` on a partial buy, `limited_by_capacity` /
`insufficient_cash_for_transport` on a partial ship all produce "wanted to X but couldn't" text
while X partially happened.

**Why blocking.** `rival_headlines` is surfaced directly in `GameView` (`schemas.py:81`) and is the
rivals' entire presence in the Section 11 outcome reveal. Shipping a UI on text that contradicts the
simulation is the kind of thing that is very hard to unwind once screens are built on it, and it is
a **truthfulness** defect, not wording taste — `AGENTS.md §7` requires the trace and its derived
player-facing output to reflect what actually happened.

**Fix.** Choose the headline on `(reason_code, actually_moved > 0)`, with a partial-fill variant per
rival ("Mira sold what little she had", etc.). Add a test asserting that when `cash_delta != 0` or
`inventory_delta` reflects a trade, the headline does not claim the action failed.

---

## SHOULD-FIX

### S0a — `ship_margin` says "positive means profitable" but ignores route reliability

**MEASURED** (raised by ChatGPT, verified independently). `actor.ship_margin`
(`actor.py:324-335`) is documented as "Single source for engine/harness/mapper ... **positive means
profitable**" and is surfaced to the player as `route_status.next_margin`. It never reads
`reliability_bps`, while `resolve_shipment` pays transport on `effective` but earns revenue only on
`delivered = effective * reliability_bps // 10_000`:

```
ship_margin(river=5200, transport=300, home=4000) = 900   ("profitable")

reliability 10000: delivered=20 cash_delta= +98 opportunity_cost=80 => TRUE net  +18  gain
reliability  5000: delivered=10 cash_delta= +46 opportunity_cost=80 => TRUE net  -34  LOSS
reliability  2000: delivered= 4 cash_delta= +14 opportunity_cost=80 => TRUE net  -66  LOSS
```

At 50% reliability the helper reports `+900` on a shipment that destroys 34 wealth.

**Scope, honestly stated.** `RouteState.reliability_bps` defaults to `10000` and
`default_start_state` uses `10000`, so **no canonical run hits this today**. But the field is
declared `ge=0, le=10_000`, `test_two_markets_route.py` exercises 9000 / 5000 / 0, and Section 8's
`event_exposure="river_risk"` exists precisely to make reliability vary later. This is a live
input-space defect and a false docstring, not a hypothetical.

**Fix.** Either fold reliability into `ship_margin(river, transport, home, reliability_bps)`, or
rename it to what it is (`quoted_margin_per_unit`) and correct the docstring to say it is a
pre-settlement quote that ignores reliability. ChatGPT's Section 10 review already warned against
calling a pre-turn spread `next_margin`; that warning was only half-applied.

---

### S0b — `run_batch` crashes on a valid `BatchConfig`

**MEASURED** (raised by ChatGPT, verified independently):

```
run_batch(BatchConfig(n_seeds=0))  ->  IndexError: list index out of range
```

`BatchConfig.n_seeds` (`harness.py:265`) carries no lower bound, so `0` is constructible, and
`run_batch` indexes the empty median list at `harness.py:539`.

*Not reproduced:* ChatGPT also predicted a `KeyError` for a policy subset
(`policies=("cash_preserving",)`) and for an unknown policy id. Both ran without raising. Reported
here as **not reproduced** rather than carried forward — though the unknown-id case silently
producing a result is worth a validation guard anyway.

**Fix.** `n_seeds: int = Field(ge=1)`; validate `policies` against `POLICY_FUNCS` keys at config
construction.

---

### S0c — `GameView` echoes `run_seed` but not `ruleset_version`, so a session cannot reproduce itself

**MEASURED** (raised by ChatGPT, verified independently):

```
GameView fields: [... 'run_seed' ...]
run_seed present: True | ruleset_version present: False
```

`CreateGameRequest` accepts `ruleset_version` (`schemas.py:16`) and `FiveTurnGame` stores it, but the
response never returns it. Determinism is defined over `run_seed + ruleset_version` (`AGENTS.md §7`),
so a game created with a non-default version cannot be reproduced from its own API representation.
This is exactly the defect ChatGPT flagged at the Section 10 plan stage ("Add both `run_seed` **and**
`ruleset_version`, because reproduction requires both") — the `run_seed` half landed, the
`ruleset_version` half did not. ORCHESTRATION §6.2, silent omission.

**Fix.** Add `ruleset_version: str` to `GameView`, populate from `session.game`, assert both in the
reproducibility test.

---

### S1 — `resolve_buy` contains two provably dead branches in the most-executed command path

**PROVEN by exhaustive enumeration** over all 1,728 combinations of
`(requested, affordable, available_space) ∈ [0,12)³`:

```
B1                     506 hits
B2(inner-DEAD)         572 hits      <- actor.py:104-108 always overwritten
B3                     506 hits
B5                     144 hits
B2(inner-used)       *** UNREACHABLE — 0 hits ***
B4                   *** UNREACHABLE — 0 hits ***      <- actor.py:116-122
```

- `actor.py:104-108`: inside `elif actual < requested and actual == available_space:`, the branch
  condition forces `requested > available_space`, so the `if requested > available_space:` block at
  109-113 **always** overwrites the reason computed at 104-108. 572/572 hits. Dead.
- `actor.py:116-122` (`elif actual == 0 and requested > 0:`): unreachable. Since
  `actual = min(requested, affordable, available_space)`, `actual == 0 < requested` implies `actual`
  equals `affordable` or `available_space`, so branch 1 or 2 always catches it first. 0/1728 hits.

All four reason codes are still produced by the live branches:

```
reason codes actually produced: ['buy_grain', 'buy_grain_zero', 'insufficient_cash', 'insufficient_storage']
```

so deleting ~12 lines is behaviour-preserving. `resolve_sell` (`actor.py:157-164`) has the same
shape in miniature: its first branch is subsumed by its second, and its `else` is unreachable.

**Fix.** Delete the dead branches; keep a unit test pinning each of the four reason codes to a
concrete `(cash, price, storage, inventory, requested)` input so the simplification is guarded.

---

### S2 — `engine/demo.py` is 242 lines of dead code

**MEASURED.** Nothing imports it:

```
$ grep -rn "from app.engine.demo\|import demo\|engine\.demo" backend/app backend/tests
(no matches)
```

It is not in `engine/__init__.py`'s exports, has no test, and is not referenced by `cli.py`. It is
~5% of the application codebase and it is the only remaining consumer of the deprecated
`PlayerOutcome.top_drivers` shim (`demo.py:236`).

Related dead shims:
- `prototype.py:132-134` `_next_world_known_for_turn` — "Backward compat shim: pre-Section 8 code
  called ..." — **zero callers**. ORCHESTRATION §6.4 (compatibility shims that reopen a closed door).
- `domain/trace.py:247-251` `top_drivers` — "Deprecated string view ... for backward compat". After
  removing `demo.py`, its only consumers are two tests that assert it mirrors `drivers`.
- `api/mappers.py:27` — `from app.engine.rng import rng_for  # noqa: F401  keep import for
  side-effect awareness`. `rng_for` has no import side effects; the justification is false and the
  import is unused.

**Fix.** Delete `demo.py`, `_next_world_known_for_turn`, and the false-justification import.
For `top_drivers`: remove it and update the two tests to assert on `drivers` directly, or keep it
and drop the "deprecated/backward compat" language — but not both.

---

### S3 — The sell path emits a node called `inventory_after_buy` carrying a sell

**REVIEW, confirmed at source** (raised by Muse, verified independently).
`engine/turn.py:490-502`, in the `sell_grain` branch:

```python
# Also emit inventory_after_buy alias for downstream valuation that expects it
nodes.append(CausalNode(id="inventory_after_buy",
                        label="Inventory after sell (alias)", delta=-actual, ...))
```

A sale is published into the player-facing causal graph under a node id that says "buy", with a
negative delta, and `purchase_quantity_value` (`turn.py:1583`) goes negative for sells. The alias
exists only because `turn.py:1105` and `turn.py:1123` hardcode `inventory_after_buy` as a parent for
both `buy_grain` and `sell_grain`.

I checked whether this produces a dangling edge on non-trade turns — it does not; both call sites
are correctly guarded by `if command.type in ("buy_grain", "sell_grain")`. So this is a naming and
modelling defect, not a broken graph.

**Fix.** Emit one node id for both verbs (e.g. `inventory_after_command`) and have `turn.py:1105`
and `1123` parent on it. **Do not** reuse the id `inventory_after_trade` — that already means
post-shipment inventory at `turn.py:1245/1375/1508` and is asserted in four tests.

---

### S4 — `OutcomeDriver`'s docstring states an identity the code violates in 70 of 455 measured turns

**MEASURED.** `domain/trace.py:205-211` says drivers have wealth impact that "**sums to
`wealth_delta` across drivers plus discarded zero effects**". `PlayerOutcome.drivers` is capped at
`max_length=3` (`trace.py:242`). Sweeping every command × world × state variant:

```
resolved 455 turns
DRIVER SUM != wealth_delta (max_length=3 truncation): 70
   ('default', 'buy_grain',  30, 'normal',  250, 342)
   ('default', 'sell_grain', 10, 'normal',  355, 305)
   ('default', 'sell_grain', 100000, 'drought', 150, 180)
   ...
```

The discarded effects are demonstrably **not** zero — e.g. a normal-world `buy_grain:30` shows
drivers summing to 250 against a `wealth_delta` of 342, so 92 of real wealth impact is dropped.

**Why it matters now.** Section 11's outcome reveal is built on `drivers` + `wealth_delta`. If the
screen lists three drivers that sum to 250 beside a headline of 342, the numbers visibly do not add
up.

**Fix (audit scope).** Correct the docstring to state what is true: top-3 by wealth-bps, residual
not represented. Whether the reveal should show a residual/"other" line is a **Section 11**
presentation decision and is explicitly *not* proposed here.

---

### S5 — Rival harvest estimates bypass the drought primitive

**REVIEW.** `engine/rivals.py:358`, `:407`, `:453` estimate available grain as
`inventory + YIELD_PER_CAPACITY * farm_capacity` — raw normal yield. The same file uses
`compute_farm_output(cap, obs.world_now)` for exactly this purpose at `:277`, `:285`, `:347`.
So under drought the rivals over-estimate their own harvest by 40% in ship/afford scoring while
correctly reducing it in farm/granary scoring. `api/mappers.py:88` has the same raw-yield pattern
(and feeds B2).

**Fix.** Route all five sites through `actor.compute_farm_output`.

---

### S6 — Type erasure at the API boundary, caused by B1

**REVIEW.** `api/mappers.py:307` `choice_map_for` returns `dict[str, object]`, forcing
`# type: ignore[arg-type]` at `api/service.py:66-67` on the single mutation path. `_wealth(state)`
(`mappers.py:30`) and `_market_view(m)` (`:34`) take untyped parameters. `to_game_view` carries three
more `# type: ignore` comments for `world`/`pressure_stage`. `mappers.py` is the worst file under
strict pyright (23 of the 47 `app/` errors) — these are the same defect seen from two angles.

**Fix.** `choice_map_for -> dict[str, PlayerCommand]`; annotate `_wealth(state: GameState)` and
`_market_view(m: MarketState)`; move the function-local `import asyncio` (`service.py:25`) and
`from app.domain.types import PlayerCommand` (`mappers.py:309`) to module scope, matching every other
module. The `# type: ignore` comments should then be removable rather than suppressed.

---

### S7 — Three implementations of "inventory value"

**REVIEW.** The same formula `qty * price // 1000` exists as:
- `actor.value_for(qty, price_milli)` — the canonical helper (`actor.py:45`)
- `prototype._wealth(state)` (`prototype.py:127-129`)
- `mappers._wealth(state)` (`mappers.py:30-31`)

`api/mappers.py:92` separately re-inlines `actor.affordable_quantity`'s formula. This is the exact
duplication that motivated extracting `actor.ship_margin` as a single helper in Section 10 (B6) —
the lesson was applied to one formula and not the others.

**Fix.** `prototype._wealth` and `mappers._wealth` call `actor.value_for`; `mappers.py:92` calls
`actor.affordable_quantity`.

---

### S8 — Dead code and chain-of-thought comments in `turn.py` and `trace.py`

**REVIEW.**
- `engine/turn.py:2010-2028` — a nested `if` whose only body is `pass`, wrapped in eight lines of
  reasoning-narration comments, followed by "Candidate 6", a four-line comment block describing a
  driver that does not exist. Violates `AGENTS.md §8`: "Comments: concise, never long
  chain-of-thought. Code is the truth."
- `domain/trace.py:57-62` — first `if` block is an identical condition to the one at 63-70 with a
  body of `pass`; the second does the real `raise`. Dead.

**Fix.** Delete both.

---

## NIT

- **N1** — `RouteState.event_exposure` (`types.py:152`) is written and never read.
  `MarketState.regional_output` defaults to 0 but is never 0 in practice.
- **N2** — Magic numbers in `mappers.py`: `80` (buy cap, `:93`) and `150` (sell cap, `:109`) have no
  stated justification.
- **N3** — `rivals.py` expresses personality through **two** mechanisms: `profile.preferences_bps`
  (used once, `:508`) and 12 hardcoded `profile.id == "mira"/"daran"` branches inside
  `_expected_return` / `score_rival_command`. Deterministic and correct, but one concept, two
  mechanisms. *(Note: an earlier pass in this audit claimed `preferences_bps` was entirely unused —
  that was a wrong grep on the wrong field name. It is used.)*
- **N4** — `SESSION_STORE` (`sessions.py:30`) grows without bound. In-memory-only until Section 16,
  so acceptable now; worth a comment noting the eviction decision is deferred.
- **N5** — `RivalPreferences.get` (`rivals.py:60-61`) double-guards with both `getattr(default)` and
  `hasattr`.
- **N6** — `harness.py:463` comment says "Keep two decimal display" while the format string emits
  four (`{ratio_frac:04d}`).
- **N7** — `prototype.py:69-88`'s tuning docstring justifies storage/route/farm but never explains
  why `demand=410` against `supply=280`, which is what makes baseline price 5928 rather than 5000.
- **N8** — `STATE.md:26` describes `prototype.py` as "`TURN_LIMIT=5, default_start_state unchanged`".
  It was substantially retuned in Section 9 (supply 280 / demand 410 / regional 360 / storage 130 /
  transport 300). Stale description.
- **N9** — `actor.py:24-42`: `cost_for_quantity` floors and `affordable_quantity` is its exact
  integer inverse. The inversion is correct (verified) but unstated; a future editor writing
  `cash // (price // 1000)` would reintroduce an off-by-one.

---

## Explicitly checked and found clean

Recording these so the next audit does not redo them.

- **Causal graph structure.** Swept 455 resolved turns (7 state variants × 13 commands × 5 pressure
  stages): **0 dangling parent edges, 0 duplicate node ids, 0 back-edges** (no node parents a node
  emitted after it). The DAG is sound.
- **`actor.affordable_quantity` / `resolve_shipment` affordability.** `((cash+1)*1000-1)//price` is
  the exact integer inverse of `qty*price//1000 <= cash`. No off-by-one.
- **Determinism.** No global `random`; `rng_for` derives via BLAKE2b over
  seed+version+turn+namespace+entity+ordinal. Engine purity is enforced by `test_engine_purity.py`.
- **HTTP semantics.** 404 unknown game / unknown choice, 409 stale revision and completed game,
  422 missing `expected_revision`, `X-Current-Revision` on conflict. Correct.
- **No skipped or xfailed tests.** No `assert True`. Only one `@pytest.mark` in the suite
  (`asyncio`, legitimate).
- **Harness balance gates.** `hold_not_top_pass = active_beats >= 2` does imply the reported
  "hold rank ≥3 among 4"; the gate and its message agree. Integer/bps throughout — no floats.

---

## Where the three reviewers disagreed

Recorded because the disagreements are informative, and because two reported findings did not
survive verification.

| Claim | Source | Verdict |
|---|---|---|
| API layer is "**clean** — per-session lock on both GET and POST, 409/404/422 correct" | Muse | **Wrong in the way that matters.** The lock is *present*; mutation proves it is *unverified* and currently inert (B3a). Muse checked existence, not effect. |
| `no_shipment` is an "unreachable legacy" headline mapping | Muse | **Wrong.** It is emitted at `turn.py:1442` and `rivals.py:702`. Not dead. Dropped. |
| `run_batch` `KeyError`s on a policy subset / unknown policy id | ChatGPT | **Not reproduced.** Both ran clean. Only the `n_seeds=0` `IndexError` is real (S0b). |
| Price-envelope test still has a `+500` loosening | ChatGPT | **Already fixed in Section 9.** Only the missing first transition remains. |
| `pyright` gate is not running strict | Claude | Missed by both Muse and ChatGPT; measured and confirmed (B1). |
| `demo.py` is 242 lines of dead code | Claude | Missed by both; confirmed by grep (S2). |
| `choices_for` hides legal moves | Claude + ChatGPT independently | Confirmed by measurement, both verbs (B2). |
| `ship_margin` ignores reliability | ChatGPT | Confirmed and quantified (S0a). |
| Rival headlines lie on partial fills | ChatGPT | Confirmed by measurement (B4). |

The pattern worth noting: **Muse verified that features exist; it did not test whether they work.**
Every finding that required running a mutation came from Claude or ChatGPT. That is a lesson for how
we prompt Muse in future rounds — ask for mutation evidence explicitly, not just file:line evidence.

---

## Ranked work order

1. **B1** — fix the pyright invocation, clear the 47 `app/` errors, decide the `tests/` policy.
   *Do this first: it surfaces S6 and part of S8 automatically.*
2. **B2** — make `choices_for` offer what the engine actually accepts, both verbs, plus the
   engine-agreement test.
3. **B4** — partial-fill-aware rival headlines.
4. **B3 (a–d)** — make the four non-falsifiable tests falsifiable (or relabel B3a honestly and
   correct `STATE.md`).
5. **S0a, S0b, S0c** — reliability-aware (or honestly renamed) `ship_margin`; `BatchConfig`
   validation; `ruleset_version` in `GameView`.
6. **S1, S2, S8** — delete proven-dead code (`resolve_buy` branches, `demo.py`, shims, `pass` blocks).
7. **S3, S4, S5, S7** — single-source the trade node id, the driver-sum docstring, the harvest
   primitive, and the value/affordability formulas.
8. **S6** — remove the type-ignores that B1's fix exposes.
9. **N1–N9** — sweep, mostly comments and doc freshness. **N8** must land with any `STATE.md` edit.

`STATE.md` must be updated in the same commit as the code (`AGENTS.md §15`), including real gate
output after B1 changes what `make type` reports.

**Tests that will legitimately need updated expectations** (numbers change because behaviour
intentionally changed — this is allowed by `BUILD_SPEC §0.4`; deleting or loosening them is not):
`test_api.py:353 test_available_choices_include_two_quantities` asserts two buy ids, two sell ids and
two ship ids from the current under-offered quantities. B2 changes those quantities. Update the
expected values to the new engine-agreeing ones; do **not** relax the assertions to `>= 1` or drop
the id checks.
