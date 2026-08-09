# Section 3 — One-Turn Grain Market Kernel — Plan

**Date:** 2026-08-09
**Branch:** `section/3-grain-market-kernel` (from `origin/main` at `5a0fe4c`)
**Spec Authority:** `BUILD_SPEC.md` Section 3 (Status: NOT STARTED) + global §§10-15 + `DECISIONS.md` 001-009 + `STATE.md`

---

## Goal

Prove the smallest economic causal chain `drought → lower production → lower supply → increased scarcity → upward price pressure → price movement → changed player exposure` in one deterministic, explainable turn with integer-only state, structural causal trace, and an explicit turn-resolution order. Stop when one turn is deterministic, explainable, and testable.

## Success Criteria (maps to AC #1-8)

1. `resolve_turn(state, command, world_condition, rng_context)` is deterministic: same `GameState + command + WorldCondition + seed` → identical `TurnResolution` (next_state, domain_effects, causal_trace, player_outcome). Verified by repeating calls and by stable-seed golden tests.
2. Supply/price monotonicity: reducing `supply` with `demand` unchanged cannot reduce `target_price` (and thus bounded `new_price` is non-decreasing in scarcity). Property test across random spreads.
3. Drought causation: drought influences price only via `farm_output → supply → price_pressure → price`; no direct `price *= factor` edge. Verified by inspecting `CausalTrace` — no `drought → price` edge; must go through intermediate nodes. Code grep confirms no direct price mutation from drought branch.
4. No negatives: `cash, inventory.grain, farm_capacity, storage_capacity, supply, demand, base_price, current_price` never negative after `resolve_turn` (clamped/validated). Tests cover normal + drought + buy edge cases.
5. Buy validation: buying beyond `cash` or `storage_capacity` is handled by one explicit rule — **clamped to max affordable** (bounded, not crash): `actual_qty = min(requested, cash // price_floor, available_space)`. If price is 0, treat as free but still bounded by space. Rejected quantity is recorded in trace/reason. Tests cover both cash-limited and space-limited cases.
6. Every major displayed economic change has a `CausalTrace` entry (e.g., `CASH_CHANGED`, `INVENTORY_CHANGED`, `FARM_CAPACITY_CHANGED`, `STORAGE_CAPACITY_CHANGED`, `FARM_OUTPUT`, `SUPPLY_CHANGED`, `PRICE_CHANGED`). Trace is emitted during resolution, not diff-reconstructed. Verified by asserting trace contains at least those nodes for relevant turns.
7. CLI demo prints `before_state → command → world_condition → causal_chain → after_state` legibly. Runnable via `uv run --project backend python -m app.engine.demo` (or `python -m` entry).
8. Unit + invariant tests pass; `make test && make lint && make type && make format-check` green; engine purity still holds (no forbidden imports).

## Context and Current Facts

- `main` at `5a0fe4c`; branch `section/3-grain-market-kernel` fresh. `STATE.md` marks Section 2 COMPLETE with 27 tests green; `backend/app/domain/types.py` defines `GameState{turn, run_seed, ruleset_version, player, market}`, `PlayerState{cash, inventory, farm_capacity, storage_capacity}`, `MarketState{supply, demand, base_price, current_price}`, `InventoryState{grain}`, `OperationState`, `TurnContext`, plus `Money/Quantity/PriceMilliunits/BasisPoints` aliases (ge=0 via Pydantic). `MarketState` currently lacks `responsiveness` and `max_movement` fields required by Section 3 market model.
- `backend/app/engine` has `rng.py` (`derive_seed`, `make_rng`, `rng_for` via BLAKE2b JSON array) and `rounding.py` (`mul_basis_points`, `apply_basis_points`, `div_round_half_up`, `clamp_non_negative`). Purity guard `tests/test_engine_purity.py` forbids `fastapi`/`sqlalchemy`/`httpx`/`asyncpg`/`openai`/`clerk` in `engine/` + `domain/`; `pydantic` is allowed.
- `pyproject.toml` has `pydantic>=2.7` + dev `pytest/ruff/pyright`. Makefile wrappers exist. No `resolve_turn` yet; no `WorldCondition`/`Command` enums; no `CausalTrace`/`DomainEffect`/`PlayerOutcome`; no CLI demo.
- Spec market model (conceptual pseudo, §3): `imbalance = demand - supply; normalized_imbalance = imbalance / effective_supply; price_pressure = normalized_imbalance × responsiveness; target_price = base_price adjusted by price_pressure; new_price = bounded movement toward target_price`. Must preserve integer-safe, monotonic, positive, bounded properties — formula details may be simplified if properties hold.
- Spec requires: one market/one good (grain), world conditions `normal`/`drought`, player commands `expand_farm`/`build_granary`/`buy_grain`/`hold`, explicit resolution order, opportunity cost (cash/storage scarce), and `resolve_turn → (next_state, domain_effects, causal_trace, player_outcome)`. Section 4 will formalize `DomainEffect/CausalNode/PlayerOutcome/OutcomeDriver` — Section 3 may introduce a minimal compatible version.
- Global rules: integer canonical state, deterministic substreams via hash, pure engine (no I/O), causal trace emitted structurally, "author cause, simulate consequences" (no `price *= 1.4`).

## Constraints and Non-goals

**Must satisfy:**
- Pure `backend/app/engine` + `backend/app/domain` — no FastAPI/SQLAlchemy/httpx.
- Integer-only canonical state; deterministic rounding via helpers; no `random` global or `hash()`.
- Explicit turn-resolution order documented and tested.

**Explicitly out of scope (BUILD_SPEC §3):**
- Two markets / River Route (Section 5), 5-turn arc (Section 6), rivals Mira/Daran (Section 7), pressure event arc (Section 8), two-era content (Section 9), API/persistence (Sections 10/16), LLM narration, generic business registry.
- Do not design universal mechanism; keep one-grain kernel explicit.

**Non-goals for this section:**
- No FastAPI routes, no DB, no React, no rival scoring, no seasonal spoilage, no credit/brands.

## Key Decisions

| # | Decision | Choice | Why | Alternative rejected |
|---|----------|--------|-----|----------------------|
| 1 | **MarketState extension** | Add `responsiveness: BasisPoints = 5000` (50% pass-through) and `max_movement_bps: BasisPoints = 2000` (20% per-turn cap) with defaults, so existing tests `MarketState(supply=..., demand=..., base_price=..., current_price=...)` keep passing. Document as "basis points where 10_000 = 100%". | Satisfies spec "responsiveness + maximum per-turn movement" while keeping backward compat; defaults are legible (50% responsiveness, 20% cap). | Breaking change requiring all call sites updated — would fail existing `test_core_types.py` and force churn. Alternative separate `MarketParams` struct rejected: spec lists them as market state fields, and single object is simpler for Section 3. |
| 2 | **Price formula (integer-safe)** | `effective_supply = max(supply, 1)`; `imbalance = demand - supply`; `normalized_imbalance_bps = div_round_half_up(imbalance * 10_000, effective_supply)`; `price_pressure_bps = normalized_imbalance_bps * responsiveness // 10_000`; `target_price = clamp_non_negative(base_price * (10_000 + price_pressure_bps) // 10_000)` with floor at 1; `max_delta = current_price * max_movement_bps // 10_000`; `new_price = clamp(target_price, current_price ± max_delta)` and `max(1, ...)`. Uses `mul_basis_points`/`clamp_non_negative`. | Preserves all five required properties: lower supply → higher normalized_imbalance → higher target (monotonic), negative imbalance gives downward pressure, prices stay ≥1, extreme moves bounded, and each step is inspectable. No float. | Direct float `price *= 1 + imbalance/supply*responsiveness` rejected: float nondeterminism + fails integer-only rule. Copying pseudo verbatim with float rejected. |
| 3 | **Drought rule** | `YIELD_PER_CAPACITY = 10` grain per farm_capacity under normal; drought reduces by `DROUGHT_YIELD_REDUCTION_BPS = 4000` (40%): `farm_output = farm_capacity * YIELD_PER_CAPACITY * (10_000 - reduction) // 10_000` when `WorldCondition.drought`, else full yield. Supply update: `next_supply = clamp_non_negative(supply + farm_output - DEMAND_CONSUMPTION)` where `DEMAND_CONSUMPTION = 0` for Section 3 minimal? Instead: `next_supply = clamp_non_negative(supply + farm_output)` and demand unchanged, so supply reflects production and scarcity changes price. Alternatively keep supply as `clamp_non_negative(supply - drought_shortfall)` where shortfall derived from reduced output. | Satisfies "drought must reduce production or yield, not directly apply price modifier" — price only moves because supply is lower after production step. Keeps model legible for trace. | Direct `if drought: price = price * 1.4` rejected — violates spec and AC #3. More complex consumption/rotation model rejected as premature. |
| 4 | **Command costs & deltas** | `expand_farm`: cost 500, `farm_capacity += 10`; `build_granary`: cost 300, `storage_capacity += 50`; `buy_grain`: param `quantity: Quantity`, cost `quantity * current_price // 1000` (milli → money) floored; capped by cash and `storage_capacity - inventory.grain`; `hold`: no cost. All costs via `Money` ints. Constants in `turn.py` top-level. | Creates opportunity cost: each consumes cash and forecloses alternatives; buying consumes storage; holding gains no asset. Values chosen so starting cash 1000 makes choices meaningfully different (can't do all). | Zero-cost commands or quantity-free buy rejected: no opportunity cost. Variable cost via float rejected. |
| 5 | **Turn-resolution order** | **Command → Production → Supply → Price → Player inventory/cash settlement → Next state** explicitly: (1) apply command to get intermediate player (cash/capacity/inventory delta), (2) compute `farm_output` from *post-command* `farm_capacity` + world condition, (3) add `farm_output` to inventory (capped by storage) and to market supply, (4) compute price from updated supply/demand, (5) compute player exposure (inventory value), (6) increment `turn`, emit trace. Document order as constant `TURN_ORDER` and test that `expand_farm` before harvest yields more output than after. | Makes command effects affect same turn's production, rewarding timely expansion — intuitive and testable. Alternative "harvest before command" would delay effect one turn and be less legible for single-turn demo. | Unspecified order rejected — spec requires explicit and tested. |
| 6 | **Buy validation rule** | **Bounded (clamped)**: `affordable_qty = cash // price_per_unit_floor` (if price 0, affordable = available_space); `space = storage_capacity - inventory.grain`; `actual_qty = min(requested, affordable, space)`; cost = `actual_qty * price // 1000`; trace records `requested` vs `actual` and reason `INSUFFICIENT_CASH` / `INSUFFICIENT_STORAGE` if clamped. If `actual_qty == 0`, no mutation but trace explains. | Satisfies AC #5 "rejected or safely bounded according to one explicit rule" with deterministic, non-negative result and inspectable trace. Clamped is more demo-friendly than exception. | Exception-throwing validation rejected: would break `resolve_turn` purity and require caller try/catch; silent no-op without trace rejected: not inspectable. |
| 7 | **Causal trace shape (minimal for §3, compatible with §4)** | Introduce `backend/app/domain/trace.py` (or `engine/trace.py`?) with `CausalNode{id, label, kind, before, after, delta, reason_code, parent_ids: list[str]}`, `CausalTrace{nodes: list[CausalNode]}` plus `DomainEffect{metric, before, after, reason_code}` and `PlayerOutcome{wealth_delta, inventory_value_delta, top_drivers: list[str]}`. Keep trace emission *during* resolution — each step appends node with `parent_ids` linking `drought → farm_output → supply → price`. Flat `domain_effects` derived from trace but kept separate for AC. | Meets AC #6 "every major displayed economic change has trace entry" and global §14 "chain/edges needed, not flat deltas". Parents give chain. Minimal enough for Section 3, extensible for Section 4 driver ranking (≤3 drivers derived deterministically from trace). | Flat list of deltas only rejected — spec says insufficient. Reconstructing trace by diffing rejected. Deferring trace to Section 4 rejected — Section 3 AC #6 requires it now. |
| 8 | **RNG usage** | `resolve_turn` takes `TurnContext` (or `run_seed/ruleset_version/turn`) and derives one substream `rng_for(..., namespace="turn", entity_id="price_jitter")` but core price remains deterministic; RNG is used only for optional ±1 milliunit tie-breaker within bounds *or* left unused with comment. At minimum, call `derive_seed` to prove seed is consumed and determinism holds. | Satisfies AC #1 without violating monotonicity. Keeps determinism test meaningful (same seed → same). | Using `random.random()` global rejected. Using RNG to drive price directly rejected (could break monotonic invariant). |
| 9 | **File layout** | `backend/app/domain/types.py` extended (add MarketState fields, WorldCondition, PlayerCommand); `backend/app/domain/trace.py` new (CausalNode/Trace etc); `backend/app/engine/turn.py` new (resolve_turn + helpers: `_compute_target_price`, `_compute_farm_output`, `_apply_command`); `backend/app/engine/demo.py` new (CLI); `backend/app/engine/__init__.py` re-exports. | Keeps domain types pure, engine logic isolated, demo separate. Matches Beta Acid file naming (`*_service.py` not needed until Section 10). | Single monolithic `engine.py` rejected: harder to keep purity + test import boundaries. |
| 10 | **CLI demo** | `python -m app.engine.demo` prints: before `GameState` (turn/cash/inventory/capacities/supply/demand/price), command, world condition, causal chain (nodes in order with parent links), after state, plus player outcome. Accepts optional `--seed`/`--command`/`--world` args but defaults to illustrate drought vs normal. | Satisfies AC #7 and gives manual verification. Uses only stdlib `argparse` + `rich` is not needed; plain prints keep engine pure. | No demo rejected: AC #7 fails. Demo that imports FastAPI rejected. |

## Recommended Approach

Extend `MarketState` with defaults, add `WorldCondition`/`PlayerCommand` to domain, introduce `trace.py` for causal structures, implement `turn.py` with explicit order and integer math, wire `rng_for` for determinism, add `demo.py`, write focused tests covering determinism, monotonicity, drought chain, non-negativity, buy clamping, and trace completeness. Keep all new code `pyright` strict and `ruff` clean.

## Work Plan

Order matters; earlier steps unblock later verification.

### 1. Domain extensions — `backend/app/domain/types.py`
- Add `WorldCondition = Literal["normal","drought"]` (or Enum) and `PlayerCommand` discriminated model: `type: Literal["expand_farm","build_granary","buy_grain","hold"]` + optional `quantity` for buy.
- Extend `MarketState` with `responsiveness: BasisPoints = 5000` and `max_movement_bps: BasisPoints = 2000` (with `Field(ge=0)` etc). Keep existing fields.
- Ensure `pyright` strict and existing `test_core_types.py` still passes (defaults).
- Files: `backend/app/domain/types.py`, `backend/app/domain/__init__.py` (re-exports).
- Depends: none.

### 2. Trace/outcome domain — `backend/app/domain/trace.py`
- Define `CausalNode`, `CausalTrace`, `DomainEffect`, `PlayerOutcome` (and `TurnResolution` if not in `turn.py`). Use `BaseModel(frozen=True)`; `CausalNode` has `id: str`, `kind: str`, `label: str`, `before: int | None`, `after: int | None`, `delta: int | None`, `reason_code: str`, `parent_ids: list[str]`.
- Define `TurnResolution` with `next_state: GameState`, `domain_effects: list[DomainEffect]`, `causal_trace: CausalTrace`, `player_outcome: PlayerOutcome`.
- Files: `backend/app/domain/trace.py`, re-export in `domain/__init__.py`.
- Depends: #1.

### 3. Engine core — `backend/app/engine/turn.py`
- Implement helpers (`_farm_output`, `_target_price`, `_bounded_price`, `_apply_command`, `_available_space`) and main `def resolve_turn(state: GameState, command: PlayerCommand, world: WorldCondition, rng_context: TurnContext) -> TurnResolution` with explicit `TURN_ORDER` docstring.
- Integer math via `mul_basis_points`/`clamp_non_negative`/`div_round_half_up`; no float; no `random` global; use `rng_for` at least for determinism proof.
- Emit `CausalNode` for each step with parent links; build `domain_effects` in parallel.
- Handle buy clamping per Key Decision 6; ensure no negative state (AC #4).
- Files: `backend/app/engine/turn.py`, `backend/app/engine/__init__.py` (re-export `resolve_turn`).
- Depends: #1-2.

### 4. CLI demo — `backend/app/engine/demo.py`
- Implement `main()` that constructs a sample `GameState`, runs `resolve_turn` for `normal` vs `drought` and for each command, prints before/after and trace chain legibly.
- Ensure `python -m app.engine.demo` works from `backend/` project root; no extra deps.
- Files: `backend/app/engine/demo.py`.
- Depends: #3.

### 5. Tests — `backend/tests/test_turn_kernel.py` + `backend/tests/test_invariants.py`
- `test_turn_kernel.py`: determinism (same inputs → same resolution), drought chain (trace has `drought -> farm_output -> supply -> price` parents, no direct drought->price), non-negative invariants, buy cash-limited & storage-limited clamping + trace reason, price bounded, hold no-op.
- `test_invariants.py`: monotonicity property (for fixed demand, lower supply → target_price non-decreasing), drought never directly mutates price (code scan for `price` mutation in drought branch), every major change has trace entry, spend forecloses alternative (cash after expand < before).
- Files: `backend/tests/test_turn_kernel.py`, `backend/tests/test_invariants.py`.
- Depends: #3.

### 6. Gates — `uv sync --project backend`, `make test`, `make lint`, `make type`, `make format-check`, plus manual `uv run --project backend python -m app.engine.demo`
- Fix `ruff`/`pyright` issues; ensure `test_engine_purity.py` still passes (new `engine/turn.py` imports only `app.domain.*`, `app.engine.rng/rounding`, `hashlib` etc).
- Update `STATE.md` milestone note but not `BUILD_SPEC.md` Status until gates pass; after green, update Status line.
- Depends: #1-5.

Linear order 1 → 2 → 3 → 4 → 5 → 6; #4 can parallel #5 after #3.

## Validation Plan

- **Gate install:** `uv sync --project backend` → 0 errors. Evidence: output.
- **Gate unit:** `make test` → expect 27 existing + ~12-15 new = ~40 passed; no failures. Evidence: `pytest -v` tail.
- **Gate lint:** `make lint` → `ruff check backend` All checks passed. Evidence: output.
- **Gate type:** `make type` → `pyright` 0 errors. Evidence: output (strict mode).
- **Gate format:** `make format-check` → already formatted. Evidence: output.
- **Purity:** `pytest backend/tests/test_engine_purity.py -v` → 2 passed. Evidence: output.
- **Determinism:** run `resolve_turn` twice with same seed, assert equality; golden seed check for `derive_seed`.
- **Monotonicity:** loop `supply in [10,50,100,200]` with same demand, assert `target_price` non-decreasing as supply decreases.
- **Drought chain:** inspect trace nodes: find node with `reason_code=="drought_reduced_yield"` parent of `supply` node parent of `price` node; assert no node has `reason_code=="drought_price_modifier"` or direct parent `drought → price`.
- **Non-negative:** after each of 4 commands × 2 worlds, assert all Money/Quantity/Price fields `>=0`.
- **Buy clamping:** with `cash=100`, `price=5000` (5 per unit), `requested=50`, assert `actual <= cash//price` and trace contains `INSUFFICIENT_CASH`.
- **Trace completeness:** after turn that changes cash/inventory/price, assert trace contains nodes for those metrics.
- **CLI demo:** `uv run --project backend python -m app.engine.demo` prints before/command/world/chain/after sections; exit 0. Evidence: captured stdout snippet.

Highest-risk validation: `pyright` strict with new `PlayerCommand` discriminated union + `WorldCondition` Literal; may need `Annotated` + `Field(discriminator=)` or simple `BaseModel` with `Literal` to satisfy strict.

## Risks / Rollback

- **Risk:** Extending `MarketState` with required fields breaks existing tests if defaults wrong. Mitigation: provide defaults matching current test values (5000/2000) and `ge=0`; run `test_core_types.py` first.
- **Risk:** Price formula float or off-by-one breaks monotonic invariant. Mitigation: use integer helpers and property test before committing.
- **Risk:** Trace emission missed for some changes → AC #6 fails. Mitigation: build `domain_effects` and `CausalNode` together at each mutation site, and assert in tests.
- **Risk:** `pyright` strict failures on new domain models. Mitigation: use `ConfigDict(frozen=True, extra="forbid")`, explicit types, `from __future__ import annotations`.
- **Risk:** Buy clamping rule ambiguous → AC #5 not met if we choose wrong. Mitigation: choose clamped rule, document in docstring and test both cash/space limits, note alternative "rejected" would also pass but clamped is explicit.
- **Rollback:** `git checkout main -- backend/app/domain/types.py backend/app/engine` + `rm backend/app/domain/trace.py backend/app/engine/turn.py` etc., branch delete if plan rejected.

## Open Questions

- **Q1:** Market `responsiveness` unit: treat as `BasisPoints` where `10_000 = 100%` pass-through from normalized imbalance to price pressure (chosen). If reviewer prefers fixed coefficient, can adjust without spec change — property preserved.
- **Q2:** `YIELD_PER_CAPACITY=10` and cost constants (500/300) are judgement values to create opportunity cost with starting cash 1000. If reviewer prefers different, constants are isolated in `turn.py` top-level and easily tuned — no spec violation.
- **Q3:** Supply persistence model: chosen `next_supply = clamp(supply + farm_output)` is simplest to show drought → supply drop → price rise. If reviewer expects `next_supply` recomputed from base, we can swap with same causal chain — tests only check direction, not absolute levels.
- All are judgement within spec; none block implementation.

---

**Next:** Awaiting approval, then `/goal` implementation on `section/3-grain-market-kernel`.
