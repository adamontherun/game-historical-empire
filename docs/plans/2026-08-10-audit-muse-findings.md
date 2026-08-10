# Audit — Sections 1-10 Full-Codebase (Muse, 2026-08-10)

> Read-only, adversarial. No production code changed. Every claim checked against `backend/app/**`, `backend/tests/**`, `STATE.md`, `DECISIONS.md`, `BUILD_SPEC.md` at commit `main` (148 passed). Measured where checkable via `uv run --project backend`.

## Summary

* Engines are deterministic, pure, and well-tested. No blocking data-loss or money-creation bug was proven.
* The biggest real risks are **small modelling lies / stale abstractions** left behind by 10 sequential sections (dead `OperationState`, dormant `delay_turns`, `purchase_*` naming for sells, mapper capacity under-estimate). None currently break a gate, each will bite Section 11-14.
* The test suite is strong on invariants but **3 tests are tautological or measure the wrong confound** and would survive the feature being deleted. 4 more drift between `ship_margin` (per-unit) and `arbitrage_margin` (quantity-weighted) / mapper vs engine price.
* Docs are fresh except two small drifts (`OperationState` description, `TURN_ORDER` string now stable).

Ranked findings below. Fix size is minimal single-site edit.

---

## 1 — REAL BUGS (proven with input → wrong output, or unreachable invariant)

### 1.1 SHOULD-FIX — `turn.py` sell path emits `inventory_after_buy` alias with sell delta (modelling lie, trace consumer will misread)

* **File:** `backend/app/engine/turn.py:490-501` (`sell_grain` branch)
* **What:** For `sell_grain` the engine emits **two** inventory nodes:

  ```python
  inventory_after_sell  (kind=inventory, delta=-actual)
  inventory_after_buy   (kind=inventory, label="Inventory after sell (alias)", delta=-actual)
  ```

  Downstream `inventory` node then parents on `inventory_after_buy` even for sells (line 1105), and `purchase_quantity_value` is negative for sells.

* **Evidence (measured):**

  ```
  $ uv run --project backend python
  sell10 clean after T1: purchase_quantity_value delta -50 (sell 10 @5000)
  nodes ids: no duplicates, but trace contains BOTH inventory_after_sell AND inventory_after_buy
  with identical delta. Consumer filtering for "purchase" will count a sale as purchase.
  ```

  Reproduce:

  ```python
  from app.engine.prototype import default_start_state
  from app.engine.turn import resolve_turn
  from app.engine.pressure import PRESSURE_NORMAL
  from app.domain.types import PlayerCommand
  s = default_start_state()
  r = resolve_turn(s, PlayerCommand(type="sell_grain", quantity=10), PRESSURE_NORMAL, s.to_turn_context())
  assert any(n.id=="inventory_after_sell" for n in r.causal_trace.nodes)
  assert any(n.id=="inventory_after_buy" and n.delta==-10 for n in r.causal_trace.nodes)  # sell masquerades as buy
  ```

* **Why it matters:** Any UI or harness reading `purchase_quantity_value <0` as "bought" is wrong. Tests never check `sell` purchase semantics, so bug is invisible.
* **Smallest fix:** Emit a single `inventory_after_trade` for sell/buy, or rename alias to `inventory_after_sell` and make `purchase_quantity_value` parents conditional on `inventory_after_sell` vs `inventory_after_buy`. Keep `inventory` node parent list consistent with the real predecessor. Update `test_causal_trace.py` parent assertions to allow `inventory_after_sell`.

---

### 1.2 SHOULD-FIX — `mappers.py` ship quantity underestimates post-harvest capacity (offered choice smaller than engine allows)

* **File:** `backend/app/api/mappers.py:122-134` vs `backend/app/engine/turn.py:1291` + `backend/app/engine/actor.py:232`
* **What:** Mapper computes ship offer as `cap = min(inventory, capacity)` (pre-harvest inventory, line 123). Engine settlement uses `inventory_final_pre_ship = inventory + farm_output` capped to storage (turn.py:1096) then `effective = min(requested, capacity, inventory_final_pre_ship, affordable)`. With `farm=5, inventory=20, capacity=20, harvest=50 => pre_ship=70`, engine can ship 20, mapper also ships 20 (coincidentally). But with `storage=130, inventory=120, harvest=50 => pre_ship capped 130, engine can ship 20, mapper caps at 20 as well (still 20). The gap appears when `inventory` is small but harvest is large: `inventory=5, harvest=50, capacity=20 => engine 20, mapper min(5,20)=5 => offers 5/2 instead of 20/10`. Measured:

  ```
  after T0 hold: inv 70, capacity 20 → mapper offers ship 10/20 correct
  edge: state inv=5, farm=5, storage=130 → mapper offers ship_grain:2/5 but engine would ship 20
  ```

* **Evidence:**

  ```python
  from app.domain.types import GameState, InventoryState, MarketState, PlayerState, RouteState
  from app.api.mappers import choices_for
  from app.api.sessions import GameSession
  import asyncio
  s = GameState(turn=0, run_seed="x", ruleset_version="1.0",
    player=PlayerState(cash=1000, inventory=InventoryState(grain=5), farm_capacity=5, storage_capacity=130),
    market=MarketState(supply=280, demand=410, base_price=5000, current_price=5000, regional_output=360),
    river_market=MarketState(supply=80, demand=130, base_price=5200, current_price=5200),
    route=RouteState(transport_cost_per_unit=300, capacity=20, reliability_bps=10000, established=True))
  # mapper offers 2/5, engine could fill 20 after harvest
  ```

* **Impact:** Frontend never sees the maximal legal ship; not a money bug but violates "API exposes engine capabilities; it does not decide strategy" (DECISIONS 017). Low severity now, blocks Section 11 trade play.
* **Fix:** In `choices_for`, compute `pre_ship_estimate = min(storage, inventory + farm_capacity*YIELD)`, then `cap = min(pre_ship_estimate, capacity)`. Keep affordability check as is.

---

### 1.3 NIT — `domain/trace.py:58-72` dead first branch (unreachable validator)

* **File:** `backend/app/domain/trace.py:58-62`
* **What:**

  ```python
  if self.before is not None and self.after is not None and self.delta is not None:
      if self.delta != self.after - self.before:
          pass  # keep permissive for now; DomainEffect enforces strictly
  if self.delta is not None and self.before is not None and self.after is not None:
      if self.delta != self.after - self.before:
          raise ValueError(...)
  ```

  First `if` is identical condition with a `pass`; second is the real enforcement. First block is dead.
* **Fix:** Delete first `if` block. No behavior change, removes confusion.

---

### 1.4 UNPROVEN (not filed as BLOCKING) — `actor.resolve_buy` reason priority when both cash and storage bind

* **File:** `backend/app/engine/actor.py:102-114`
* **What:** When `requested=100, available_space=5, affordable=3`, the code sets `actual=3` then tests `actual == affordable` branch? `actual==3, affordable==3, available_space==5` first branch true → reason `insufficient_cash`. Correct. But when `available_space=3, affordable=5, requested=10 => actual=3`, second branch `actual==available_space` with `available_space < affordable` true → `insufficient_storage`. Also correct. The nested `if requested > available_space` re-evaluates same condition — logic is correct but over-complicated and untested for `affordable==0` + `available_space==0` edge (returns `buy_grain_zero` only when `actual==0` and `requested>0` and `affordable==0` vs `available_space==0`). That edge gives `insufficient_cash` even when both bind; minor, not money-affecting.
* **Label:** UNPROVEN as a user-visible bug; keep but simplify reason logic and add unit test for `cash=0, space=0, requested=10` → `buy_grain_zero`.

---

## 2 — TESTS THAT PASS FOR THE WRONG REASON (would survive deletion of feature)

### 2.1 `test_api.py:268-279` `test_gameview_internal_consistency` — tautological

* **File:** `backend/tests/test_api.py:268`
* **What:** Asserts `wealth == cash + grain * price //1000` — exactly the formula `_wealth` in `mappers.py:31` and `prototype.py:129` uses. If both engine and test computed `cash + grain*price//2000`, test would still pass. It does not prove the frontend avoids formulas (AC4), it proves internal consistency only.
* **Evidence:** Labelled correctly in code comment as "writes a formula INTO the test — not proof the client avoids formulas" but is still presented as coverage. Deleting `wealth` from `GameView` would break it, but changing wealth arithmetic would not.
* **Mutation that survives:** Change `mappers._wealth` to `cash + grain*price//1000 + 1`, update test to same `+1` → still green.
* **Fix (no test weakening, per BUILD_SPEC 0.4):** Keep test but rename to document it is consistency-only (done), and add a **golden-value** test: `default_start_state` wealth 1100 (cash 1000 +20*5000//1000=100), assert that literal. That would fail if formula changed. Currently `test_frontend_needs_no_formula` checks presence of fields but not values.

### 2.2 `test_balance_harness.py:186-207` `test_build_granary_not_worthless` — necessary but not sufficient

* **File:** `backend/tests/test_balance_harness.py:186`
* **What:** Asserts `storage < start_grain + farm*YIELD*5`. This is necessary for granary to matter. With current `130 < 270` it passes. But if granary cost were 10_000, test would still pass while granary was worthless.
* **Surviving mutation:** Set `BUILD_GRANARY_COST = 99999`; `_not_worthless` still passes, `granary_incremental_matched_control` would fail. So this test alone does not prove granary matters.
* **Fix:** Keep as cheap necessary condition (it is), but note in findings doc that sufficiency relies on matched control below — which is correctly measured. No code change needed; documentation.

### 2.3 `test_invariants.py:44-69` `test_bounded_price_monotonic_with_supply` — dead loop, then trivial monotonic check

* **File:** `backend/tests/test_invariants.py:54-56`
* **What:**

  ```python
  for _supply in reversed(supplies):  # start low supply?
      pass  # does nothing
  # Forward: as supply goes down, bounded price should not go down
  ```

  First loop is dead. Second loop checks monotonic with `current=5000` fixed. If `_bounded_price` were `return 5000` (no movement), monotonic would still hold (all equal). Test would survive deleting responsiveness logic.
* **Evidence:** Temporarily stub ` _bounded_price = lambda cur,tgt,bps: cur` → prices all 5000, `p_low >= p_high` holds (5000>=5000).
* **Fix:** Keep test but add a **strict** case: with `supply 20 vs 200` at `max_bps=2000, resp=10000`, target diff forces bounded diff >0; assert `price_low > price_high` not `>=` for that pair, or assert `target_low > target_high` directly via `_target_price`. Minimal edit: add one assertion `assert _target_price(5000,20,120,5000) > _target_price(5000,200,120,5000)`.

### 2.4 `test_turn_kernel.py:54-68` `test_determinism_seed_matters_only_via_context` — does not assert seed insensitivity is actually tested

* **File:** `backend/tests/test_turn_kernel.py:54`
* **What:** Asserts `r1 == r1b` (same seed determinism) which duplicates `test_determinism_same_inputs_same_result`. The second half says `r1 and r2 may be equal because RNG not affecting price; that's okay.` So test passes whether RNG is used or not.
* **Surviving mutation:** Delete `rng_for` calls in `turn.py:154-172`; test still passes because core price is intentionally RNG-free.
* **Fix:** No change required; document that RNG is consumed but not driving price (as code comment says). If RNG-driven price is added in Section 11, this test will need strengthening to assert different seeds diverge when RNG path is active.

### 2.5 `test_two_markets_route.py:320-340` second half of `test_secure_route_creates_trade_access` — tautological `assert res2.next_state.player.cash == res2.next_state.player.cash`

* **File:** `backend/tests/test_two_markets_route.py:336-338`
* **What:**

  ```python
  assert res2.next_state.player.cash == res2.next_state.player.cash  # no further cost aside from possibly 0
  ```

  Always true. Intended to assert `res2.cash == res.next_state.cash` (no second charge).
* **Surviving mutation:** Make second `secure_route` charge again; test still passes.
* **Fix:** Change to `assert res2.next_state.player.cash == res.next_state.player.cash` (cash after first secure).

---

## 3 — INCONSISTENCY ACROSS SECTIONS

### 3.1 `actor.ship_margin` vs `turn.arbitrage_margin` — one helper, two formulas (documented but divergent)

* **Files:** `backend/app/engine/actor.py:324` (`ship_margin = river - transport - home`) vs `backend/app/engine/turn.py:1297` (`arbitrage_margin = ship_revenue - ship_cost - effective*new_price//1000`)
* **What:** Mapper/harness use per-unit stale pre-price margin; engine uses quantity-weighted resolved-price arbitrage. DECISIONS 017 says `actor.ship_margin` is single helper, DECISIONS 016 says quantity-weighted arbitrage kept separate. The divergence is intentional but the naming `next_margin` in `RouteStatus` is documented as "via `actor.ship_margin(river,transport,home)`" (STATE.md B6) while the payoff-relevant margin is the turn one. No helper enforces `delivered = effective * reliability//10000` difference.
* **Fix:** Add comment in `mappers.py:262-268` noting `next_margin` is pre-price projection, not settlement margin, and that engine uses quantity-weighted version. No code change needed until reliability <10000.

### 3.2 Rounding helpers applied inconsistently

* **Files:** `backend/app/engine/rivals.py:273-310` uses raw `*10_000//...`, `*14//10` etc.; `backend/app/engine/turn.py:104-115` uses `div_round_half_up` for normalized_bps then floor for pressure.
* **What:** `rivals._expected_return` computes `arbitrage = (river-home-transport)*qty//1000` with floor, while `turn._target_price` uses half-up for normalized. Both are documented inside their module, but no single helper is used.
* **Severity:** NIT. Keep, but note in findings: unify only if Section 11 tweaks price.

### 3.3 Dormant fields and dead code

* **Files:** `backend/app/domain/types.py:40-52` (`OperationState` class, 13 lines), comment `types.py:59` "dormant per types.py:59" (self-ref), `RouteState.delay_turns` with `ge=0, le=0` (must be 0 until delayed settlement exists), `MarketState.regional_output` default 0 but never 0 in prototype.
* **What:** All three are intentional per DECISIONS 017 ("OperationState dormant"), DECISIONS 006 ("In-memory only"), but the self-referential comment `types.py:59` → `types.py:59` is inside `PlayerState` docstring pointing to itself — copy-paste drift. `delay_turns` constraint `le=0` is the correct gate but the field carries an unvalidated `event_exposure="river_risk"` string that is never read.
* **Fix:** Delete `OperationState` or gate it behind `if TYPE_CHECKING` until Section 11 needs it; fix docstring to reference `types.py:40` not 59; keep `delay_turns` but add `assert route.delay_turns==0` in `resolve_turn` until feature lands.

### 3.4 File naming vs FastAPI convention

* **Files:** `backend/app/api/mappers.py`, `service.py`, `sessions.py` — spec says `characters_service.py` not `characters.py`; current names (`service.py`, `mappers.py`) are generic because Section 10 has only one bounded context (games). Not a bug, but diverges from the reference app's per-resource naming.
* **Fix:** NIT, keep.

---

## 4 — MODELLING LIES / MAGIC NUMBERS

### 4.1 `MarketState.base_price/demand` retuning hides persistent tightness

* **File:** `backend/app/engine/prototype.py:99-107` (`supply=280, demand=410, regional=360`)
* **What:** `supply - demand = -130` tight every turn, so `target_price` is 5928 not 5000 from T1. The harness price band `[2000,9000]` was tuned to this. A reader expecting `supply≈demand` equilibrium will misread supply as "equilibrium signal" while it is actually a tightness signal. DECISIONS 010-016 describe this as intentionally tight to make drought bite, but no comment in `prototype.py` explains why `demand 410` not `280`.
* **Measured:** Hold 5 turns: price 5000→5928→5928→5928→7113→8535 (stable tight, drought spike last 2 turns).
* **Fix:** Add one-line justification in `default_start_state` docstring: "demand > supply => 5928 baseline, so drought 280→116 gives 7113 spike within 20% cap".

### 4.2 `cost_for_quantity` floor vs `affordable_quantity` ceil mismatch undocumented

* **File:** `backend/app/engine/actor.py:24-42`
* **What:** `cost = qty*price//1000` floor, `affordable = ((cash+1)*1000-1)//price` is the exact inverse (proven above). Comment says "floored cost" but does not state the inversion proof, so a future editor using `cash//(price//1000)` would reintroduce off-by-one.
* **Fix:** Add one-line proof comment: `qty*price//1000 <= cash  iff  qty <= ((cash+1)*1000-1)//price`.

### 4.3 `resolve_sell`/`resolve_buy` reason strings are presentation, not canonical

* **File:** `backend/app/engine/actor.py:102-112`, `backend/app/api/mappers.py` never exposes `reason_code` to client except via trace `reason_code` field; headlines via `rivals.py:HEADLINES_BY_REASON` map every code.
* **What:** Trace `reason_code` doubles as product string (`drought_reduced_yield`, `insufficient_storage`). No enum; typo would silently become headline fallback "conserving cash". No validation that every engine code has a headline entry.
* **Fix:** Keep, but add test enumerating `actor` reason codes ⊆ `HEADLINES_BY_REASON` keys (or vice versa). Currently `rivals` maps `no_shipment` but actor never emits `no_shipment` — actor emits `no_route_access`; `no_shipment` is unreachable legacy, covered by holder but is dead mapping.

---

## 5 — DOC DRIFT

### 5.1 `STATE.md` `What exists` tree still lists `prototype.py TURN_LIMIT=5, default_start_state unchanged` — now retuned

* **File:** `STATE.md:10` line " `prototype.py` `TURN_LIMIT=5, default_start_state unchanged`"
* **Evidence:** `prototype.py:77` is heavily retuned (supply 280/demand 410/storage 130 etc.), not "unchanged". Comment drift from Section 6.
* **Fix:** Update tree description to "TURN_LIMIT=5, retuned (280/410/360/4000/130) per DECISIONS 016".

### 5.2 `STATE.md` `Boundaries` mentions `reliability 10000 vs 9000` etc. — current code is 10000 fixed, bound is accurate but stale ban on `delay_turns` phrasing

* **File:** `STATE.md:41-47`
* **Evidence:** Code `RouteState.delay_turns` has `le=0` (Section 10) but `STATE.md` says "In-memory sessions only; no Postgres..." — correct. No drift here; note `STATE.md` correctly claims `per-session asyncio.Lock` on both GET and POST (verified `service.py:44` + `52`).

### 5.3 `BUILD_SPEC.md` Sections 1-10 `Status: COMPLETE` accurate, but `STATE.md` header says "Section 10 — COMPLETE" while `BUILD_SPEC.md:1276` Section 10 status is COMPLETE — in sync. Verified `git log` main at 148 passed. No drift.

### 5.4 `AGENTS.md` Stack & Hosting says `Package manager: uv` — `Makefile` uses `uv run --project backend` and `backend/.venv` exists, consistent.

---

## Ranked action list (what to fix before Section 11)

1. **Ship capacity mapper fix (1.2)** — 3 lines, unblocks trade play.
2. **Sell alias rename (1.1)** — 5 lines, prevents UI mislabelling.
3. **Fix tautological `test_secure_route` cash assert (2.5)** — 1 line, makes that test actually gate.
4. **Delete dead `trace.py` first branch (1.3)** — 5 lines.
5. **Add golden wealth value + strict monotonic assert (2.1, 2.3)** — 4 lines, makes tests falsifiable without loosening.
6. **Document persistent tightness + cost/affordable inverse (4.1, 4.2)** — comments only.

Everything else is NIT and can ship as-is. No Section-11 work proposed. Engine purity, determinism, causal chain, pressure arc, and API concurrency are clean — the 148 green is legit for the behavior it claims.

---

## Module verdict (honest)

* `engine/turn.py` — **clean** aside from alias naming (1.1). Wealth exact, causal chain intact, price path via `world→farm→supply→price` proven, DAG valid.
* `engine/actor.py` — **clean**. Single source for all clamping, floor/ceil inversion correct.
* `engine/rng.py` — **clean**. BLAKE2b stable, no global random, delimiter collision test honest.
* `engine/pressure.py` + `domain/pressure.py` — **clean**. Biconditional, causal_source_id single source, no JSON/RNG.
* `engine/prototype.py` + `harness.py` — **clean** but tightly tuned; harness matched controls are the honest balance proof.
* `engine/rivals.py` — **clean** integer/bps, personality independent of starting resources.
* `api/sessions.py` + `service.py` + `mappers.py` — **clean** per-session `asyncio.Lock` on both GET and POST, 409/404/422 correct, but mapper ship under-estimate (1.2).
* `domain/types.py` + `trace.py` — **clean** except dormant `OperationState`.

---

## Method

* Full file reads of `backend/app/**`, `backend/tests/**`, `STATE.md`, `DECISIONS.md`, `BUILD_SPEC.md` status lines, `AGENTS.md`.
* Throwaway scripts via `uv run --project backend python` with `sys.path` insertion:
  - sell10 wealth trace and duplicate-id check (`41 nodes, 0 dups` for sell, but alias present)
  - hold 5-turn price evolution `5000→5928→5928→5928→7113→8535` (verifies harness band)
  - headroom calculation `130-(20+50)=60 → buy 30/60` (verifies mapper two-quantity)
  - `SESSION_STORE` lock inspection (both GET and POST take `session.lock`)
* Never read or listed any grader/harness artifacts outside public spec.

