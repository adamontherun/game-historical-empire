# Section 4 — Causal Explanation and Outcome Model — Plan

**Date:** 2026-08-09
**Branch:** `section/4-causal-explanation` (from `origin/main` at `35fa70e`)
**Spec Authority:** `BUILD_SPEC.md` Section 4 (Status: NOT STARTED) + global §§10–15 + `DECISIONS.md` 001–009 + `STATE.md` §3 follow-ups
**Related:** `backend/app/domain/types.py`, `backend/app/domain/trace.py`, `backend/app/engine/turn.py`, `backend/app/engine/demo.py`, `backend/app/engine/rng.py`, `backend/app/engine/rounding.py`

---

## Goal

Make the one-turn grain market from Section 3 legible without reconstructing causes by diffing snapshots: formalize a causal graph (`DomainEffect`, `CausalNode`, `CausalEdge`/`parent_ids`, `CausalTrace`) plus a deterministic, player-facing `OutcomeDriver` / `PlayerOutcome` ranking (≤3 drivers in the main reveal, full trace retained for debug), and prove via tests and CLI that "why did this happen?" is answered structurally. Fix the three Section 3 follow-ups owned by Section 4.

---

## Success Criteria (maps to Section 4 AC 1–5 + STATE follow-ups)

1. **Every important state change has a causal parent — including wealth with exact decomposition.** After `resolve_turn`, each node that represents a mutated canonical value (`cash`, `farm_capacity`, `storage_capacity`, `farm_output`, `supply`, `price_pressure`, `target_price`, `price`, `inventory`, plus valuation nodes `quantity_value_effect`, `price_value_effect`, `wealth`) lists ≥1 `parent_ids` that resolves to an earlier node, the graph is acyclic, ids are unique, parents are tuples, and parents appear before children in `trace.nodes` emission order. Pure diagnostic roots `world` and `command` may have `()` regardless of delta; `farm_capacity` may have `()` only when `delta==0` (`farm_capacity_unchanged`). The valuation subgraph must be exactly:

   ```text
   wealth_before = cash_before + value(inventory_before, price_before)
   quantity_value_effect = value(inventory_after, price_before) - value(inventory_before, price_before)
   price_value_effect    = value(inventory_after, price_after)  - value(inventory_after, price_before)
   cash_effect           = cash_after - cash_before
   wealth_delta          = cash_effect + quantity_value_effect + price_value_effect
   ```

   where `value(qty, price_milli) = qty * price_milli // 1000` (integer, no float). Graph edges:

   ```text
   inventory_before ─┐
                     ├→ quantity_value_effect ─┐
   inventory_after ──┘                         │
                                               ├→ wealth
   inventory_after ─┐                         │
                    ├→ price_value_effect ────┤
   price_before → price_after ─┘              │
   cash_before → cash_after ──────────────────┘
   ```

   `quantity_value_effect` parents `("inventory", "price_before")` (or `("inventory", "price")` if price node covers before/after), `price_value_effect` parents `("inventory", "price")`, `wealth` parents `("cash_after_command", "quantity_value_effect", "price_value_effect")` (tuples). `DomainEffect` entries for `quantity_value_effect`, `price_value_effect`, `wealth` added.

2. **Drivers derived from trace, not snapshot diff.** `PlayerOutcome.drivers: tuple[OutcomeDriver, ...]` (with deprecated `top_drivers: tuple[str, ...]` derived) is computed only from `CausalTrace` nodes/effects — no `next_state - before_state` guessing. Drivers must reference `reason_code`/`causal_node_ids` that are subsets of trace ids, and their `impact_money` must sum to `wealth_delta` exactly (see #1).

3. **Driver ranking is deterministic and exact.** Same `state + command + world + seed` → identical ranked driver tuple, byte-for-byte. Implementation uses a total order `(impact_bps DESC, id ASC)` where `impact_bps = abs(impact_money)*10_000 // max(wealth_before,1)` with no `random`/`hash()`/`set` iteration. Tested by calling `resolve_turn` twice and by shuffling candidate construction order in a helper and re-sorting.

4. **CLI shows both concise and full trace.** `uv run --project backend python -m app.engine.demo --world drought --command hold [--verbose]` prints (a) concise section: `WHY?` with 1–3 driver sentences + wealth/inventory/price deltas with exact `impact_money`/`impact_bps`, and (b) verbose/debug section: full `CausalTrace` nodes in emission order with `before/after/delta/reason_code/parents` and `DomainEffect` list including `quantity_value_effect`/`price_value_effect`/`wealth`. Default shows concise; `--verbose` / `--debug` shows both.

5. **Multi-step chain test: drought → wealth effect — structurally exact.** At least one test asserts the full structural chain `world(drought) → farm_output(reduced) → supply(lower) → price_pressure → price(increase) → price_value_effect → wealth` and that `wealth_delta == cash_effect + quantity_value_effect + price_value_effect` exactly (integer). Each driver must reference its supporting `causal_node_ids` (tuple) that are a subset of `CausalTrace` ids, and the wealth node must be parented by `quantity_value_effect`+`price_value_effect`+`cash_after_command`, not merely computed after resolution. Test uses `turn=0, farm=10, supply=100, demand=120, inventory=20, storage=100` sample; if storage was full, `quantity_value_effect` must be 0.

6. **Section 3 follow-ups resolved before COMPLETE:**
   - Raw `abs(delta)` ranking replaced by **exact wealth-bps ranking** (impact on player wealth in basis points of pre-turn wealth, derived from exact decomposition). New test demonstrates the old bug: raw price milliunits vs grain magnitude no longer decides ranking; only `impact_bps` does.
   - Trace graph shape hardened with validators (unique ids, parent existence, acyclic, ordering, allowed roots `world`/`command` regardless of delta) and **immutable tuples** for all sequence fields. `pyright` strict and `ruff` still pass.
   - RNG context ownership fixed: `resolve_turn` validates `rng_context == state.to_turn_context()`; caller desync raises `ValueError`. No jitter added merely because a substream exists. Tested.

---

## Context And Current Facts

- `main` at `35fa70e` (squashed Section 3). `STATE.md` marks Section 3 COMPLETE — 50 tests green (`8 core + 7 rounding + 11 determinism + 15 kernel + 7 invariants + 2 purity/sanity`), `ruff` + `pyright` strict pass. `BUILD_SPEC.md` Section 4 is `NOT STARTED`.
- **Current domain (`backend/app/domain/types.py:1`):** `Money/Quantity/PriceMilliunits/BasisPoints` via `Annotated[int, Field(ge=0, strict=True)]` etc., `InventoryState{grain}`, `OperationState{id,kind,capacity,level}`, `PlayerState{cash, inventory, farm_capacity, storage_capacity}`, `MarketState{supply,demand,base_price,current_price,responsiveness=5000,max_movement_bps=2000}`, `TurnContext{turn,run_seed,ruleset_version}`, `WorldCondition = Literal["normal","drought"]`, `PlayerCommand{type, quantity?}`, `GameState{turn,run_seed,ruleset_version,player,market}` with `to_turn_context()`. All frozen via `ConfigDict(frozen=True)`.
- **Current trace (`backend/app/domain/trace.py:1`):** `CausalNode{id,label,kind,before,after,delta,reason_code,parent_ids: list[str]}`, `CausalTrace{nodes: list[CausalNode]}`, `DomainEffect{metric,before,after,delta,reason_code}`, `PlayerOutcome{wealth_delta,inventory_delta,price_delta,top_drivers: list[str]}`, `TurnResolution{next_state,domain_effects,causal_trace,player_outcome}`. No `OutcomeDriver` type, no valuation nodes, mutable lists.
- **Current engine (`backend/app/engine/turn.py:1`):** `resolve_turn(state, command, world, rng_context)` with explicit `TURN_ORDER = "command -> production -> supply -> price -> settlement"`. Integer-safe market math via `rounding.py`. Drought correctly reduces `farm_output` rather than price. Buy clamped via `min(requested, affordable, space)`. RNG substream consumed but core price deterministic. Trace emission is structural but stops at `inventory` — wealth is computed as `cash + inventory*price//1000` only for `PlayerOutcome`, not as graph nodes. Ranking is `sorted by abs(delta)` over raw nodes — the documented follow-up bug.
- **Purity and tooling:** `tests/test_engine_purity.py` forbids forbidden imports; `tests/test_determinism.py` bans global `random.*` and `hash()`. `pyproject.toml` has `pydantic>=2.7`, `pytest>=9`, `ruff>=0.8`, `pyright>=1.1 strict`, `python >=3.12`. Makefile wrappers are `make test`→`uv run --project backend pytest -v`, etc. Gates green (after `~/.cache/uv/sdists-v9/.git` fix).
- **Section 4 spec (BUILD_SPEC.md:865):** Must formalize `DomainEffect`, `CausalNode`, `CausalEdge or parent reference`, `CausalTrace`, `PlayerOutcome`, `OutcomeDriver`; support causal chain not flat list; rank ≤3 drivers derived from trace; preserve full debug trace. Out of scope: LLM narration, advisor chat, natural-language action interpretation, persistence.

---

## Constraints And Non-goals

**Must satisfy:**
- Pure `backend/app/engine` + `backend/app/domain` — no `fastapi`/`sqlalchemy`/`httpx`/`asyncpg`/`openai`/`clerk` imports.
- Integer-only canonical state; deterministic via `derive_seed`/`rng_for` (BLAKE2b JSON array), no `random` global or `hash()`.
- Deterministic rounding via `rounding.py` helpers; no floats in canonical path.
- Keep `frontend/` untouched (Section 11), no DB/API/auth/deployment.

**Explicitly out of scope (BUILD_SPEC §4):**
- LLM narration / advisor chat / natural-language command interpretation.
- Persistence (Section 16), two markets / River Route (Section 5), 5-turn prototype (Section 6), rivals Mira/Daran (Section 7), generic event framework.

**Non-goals for this section:**
- No new economic goods or markets beyond grain/Home-Valley single market.
- No transport/trade logic, no spoilage/seasonality, no credit/brands/automation.
- No API routes or `render.yaml` changes.
- Do not chase repo-wide `90%+ coverage` gating yet — only Section 4-relevant tests.

---

## Key Decisions

| # | Decision | Choice | Why | Alternative rejected |
|---|----------|--------|-----|----------------------|
| 1 | **Exact wealth decomposition (no approximation)** | Define `value(qty, price_milli) = qty * price_milli // 1000` (floor, integer). Then before/after wealth and exact effects: `wealth_before = cash_before + value(inv_before, price_before)`; `quantity_value_effect = value(inv_after, price_before) - value(inv_before, price_before)`; `price_value_effect = value(inv_after, price_after) - value(inv_after, price_before)`; `cash_effect = cash_after - cash_before`; `wealth_delta = cash_effect + quantity_value_effect + price_value_effect`. This is exact — sum of driver `impact_money` equals `wealth_delta` by construction, preserving all rounding. Nodes: `quantity_value_effect` (parents `("inventory","price")` or `("inventory_before","inventory_after","price_before")` simplified to `("inventory","price")` with `before=value(inv_before,price_before)`, `after=value(inv_after,price_before)`), `price_value_effect` (parents `("inventory","price")`, `before=value(inv_after,price_before)`, `after=value(inv_after,price_after)`), `wealth` (parents `("cash_after_command","quantity_value_effect","price_value_effect")`, `before=wealth_before`, `after=wealth_after`). Extend `TURN_ORDER` to `command -> production -> supply -> price -> settlement -> valuation`. Add `DomainEffect` for each. | Fixes dangerous approximate attribution flagged in review: if drivers double-count or use residual, `sum(impact_money) != wealth_delta` and a farm-output driver could claim impact that storage prevented, or a counterfactual drought-vs-normal could sneak in. Exact decomposition at old vs new prices makes realized wealth impact zero when storage was full, and makes `sum == wealth_delta` a testable invariant. No float, no approximation. | Approximate `farm_output_delta * new_price`, `price_delta * final_inventory`, or residual rejected — they can double-count, not sum to `wealth_delta`, and hide storage constraints. Single `inventory_value` node (`value(before)`→`value(after)`) without splitting quantity vs price effects rejected — collapses two distinct economic phenomena and prevents drivers from pointing to the correct valuation effect. |
| 2 | **Immutable tuples for frozen causal models** | Use `tuple` for all sequence fields: `CausalNode.parent_ids: tuple[str, ...]`, `CausalTrace.nodes: tuple[CausalNode, ...]`, `OutcomeDriver.causal_node_ids: tuple[str, ...]`, `PlayerOutcome.drivers: tuple[OutcomeDriver, ...]`, `CausalTrace.edges: tuple[CausalEdge, ...]`. Keep `ConfigDict(frozen=True)`. Construct with `tuple(...)` in `turn.py`. | `frozen=True` only freezes reassignment, not list contents; tuples make trace tamper-evident. | `list` rejected — mutable. Custom guard rejected — verbose. |
| 3 | **OutcomeDriver as causal story, not single node — generate all, rank, keep top 3** | Define `OutcomeDriver` as story grouping multiple causal nodes: `id: str`, `label: str`, `kind: str`, `impact_money: int`, `impact_bps: int`, `reason_code: str`, `causal_node_ids: tuple[str, ...]`. **Generate all materially applicable candidates, discard zero/non-material, then rank.** Candidate stories (only if they actually occurred, `impact_money !=0` or meaningful `delta`): `command_cost` (`command → cash_after_command`), `farm_output` (`world → farm_output`), `storage_constraint` (`farm_output + storage → inventory` capped), `supply_price` (`farm_output → supply → price_pressure → target_price → price`), `quantity_value_effect` (`inventory → quantity_value_effect`), `price_revaluation` (`price → price_value_effect`), plus `cash_effect`/`wealth` wrappers if needed. For each, `impact_money` is the exact effect from #1 (`cash_effect` for command, `quantity_value_effect` for storage/farm paths, `price_value_effect` for supply-price). Then `impact_bps = abs(impact_money)*10_000 // max(wealth_before,1)`, sort by `(-impact_bps, id)` and slice `[:3]` → `tuple`. If `wealth_before==0`, fallback to `abs(impact_money)`. No canned exactly-3. | Prevents both failure modes flagged: exactly-3 canned stories would rank meaningless zero-impact stories and violate "top drivers" selection; one-node-per-driver would produce `supply fell`/`price pressure rose`/`target rose` as three drivers for one phenomenon. Generating only applicable stories and ranking by exact wealth impact yields turns with 2 or 3 drivers as appropriate (e.g. `hold` in normal market may have only `farm_output`+`supply_price`). | Exactly-3 canonical drivers rejected — not selective, produces zero-impact stories. One-driver-per-node rejected — redundant. Approximate impact rejected per #1. |
| 4 | **Driver ranking in one common unit: exact wealth-bps** | Use exact `impact_money` from #1, then `impact_bps = abs(impact_money)*10_000 // max(wealth_before,1)` (or `abs(impact_money)` if `wealth_before==0`). No mixing of `delta_bps` per kind or weights. | Single-unit wealth-bps makes every story comparable and exact. | Mixed `delta_bps`+`impact_money`+weights rejected — arbitrary cross-unit. |
| 5 | **CausalEdge vs parent_ids** | Keep `parent_ids: tuple[str,...]` canonical; add `CausalEdge = tuple[str,str]` and computed `edges: tuple[CausalEdge,...]`. No separate persisted edge list. | Single source of truth. | Separate mutable edge list rejected. |
| 6 | **Trace hardening & validator roots fix** | Add `CausalTrace` `@model_validator(mode="after")` enforcing: ids unique, every `parent_id` resolves to a preceding node, no self-cycle, parents-before-children, **allowed roots are `world` and `command` regardless of delta** (they are authored causes), `farm_capacity` may have `()` only when `delta==0`/`reason=="farm_capacity_unchanged"`; otherwise it must be child of `command`. Also validate `DomainEffect.delta == after - before` and `CausalNode.delta == after - before` when both present. | Fixes validator bug flagged: `expand_farm`/`build_granary` have nonzero delta on `farm_capacity`/`storage_capacity` and `command` has nonzero cash delta — validator must not reject them as roots. `world` is always a root. `farm_capacity` with `delta==0` represents unchanged pre-existing state, otherwise it's a child. | Old validator that required parents for any nonzero delta rejected — would reject valid command traces. No validation rejected. |
| 7 | **RNG context ownership** | Keep `resolve_turn(state, command, world, rng_context)` but validate `expected = state.to_turn_context(); if rng_context != expected: raise ValueError(...)`. Consume substream without driving price. | Fixes follow-up without breaking tests. | Ignore mismatch rejected. Remove param now rejected. Add jitter rejected. |
| 8 | **CLI — concise vs full trace** | Extend `demo.py` with `--verbose/--debug`: concise prints `PLAYER OUTCOME` + `WHY?` with story drivers (`label`, exact `impact_money`, `impact_bps`, `causal_node_ids`); verbose adds `FULL CAUSAL TRACE` including `quantity_value_effect`, `price_value_effect`, `wealth` and `DOMAIN EFFECTS`. Keep `--seed/--world/--command/--qty`. | Meets AC 4; default readable. | Single-mode rejected. |
| 9 | **File layout** | `domain/trace.py` — add `OutcomeDriver`, tuples, valuation kinds (`quantity_value_effect`, `price_value_effect`, `wealth`), hardening with correct roots. `engine/turn.py` — add exact valuation nodes, tuples, story drivers with exact wealth-bps ranking, RNG validation. `engine/demo.py` — verbose flag. Re-export. No new modules. | Focused to domain+engine. | New `explanation.py` rejected. |
| 10 | **Test strategy — exact totals** | Extend `test_turn_kernel.py` minimally; add `test_causal_trace.py` for DAG/tuples/ranking/RNG/allowed-roots; add `test_explanation.py` for drought→wealth exact chain and `sum(impact_money)==wealth_delta`. New files flat under `backend/tests/`. | Proves AC 1–5 and exact invariant. | Monolithic file rejected. |

---

## Recommended Approach

Treat `trace.py` as the structural authority with exact valuation: define `value(qty,price_milli)` and split `wealth_delta` exactly into `cash_effect + quantity_value_effect + price_value_effect` with integer math, so every story driver's `impact_money` is one of those exact components and sums to `wealth_delta`. Make all sequences tuples, extend the graph to `quantity_value_effect`/`price_value_effect`/`wealth` with correct parents, and generate only applicable stories (e.g. `command_cost`, `farm_output`, `storage_constraint`, `supply_price`, `quantity_value_effect`, `price_revaluation`) then rank by exact `impact_bps` and keep top 3. Harden validator to allow `world`/`command` as roots regardless of delta. Validate RNG, keep determinism, surface concise story drivers vs verbose DAG.

---

## Work Plan

Order matters; each step unblocks the next. Checkpoints are where lints/types/tests are verified; do not batch all fixes at the end.

### 1. Confirm workspace & branch → unblocks all edits

- Verify Git writes work in the authoritative checkout:
  ```bash
  git rev-parse --show-toplevel  # .../game-historical-empire
  git status --short               # clean
  git branch --show-current        # section/4-causal-explanation
  ```
  If any Git write unexpectedly fails, stop and diagnose. Do not use `/tmp` or alternate repo as workaround.
- Deps (uv cache already fixed): `uv sync --project backend` → 50 passed before changes.
- Files: none. Depends: none.

### 2. Domain — formalize `OutcomeDriver`, tuples, valuation kinds, correct roots → unblocks engine

- File: `backend/app/domain/trace.py`
  - `CausalNode.parent_ids: tuple[str, ...] = Field(default_factory=tuple)`, `CausalTrace.nodes: tuple[CausalNode, ...]`, `OutcomeDriver.causal_node_ids: tuple[str, ...]`, `PlayerOutcome.drivers: tuple[OutcomeDriver, ...] = Field(max_length=3)`, `CausalEdge = tuple[str,str]`.
  - `OutcomeDriver(BaseModel, frozen=True)`: `id, label, kind, impact_money: int, impact_bps: int, reason_code, causal_node_ids: tuple[str,...]` (min_length 1). No approximate `delta_bps` mixing — ranking uses exact wealth fields.
  - `PlayerOutcome`: `wealth_delta, inventory_delta, price_delta, drivers: tuple[OutcomeDriver,...]` plus `top_drivers: tuple[str,...]` computed as `tuple(d.label for d in drivers)`.
  - Extend `CausalNode.kind` literal to include `quantity_value_effect`, `price_value_effect`, `wealth` (keep `world, command, capacity, cash, production, supply, price, inventory`).
  - Harden `CausalTrace` validator: unique ids, parent existence, parents-before-children, acyclic, allowed roots `world`/`command` always (even if `delta !=0`), `farm_capacity`/`storage_capacity` `()` only when `delta==0` and reason `..._unchanged`; otherwise must have parents. Validate `DomainEffect.delta == after-before`.
  - `CausalTrace.edges` computed `tuple[CausalEdge,...]` from `parent_ids`.
  - Re-export in `backend/app/domain/__init__.py`.
- Depends: #1. Validation: `uv run --project backend pyright` and `ruff check backend` clean.

### 3. Engine — exact wealth subgraph + story drivers + exact wealth-bps ranking + RNG validation → unblocks tests/demo

- File: `backend/app/engine/turn.py`
  - Top: validate `rng_context == state.to_turn_context()` else `ValueError`; consume `rng_for(...).random()` without driving price.
  - After settlement (`inventory_final`, `cash`, `new_price`, `before_*` known), compute exact valuation:

    ```python
    def _value(qty: int, price_milli: int) -> int:
        return qty * price_milli // 1000

    wealth_before = before_cash + _value(before_inventory, before_price)
    value_before = _value(before_inventory, before_price)
    value_after_quantity = _value(inventory_final, before_price)
    value_after = _value(inventory_final, new_price)
    quantity_value_effect = value_after_quantity - value_before
    price_value_effect = value_after - value_after_quantity
    cash_effect = cash - before_cash
    wealth_after = cash + value_after
    wealth_delta = cash_effect + quantity_value_effect + price_value_effect
    assert wealth_after - wealth_before == wealth_delta
    ```

  - Emit nodes (tuples):
    ```python
    nodes.append(CausalNode(id="quantity_value_effect", kind="quantity_value_effect",
        before=value_before, after=value_after_quantity, delta=quantity_value_effect,
        reason_code="inventory_quantity_change" if quantity_value_effect!=0 else "no_quantity_effect",
        parent_ids=("inventory","price")))  # price_before via price node
    nodes.append(CausalNode(id="price_value_effect", kind="price_value_effect",
        before=value_after_quantity, after=value_after, delta=price_value_effect,
        reason_code="price_revalued_stored_grain" if price_value_effect!=0 else "no_price_effect",
        parent_ids=("inventory","price")))
    nodes.append(CausalNode(id="cash_effect", kind="cash",
        before=before_cash, after=cash, delta=cash_effect,
        reason_code="cash_after_command", parent_ids=("cash_after_command",)))
    nodes.append(CausalNode(id="wealth", kind="wealth",
        before=wealth_before, after=wealth_after, delta=wealth_delta,
        reason_code="wealth_from_cash_and_valuation",
        parent_ids=("cash_effect","quantity_value_effect","price_value_effect")))
    effects.extend([... for quantity_value_effect, price_value_effect, wealth, cash_effect ...])
    ```
    Adjust parent ids to actual node ids present (`cash_after_command` already exists per command; if we keep `cash_effect` as wrapper, wealth parents are the three effects; alternative simpler: wealth parents `("cash_after_command","quantity_value_effect","price_value_effect")` — choose one and be consistent; document in docstring).
  - Convert all `parent_ids`/`nodes` to tuples; final `CausalTrace(nodes=tuple(nodes))`.
  - Build **applicable** story drivers (only if `impact_money !=0` or meaningful):
    - `command_cost`: `causal_node_ids=("command","cash_after_command")`, `impact_money=cash_effect`, `kind="cash"`, `label=f"Command {command.type} cost {abs(cash_effect)}"` (or `gained` if positive)
    - `farm_output`: `("world","farm_capacity","farm_output")`, `impact_money` is farm_output's contribution to `quantity_value_effect` if not storage-capped else 0 — but to keep exact, map farm_output story to `quantity_value_effect`'s portion that is farm-driven (if storage capped, `quantity_value_effect` may be 0, so farm_output driver will be discarded as zero)
    - `storage_constraint`: `("farm_output","inventory")`, `impact_money` is the capped excess that was lost, only if `inventory` was capped (`excess>0`)
    - `supply_price`: `("farm_output","supply","price_pressure","target_price","price")`, `impact_money=price_value_effect`
    - `inventory_quantity`: `("inventory","quantity_value_effect")`, `impact_money=quantity_value_effect`
    - `price_revaluation`: `("price","price_value_effect")`, `impact_money=price_value_effect` — if we already have supply_price covering price_value_effect, choose one story per effect to avoid double-count; simpler: candidates are exactly the three exact effects plus command: `cash_effect`, `quantity_value_effect`, `price_value_effect` (and optionally `farm_output` as narrative for quantity effect). But to preserve story richness, candidates should be at most one driver per exact effect, with `causal_node_ids` being the full path that explains that effect. So generate at most 4 candidates (`command_cost`, `farm_output+quantity`, `storage`, `supply_price`), filter `impact_money==0`, then rank.
    - For each candidate, `impact_bps = abs(impact_money)*10_000 // max(wealth_before,1)` (or `abs(impact_money)` if `wealth_before==0`), `sorted(..., key=lambda d: (-d.impact_bps, d.id))[:3]` → `tuple`.
  - Update `TURN_ORDER` docstring to `command -> production -> supply -> price -> settlement -> valuation`; keep determinism.
- Files: `backend/app/engine/turn.py`, `__init__.py`. Depends: #2.

### 4. CLI — concise story drivers + full debug trace

- File: `backend/app/engine/demo.py`
  - Add `--verbose` (`--debug` alias).
  - After `res = resolve_turn(...)`, print concise `PLAYER OUTCOME` (`wealth_delta == cash_effect+quantity+price` verified) + `WHY?` story drivers (`label`, `impact_money`, `impact_bps`, `causal_node_ids` path), then only if `--verbose` print `FULL CAUSAL TRACE` (including `quantity_value_effect`, `price_value_effect`, `wealth`) and `DOMAIN EFFECTS`.
- Depends: #3.

### 5. Tests — prove AC 1–5 plus exact totals and correct roots

- File: `backend/tests/test_causal_trace.py` (new, ~8 tests)
  - `test_every_important_node_has_parent_including_valuation`: 4 commands×2 worlds → ids `farm_output, supply, price_pressure, target_price, price, inventory, quantity_value_effect, price_value_effect, wealth, cash_after_command, cash_effect` have correct parents; `world`/`command` `()` regardless of delta; `farm_capacity` `()` only when `delta==0`; tuples.
  - `test_trace_immutable_tuples`: `isinstance(trace.nodes, tuple)` etc., `append` raises `AttributeError`.
  - `test_wealth_decomposition_exact`: `wealth_delta == cash_effect.delta + quantity_value_effect.delta + price_value_effect.delta` and each equals `DomainEffect` counterpart; integer math checked.
  - `test_wealth_graph_parents`: `quantity_value_effect` parents `("inventory","price")`, `price_value_effect` parents `("inventory","price")`, `wealth` parents `("cash_effect","quantity_value_effect","price_value_effect")` (or allowed variant).
  - `test_drivers_derived_from_trace_not_snapshot`: buy clamped — drivers subset of trace.
  - `test_driver_ranking_deterministic_exact_wealth_bps`: same inputs → identical tuple; shuffle → same.
  - `test_story_drivers_are_paths_and_filtered`: `len(drivers)<=3`, at least one has `len(causal_node_ids)>=3`, zero-impact stories absent (e.g. `hold` with `before_price==new_price` has no `price_revaluation` driver).
  - `test_trace_validates_dag_and_allowed_roots`: forward parent or duplicate id raises `ValidationError`; `command` with `delta!=0` and `parent_ids==()` is allowed; `farm_capacity` with `delta!=0` and `parent_ids==()` raises.
  - `test_rng_context_mismatch_raises`: `TurnContext(turn=999)` raises `ValueError`.
  - `test_storage_capped_zero_quantity_effect`: farm_output>0 but storage full → `quantity_value_effect` 0, farm story discarded, `price_value_effect` may still rank.
- File: `backend/tests/test_explanation.py` (new, ~3 tests)
  - `test_drought_to_wealth_structural_chain_exact`: ids `world, farm_output, supply, price_pressure, target_price, price, quantity_value_effect, price_value_effect, wealth` present and chain `world→farm_output→supply→price→price_value_effect→wealth` valid; `sum(driver.impact_money)==wealth_delta`.
  - `test_story_drivers_cover_wealth_chain`: drivers collectively reference `farm_output`, `price`, `wealth`; `drivers` sorted by `impact_bps`.
  - `test_concise_le_three_full_trace_preserved`: `len(drivers)<=3` while `len(trace.nodes)>=10`.
- Extend `test_turn_kernel.py`: update `test_player_outcome_drivers_deterministic_and_bounded` to check `tuple` and `top_drivers == tuple(d.label for d in drivers)` and `sum(d.impact_money for d in drivers)+discarded == wealth_delta` if applicable.
- Depends: #3.

### 6. Gates & handoff

- Run gates: `uv sync --project backend`, `uv run --project backend pytest -v`, `uv run --project backend ruff check backend`, `uv run --project backend pyright`, `uv run --project backend ruff format --check backend`.
- CLI: `uv run --project backend python backend/app/engine/demo.py --world drought --command hold` (concise) and `--verbose` (full).
- Update `STATE.md` (Section 4 COMPLETE, note exact valuation, tuples, exact wealth-bps stories, correct roots, RNG fix). Do not edit `BUILD_SPEC.md` Status until gates green.
- Commit and push: `git push -u origin section/4-causal-explanation`.
- Depends: #2–5.

Linear order: #1 → #2 → #3 → (#4 ∥ #5) → #6.

---

## Validation Plan

| Check | Command | Expected evidence |
|-------|---------|-------------------|
| Git writes | `git checkout -b section/4-causal-explanation && git branch --show-current` | `section/4-causal-explanation` (from `35fa70e`) |
| Gate install | `uv sync --project backend` | `Resolved 15 packages` |
| Gate unit | `uv run --project backend pytest -v` | `~59 passed` |
| Gate lint | `uv run --project backend ruff check backend` | `All checks passed` |
| Gate type | `uv run --project backend pyright` | `0 errors` |
| Gate format | `uv run --project backend ruff format --check backend` | `already formatted` |
| Valuation exact | `pytest backend/tests/test_causal_trace.py::test_wealth_decomposition_exact -v` | `PASSED` — sum equals wealth_delta |
| Valuation graph | `pytest backend/tests/test_causal_trace.py::test_wealth_graph_parents -v` | `PASSED` — quantity/price/wealth parents correct |
| Causal parents | `pytest backend/tests/test_causal_trace.py::test_every_important_node_has_parent_including_valuation -v` | `PASSED` |
| Tuples immutable | `pytest backend/tests/test_causal_trace.py::test_trace_immutable_tuples -v` | `PASSED` |
| Allowed roots | `pytest backend/tests/test_causal_trace.py::test_trace_validates_dag_and_allowed_roots -v` | `PASSED` — command allowed with delta |
| Drivers from trace | `pytest backend/tests/test_causal_trace.py::test_drivers_derived_from_trace_not_snapshot -v` | `PASSED` |
| Exact wealth-bps ranking | `pytest backend/tests/test_causal_trace.py::test_driver_ranking_deterministic_exact_wealth_bps -v` | `PASSED` |
| Story drivers filtered | `pytest backend/tests/test_causal_trace.py::test_story_drivers_are_paths_and_filtered -v` | `PASSED` — zero stories absent, len≤3 |
| Structural chain exact | `pytest backend/tests/test_explanation.py::test_drought_to_wealth_structural_chain_exact -v` | `PASSED` — chain via price_value_effect |
| CLI concise | `python backend/app/engine/demo.py --world drought --command hold` | `WHY?` with ≤3 story drivers, exact impacts sum to wealth_delta |
| CLI verbose | `python backend/app/engine/demo.py --world drought --command hold --verbose` | concise + `FULL CAUSAL TRACE` with `quantity_value_effect, price_value_effect, wealth` |

Highest-risk: `pyright` strict with `tuple` fields + `computed_field` + valuation nodes — run `pyright` after steps #2 and #3.

---

## Risks / Rollback

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Exact attribution requires careful integer math at old vs new price | Medium | Medium | Define `_value` helper, assert `wealth_after-wealth_before == sum(effects)` in `turn.py` and in test; rare edge of zero `wealth_before` handled via `max(1)` fallback only for `impact_bps`, not for `impact_money`. |
| Generating only applicable stories could yield 1–2 drivers, not 3 — reviewer expects 3 | Low | Low | Tests assert `len(drivers) <=3` and at least one story when wealth changes; document that zero-impact stories are discarded. |
| Validator too strict on farm_capacity/storage_capacity | Low | Low | Allow `world`/`command` always; allow `farm_capacity` `()` only when `delta==0`; otherwise require parents. |
| PlayerOutcome tuple migration breaks old test | Medium | Medium | Keep `top_drivers` computed tuple; update test. |
| `pyright` tuple literal issues | Low | Low | Use `tuple[str,...]` + `Field(default_factory=tuple)`. |

**Rollback:** `git checkout main -- backend/app/domain/trace.py backend/app/engine/turn.py backend/app/engine/demo.py backend/app/domain/__init__.py backend/tests/` + `rm backend/tests/test_causal_trace.py backend/tests/test_explanation.py` + `git checkout main -- docs/plans/2026-08-09-section-4-causal-explanation.md`.

---

## Open Questions

None — all decisions discoverable locally. Exact decomposition formula above is the approved contract for this section.

---

**Next:** Awaiting approval, then implementation on `section/4-causal-explanation` per Work Plan steps 2–6. Do not auto-advance to Section 5.
