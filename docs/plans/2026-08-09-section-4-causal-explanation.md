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

1. **Every important state change has a causal parent — including wealth.** After `resolve_turn`, each node that represents a mutated canonical value (`cash`, `farm_capacity`, `storage_capacity`, `farm_output`, `supply`, `price_pressure`, `target_price`, `price`, `inventory`, `inventory_value`, `wealth`) lists ≥1 `parent_ids` that resolves to an earlier node, the graph is acyclic, ids are unique, parents are tuples, and parents appear before children in `trace.nodes` emission order. Pure diagnostic nodes (`world`) may have `()`. Explicitly, `inventory_value` must have parents `(inventory, price)` and `wealth` must have parents `(cash, inventory_value)` (or `(cash_after_command, inventory_value)`), closing the chain.
2. **Drivers derived from trace, not snapshot diff.** `PlayerOutcome.drivers: tuple[OutcomeDriver, ...]` (with deprecated `top_drivers: tuple[str, ...]` derived) is computed only from `CausalTrace` nodes/effects — no `next_state - before_state` guessing. Proof: a test mutates only one intermediate node vs. a snapshot-diff approach and asserts drivers diverge if diff were used; main proof is code inspection + a test that drivers reference trace `reason_code`/`id`.
3. **Driver ranking is deterministic.** Same `state + command + world + seed` → identical ranked driver tuple, byte-for-byte. Implementation uses a total order `(impact_bps DESC, id ASC)` with no `random`/`hash()`/`set` iteration. Tested by calling `resolve_turn` twice and by shuffling candidate construction order in a helper and re-sorting.
4. **CLI shows both concise and full trace.** `uv run --project backend python -m app.engine.demo --world drought --command hold [--verbose]` prints (a) concise section: `WHY?` with 1–3 driver sentences + wealth/inventory/price deltas, and (b) verbose/debug section: full `CausalTrace` nodes in emission order with `before/after/delta/reason_code/parents` and `DomainEffect` list. Default should show concise; `--verbose` / `--debug` shows both. AC 4 satisfied when both are visible in one invocation without code edits.
5. **Multi-step chain test: drought → wealth effect — structurally.** At least one test asserts the full structural chain `world(drought) → farm_output(reduced) → supply(lower than normal) → price_pressure → price(increase) → inventory_value → wealth` with typed `OutcomeDriver` entries. Each driver must reference its supporting `causal_node_ids` (tuple) that are a subset of `CausalTrace` ids, and the wealth node must be parented by `inventory_value`+`cash`, not merely computed after resolution. Test uses `turn=0, farm=10, supply=100, demand=120, inventory=20, storage=100` sample.
6. **Section 3 follow-ups resolved before COMPLETE:**
   - Raw `abs(delta)` ranking replaced by **wealth-bps ranking** (impact on player wealth in basis points of pre-turn wealth). New test demonstrates the old bug: raw price milliunits vs grain magnitude no longer decides ranking; only `impact_bps` does.
   - Trace graph shape hardened with validators (unique ids, parent existence, acyclic, ordering) and **immutable tuples** for all sequence fields. `pyright` strict and `ruff` still pass.
   - RNG context ownership fixed: `resolve_turn` either derives `TurnContext` from `state` internally or validates `rng_context == state.to_turn_context()`; caller desync raises `ValueError`. No jitter added merely because a substream exists. Tested.

---

## Context And Current Facts

- `main` at `35fa70e` (squashed Section 3). `STATE.md` marks Section 3 COMPLETE — 50 tests green (`8 core + 7 rounding + 11 determinism + 15 kernel + 7 invariants + 2 purity/sanity`), `ruff` + `pyright` strict pass. `BUILD_SPEC.md` Section 4 is `NOT STARTED`.
- **Current domain (`backend/app/domain/types.py:1`):** `Money/Quantity/PriceMilliunits/BasisPoints` via `Annotated[int, Field(ge=0, strict=True)]` etc., `InventoryState{grain}`, `OperationState{id,kind,capacity,level}`, `PlayerState{cash, inventory, farm_capacity, storage_capacity}`, `MarketState{supply,demand,base_price,current_price,responsiveness=5000,max_movement_bps=2000}`, `TurnContext{turn,run_seed,ruleset_version}`, `WorldCondition = Literal["normal","drought"]`, `PlayerCommand{type, quantity?}`, `GameState{turn,run_seed,ruleset_version,player,market}` with `to_turn_context()`. All frozen via `ConfigDict(frozen=True)`.
- **Current trace (`backend/app/domain/trace.py:1`):** `CausalNode{id,label,kind,before,after,delta,reason_code,parent_ids: list[str]}`, `CausalTrace{nodes: list[CausalNode]}`, `DomainEffect{metric,before,after,delta,reason_code}`, `PlayerOutcome{wealth_delta,inventory_delta,price_delta,top_drivers: list[str]}`, `TurnResolution{next_state,domain_effects,causal_trace,player_outcome}`. No `OutcomeDriver` type, no `inventory_value`/`wealth` nodes, mutable lists.
- **Current engine (`backend/app/engine/turn.py:1`):** `resolve_turn(state, command, world, rng_context)` with explicit `TURN_ORDER = "command -> production -> supply -> price -> settlement"`. Integer-safe market math via `rounding.py`. Drought correctly reduces `farm_output` rather than price. Buy clamped via `min(requested, affordable, space)`. RNG substream consumed but core price deterministic. Trace emission is structural but stops at `inventory` — wealth is computed as `cash + inventory*price//1000` only for `PlayerOutcome`, not as graph nodes `inventory_value`/`wealth`. Ranking is `sorted by abs(delta)` over raw nodes — the documented follow-up bug.
- **Purity and tooling:** `tests/test_engine_purity.py` forbids forbidden imports; `tests/test_determinism.py` bans global `random.*` and `hash()`. `pyproject.toml` has `pydantic>=2.7`, `pytest>=9`, `ruff>=0.8`, `pyright>=1.1 strict`, `python >=3.12`. Makefile wrappers are `make test`→`uv run --project backend pytest -v`, etc. Gates green.
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
| 1 | **Wealth as causal graph, not just outcome math** | Add explicit nodes `inventory_value` and `wealth` to the trace. Structure: `inventory ─┐ → inventory_value ─┐ → wealth` and `price ──────┘` and `cash ───────────────┘`. Extend `TURN_ORDER` to `command -> production -> supply -> price -> settlement -> valuation` (or keep order string but document valuation as final step). Nodes: `inventory_value: before=before_inventory*before_price//1000, after=inventory_final*new_price//1000, delta=after-before, parent_ids=("inventory","price"), reason="inventory_revalued"`; `wealth: before=before_cash+before_value, after=cash+after_value, delta=after-before, parent_ids=("cash_after_command","inventory_value")` (or `("cash_after_command","inventory_value")`), `reason="wealth_from_cash_and_inventory_value"`. `DomainEffect` entries for `inventory_value` and `wealth` added alongside existing effects. | Closes the structural gap flagged in feedback: AC 5 requires `drought → ... → price → player wealth effect` as a causal chain, not a post-hoc arithmetic summary. With `inventory_value`+`wealth` nodes, the full path `drought → farm_output → supply → price_pressure → target_price → price → inventory_value → wealth` exists as parent links, making the explanation authoritative evidence rather than reconstructed arithmetic. | Keep wealth only as `PlayerOutcome.wealth_delta` arithmetic rejected — leaves final link optional and not traceable via `causal_node_ids`. Add only `wealth` without `inventory_value` rejected — `wealth` would then depend directly on `price`+`inventory`, collapsing two distinct economic phenomena (inventory quantity vs price revaluation) into one node. |
| 2 | **Immutable tuples for frozen causal models** | Use `tuple` for all sequence fields in frozen models: `CausalNode.parent_ids: tuple[str, ...]`, `CausalTrace.nodes: tuple[CausalNode, ...]`, `OutcomeDriver.causal_node_ids: tuple[str, ...]`, `PlayerOutcome.drivers: tuple[OutcomeDriver, ...]`, `CausalTrace.edges` computed as `tuple[CausalEdge, ...]`. Keep `ConfigDict(frozen=True)` — now contents cannot be mutated via `.append()`. Construct with `tuple(...)` in `turn.py`. | `frozen=True` only freezes attribute reassignment, not list contents; mutable lists would allow `trace.nodes.append(...)` or `node.parent_ids.append("bogus")` to silently invalidate the DAG after validation. Tuples make the trace authoritative and tamper-evident. | Keep `list[str]` rejected — mutable, violates "authoritative evidence" requirement. Use `frozen` plus custom `__setitem__` guard rejected — more code, less idiomatic than tuples; Pydantic already handles `tuple` validation cleanly. |
| 3 | **OutcomeDriver as causal path/story, not single node** | Define `OutcomeDriver` as a **story grouping multiple causal nodes**: `id: str` (e.g. `drought_farm_output`, `supply_price`, `inventory_value_wealth`), `label: str` (player-facing sentence), `kind: str`, `impact_money: int` (contribution to wealth), `impact_bps: int` (basis points of `wealth_before`), `reason_code: str`, `causal_node_ids: tuple[str, ...]` (ordered path). Build exactly 3 canonical drivers per turn (or fewer if wealth_before is 0): Driver 1 `world → farm_output` (`Drought reduced farm output by X%`), Driver 2 `farm_output → supply → price_pressure → target_price → price` (`Lower regional supply pushed grain prices higher/lower`), Driver 3 `price + inventory → inventory_value → wealth` plus `cash` contribution (`Higher/lower prices changed the value of your stored grain, partially offsetting ...`). Drivers are constructed from trace, not from scanning individual nodes for largest delta. | Prevents the failure mode where top drivers are three nodes on the same price phenomenon (`supply fell`, `price pressure rose`, `target price rose`) — three labels for one story. Story grouping matches Section 4's player-facing goal: `≤3 primary causal drivers in the main reveal` should be distinct economic narratives. Reviewer feedback explicitly prefers this. | One-driver-per-node ranking rejected — produces redundant drivers on one chain. Single `label` string without `causal_node_ids` rejected — loses trace linkage. |
| 4 | **Driver ranking in one common unit: wealth-bps** | Ranking key is **impact on player wealth in basis points of pre-turn wealth**: `wealth_before = before_cash + before_inventory*before_price//1000` (≥1); for each driver compute `impact_money` (signed contribution to `wealth_delta`; e.g. for farm-output driver `impact_money = (farm_output_drought - farm_output_normal)*new_price//1000` or more simply `delta*new_price//1000` for production-related, for price driver `impact_money = inventory_final*price_delta//1000` or the portion attributable to price, for cash driver `impact_money = cash_delta`), then `impact_bps = abs(impact_money)*10_000 // max(wealth_before,1)`. Sort by `(-impact_bps, id)` and slice `[:3]`. If `wealth_before == 0`, fallback to `abs(impact_money)` with same tie-breaker. Document formula in `turn.py` docstring. | Simplifies the prior mixed `delta_bps + impact_money + kind weights` proposal which could still produce arbitrary cross-unit comparisons. Single-unit wealth-bps makes every driver comparable: a -40 grain farm loss worth -200 money at price 5000 and pre-wealth 2000 is `1000 bps`, a +600 milliunit price rise on 20 grain inventory is `+600 bps`, so farm loss outranks price move purely by wealth impact, deterministically. | Rank by `delta_bps` per-node rejected — still cross-unit (grain bps vs price bps). Rank by `abs(delta)` raw rejected — known bug. Kind-weighted table rejected — ad-hoc, not grounded. |
| 5 | **CausalEdge vs parent_ids** | Keep `CausalNode.parent_ids: tuple[str, ...]` as canonical; add alias `CausalEdge = tuple[str, str]` and computed `CausalTrace.edges: tuple[CausalEdge, ...]` derived from `parent_ids`. Do not persist separate edge list. | Satisfies "CausalEdge or parent reference" with single source of truth; minimal diff; backward compatible after tuple migration. | Separate mutable edge list rejected — dual source. |
| 6 | **Trace hardening & validation** | Add `CausalTrace` `@model_validator(mode="after")` enforcing: ids unique, every `parent_id` resolves to a preceding node id, no self-cycle, parents-before-children, and every node except `world` with `delta` non-None has parents (or is explicitly allowed root `command`/`farm_capacity` when `delta==0`). Also validate `DomainEffect.delta == after - before` and `CausalNode.delta == after - before` when both present. Validate tuples immutably. | Hardens DAG; turns silent bugs into loud `ValidationError`. Cheap (≤14 nodes). | No validation rejected — weak AC 1. Networkx rejected — overkill. |
| 7 | **RNG context ownership** | Keep `resolve_turn(state, command, world, rng_context)` but validate `expected = state.to_turn_context(); if rng_context != expected: raise ValueError(...)`. Consume substream deterministically but do not drive price. | Fixes follow-up without breaking 15 kernel tests that pass `state.to_turn_context()`. | Ignore mismatch silently rejected. Remove param now rejected (breaks tests). Add jitter rejected. |
| 8 | **CLI — concise vs full trace** | Extend `demo.py` with `--verbose/--debug` flag: concise prints `PLAYER OUTCOME` + `WHY?` with ≤3 `OutcomeDriver.label`s and `impact_bps`; verbose adds `FULL CAUSAL TRACE` (nodes with `before/after/delta/reason/parents`) and `DOMAIN EFFECTS` including `inventory_value`/`wealth`. Also print drivers structured `id, impact_money, impact_bps, causal_node_ids`. Keep `--seed/--world/--command/--qty`. | Meets AC 4; keeps default readable. | Single-mode verbose-only rejected. Rich dep rejected. |
| 9 | **File layout** | `domain/trace.py` — add `OutcomeDriver`, switch lists to tuples, add `inventory_value`/`wealth` kinds, harden validators. `engine/turn.py` — add wealth nodes, switch to tuples, add story drivers + wealth-bps ranking, RNG validation. `engine/demo.py` — verbose flag + driver rendering. Re-export in `__init__.py`s. No new modules. | Focused to domain+engine (≤3 files). | New `explanation.py` rejected (no second consumer yet). |
| 10 | **Test strategy** | Extend `test_turn_kernel.py` minimally; add `test_causal_trace.py` for DAG/tuple/ranking/RNG; add `test_explanation.py` for drought→wealth structural chain via `wealth` node and story drivers. New files flat under `backend/tests/`. | Proves AC 1–5 + follow-ups; keeps 50 existing green. | Monolithic test file rejected. |

---

## Recommended Approach

Treat `trace.py` as the structural authority: add `OutcomeDriver` as a story/path over tuples of node ids, make every sequence field a `tuple`, and extend the causal graph to include `inventory_value` → `wealth` so the engine's wealth arithmetic is itself a causal subgraph. Move driver selection into `turn.py` as a pure function that builds three canonical stories from trace segments and ranks them solely by `impact_bps = abs(impact_money)*10000//wealth_before` (tie-break `id ASC`). Validate RNG context, keep determinism, and surface concise/story drivers vs verbose DAG in `demo.py`. Do not add new economic mechanics — only explanation fidelity.

---

## Work Plan

Order matters; each step unblocks the next. Checkpoints are where lints/types/tests are verified; do not batch all fixes at the end.

### 1. Confirm workspace & branch → unblocks all edits

- Verify Git writes work in the authoritative checkout:
  ```bash
  git rev-parse --show-toplevel  # .../game-historical-empire
  git status --short               # clean
  git branch --show-current        # main
  git checkout -b section/4-causal-explanation
  git branch --show-current        # section/4-causal-explanation
  ```
  If any Git write unexpectedly fails, stop and diagnose the environment. Do not use `/tmp` or an alternate repo as a Git workaround.
- Install deps (cache workaround is for uv cache only, unrelated to Git):
  ```bash
  UV_CACHE_DIR=/tmp/uv-cache uv sync --project backend
  UV_CACHE_DIR=/tmp/uv-cache uv run --project backend pytest -v  # 50 passed before changes
  ```
- Files: none (branch only). Depends: none.

### 2. Domain — formalize `OutcomeDriver`, tuples, and wealth kinds → unblocks engine

- File: `backend/app/domain/trace.py`
  - Change `CausalNode.parent_ids: tuple[str, ...] = Field(default_factory=tuple)` and `CausalTrace.nodes: tuple[CausalNode, ...]`, `DomainEffect` unchanged, add `OutcomeDriver(BaseModel, frozen=True)` with `id: str`, `label: str`, `kind: str`, `impact_money: int`, `impact_bps: int`, `reason_code: str`, `causal_node_ids: tuple[str, ...]` (min_length 1), plus optional `delta/delta_bps` if useful (or omit to keep single-unit ranking pure). Use `ConfigDict(frozen=True)`.
  - Update `PlayerOutcome` to `drivers: tuple[OutcomeDriver, ...] = Field(max_length=3)` plus existing `wealth_delta, inventory_delta, price_delta`; keep `top_drivers: tuple[str, ...]` as `@computed_field` returning `tuple(d.label for d in drivers)` for compat (or property).
  - Extend `CausalNode.kind` literal to include `inventory_value` and `wealth` (and keep existing kinds).
  - Harden `CausalTrace` validator: unique ids, parent existence, parents-before-children, no cycles, every non-world node with meaningful delta has parents; validate `DomainEffect.delta == after - before`.
  - Add `CausalEdge = tuple[str, str]` alias and `CausalTrace.edges` computed property returning tuple of edges from `parent_ids`.
  - Update `backend/app/domain/__init__.py` to re-export `OutcomeDriver`, `CausalEdge`.
- Depends: #1. Validation: `UV_CACHE_DIR=/tmp/uv-cache uv run --project backend pyright` and `ruff check backend` clean.

### 3. Engine — wealth subgraph + story drivers + wealth-bps ranking + RNG validation → unblocks tests/demo

- File: `backend/app/engine/turn.py`
  - Top: validate `rng_context == state.to_turn_context()` else `ValueError`; consume `rng_for(...).random()` without driving price.
  - After settlement (`inventory_final`, `cash`, `new_price` known), emit:
    ```python
    wealth_before = before_cash + before_inventory*before_price//1000
    inv_value_before = before_inventory*before_price//1000
    inv_value_after = inventory_final*new_price//1000
    wealth_after = cash + inv_value_after
    nodes.append(CausalNode(id="inventory_value", kind="inventory_value",
        before=inv_value_before, after=inv_value_after, delta=inv_value_after-inv_value_before,
        reason_code="price_revalued_stored_grain" if price_delta!=0 else "inventory_change",
        parent_ids=("inventory","price")))
    nodes.append(CausalNode(id="wealth", kind="wealth",
        before=wealth_before, after=wealth_after, delta=wealth_after-wealth_before,
        reason_code="wealth_from_cash_and_inventory_value",
        parent_ids=("cash_after_command","inventory_value")))
    effects.append(DomainEffect(metric="inventory_value", before=inv_value_before, after=inv_value_after, delta=...))
    effects.append(DomainEffect(metric="wealth", before=wealth_before, after=wealth_after, delta=...))
    ```
    Ensure `cash_after_command` node id exists (already emitted for every command).
  - Convert all `parent_ids` and `nodes` constructions to tuples: `parent_ids=("world","farm_capacity")` etc., final `CausalTrace(nodes=tuple(nodes))`.
  - Build 3 story drivers from trace segments:
    - D1 `world → farm_output` (covers drought vs normal yield)
    - D2 `farm_output → supply → price_pressure → target_price → price` (supply-price chain)
    - D3 `price + inventory → inventory_value → wealth` plus cash contribution (or `cash_after_command + inventory_value → wealth`)
    For each, compute `impact_money` as that story's contribution to `wealth_after - wealth_before` (e.g. D1: `farm_output_delta * new_price //1000` capped by storage, D2: `price_delta * inventory_final //1000` plus supply-driven price portion, D3: residual or explicit inventory_value delta + cash delta). Keep it simple and deterministic; document approximation in docstring. If exact attribution is ambiguous, attribute inventory_value delta to D3 and cash delta to D3 as well, while D1/D2 get their marginal price/farm impacts — key is that ranking by `impact_bps` compares same-unit wealth contributions.
    - Compute `impact_bps = abs(impact_money)*10_000 // max(wealth_before,1)` and `sorted(drivers, key=lambda d: (-d.impact_bps, d.id))[:3]` → `tuple`.
  - Update docstring for `resolve_turn` to describe wealth subgraph and wealth-bps ranking; keep `TURN_ORDER` but note valuation step: `"command -> production -> supply -> price -> settlement -> valuation"`.
- Files: `backend/app/engine/turn.py`, optional `__init__.py` re-exports. Depends: #2.

### 4. CLI — concise story drivers + full debug trace

- File: `backend/app/engine/demo.py`
  - Add `--verbose` (`--debug` alias) flag.
  - After `res = resolve_turn(...)`, print concise `PLAYER OUTCOME` + `WHY?` numbered story drivers (`label`, `impact_money`, `impact_bps`, `nodes=causal_node_ids`), then only if `--verbose` print `FULL CAUSAL TRACE` (including `inventory_value`, `wealth`) and `DOMAIN EFFECTS`.
- Depends: #3.

### 5. Tests — prove AC 1–5 + follow-ups with tuples and wealth graph

- File: `backend/tests/test_causal_trace.py` (new, ~7 tests)
  - `test_every_important_node_has_parent_including_wealth`: 4 commands ×2 worlds → every id in (`farm_output`,`supply`,`price_pressure`,`target_price`,`price`,`inventory`,`inventory_value`,`wealth`,`cash_after_command`) has `parent_ids != ()` and parents exist; ids unique; parents before children; `inventory_value` parents `("inventory","price")`; `wealth` parents `("cash_after_command","inventory_value")`; tuples are `tuple` type.
  - `test_trace_immutable_tuples`: `isinstance(trace.nodes, tuple)` and `isinstance(node.parent_ids, tuple)` and mutating via `append` raises `AttributeError`.
  - `test_drivers_derived_from_trace_not_snapshot`: buy clamped by storage vs cash — drivers' `causal_node_ids` subset of trace ids and `reason_code` matches.
  - `test_driver_ranking_deterministic_wealth_bps`: same inputs → identical `drivers` tuple; shuffle helper → same order.
  - `test_ranking_is_wealth_bps_not_raw`: craft state where raw `price_delta` 800 > `farm_output_delta` 40 but wealth-bps ranking puts farm story first; assert order.
  - `test_story_drivers_are_paths_not_single_nodes`: `len(drivers) <=3` and at least one driver has `len(causal_node_ids) >=3` (the supply-price chain); no driver is duplicate coverage of same single node.
  - `test_trace_validates_dag_and_tuples`: forward parent reference or duplicate id raises `ValidationError`.
  - `test_rng_context_mismatch_raises`: `TurnContext(turn=999)` raises `ValueError`.
- File: `backend/tests/test_explanation.py` (new, ~3 tests)
  - `test_drought_to_wealth_structural_chain`: assert ids `world, farm_output, supply, price_pressure, target_price, price, inventory_value, wealth` all present and parent chain `world→farm_output→supply→price→inventory_value→wealth` valid via `parent_ids`; `wealth_before/after` matches formula.
  - `test_story_drivers_cover_wealth_chain`: drivers collectively reference `farm_output`, `price`, and `wealth`/`inventory_value` nodes; `drivers[0].impact_bps` is wealth-bps.
  - `test_concise_le_three_full_trace_preserved`: `len(drivers) <=3` while `len(trace.nodes) >=8` and chain intact.
- Extend `test_turn_kernel.py` minimally: update `test_player_outcome_drivers_deterministic_and_bounded` to check `tuple` type and `top_drivers == tuple(d.label for d in drivers)`.
- Depends: #3.

### 6. Gates & handoff

- Run gates (cache prefix for uv cache only):
  ```bash
  UV_CACHE_DIR=/tmp/uv-cache uv sync --project backend
  UV_CACHE_DIR=/tmp/uv-cache uv run --project backend pytest -v
  UV_CACHE_DIR=/tmp/uv-cache uv run --project backend ruff check backend
  UV_CACHE_DIR=/tmp/uv-cache uv run --project backend pyright
  UV_CACHE_DIR=/tmp/uv-cache uv run --project backend ruff format --check backend
  ```
- CLI: `UV_CACHE_DIR=/tmp/uv-cache uv run --project backend python backend/app/engine/demo.py --world drought --command hold` (concise) and `--verbose` (full).
- Update `STATE.md` (Section 4 COMPLETE, note wealth subgraph, tuples, wealth-bps stories, RNG fix). Do not edit `BUILD_SPEC.md` Status until gates green.
- Commit and push: `git push -u origin section/4-causal-explanation`.
- Depends: #2–5.

Linear order: #1 → #2 → #3 → (#4 ∥ #5) → #6.

---

## Validation Plan

| Check | Command (cache prefix for uv cache only) | Expected evidence |
|-------|------------------------------------------|-------------------|
| Git writes | `git checkout -b section/4-causal-explanation && git branch --show-current` | `section/4-causal-explanation` |
| Gate install | `UV_CACHE_DIR=/tmp/uv-cache uv sync --project backend` | `Resolved 15 packages` |
| Gate unit | `UV_CACHE_DIR=/tmp/uv-cache uv run --project backend pytest -v` | `~59 passed` (50 + ~9 new) |
| Gate lint | `UV_CACHE_DIR=/tmp/uv-cache uv run --project backend ruff check backend` | `All checks passed` |
| Gate type | `UV_CACHE_DIR=/tmp/uv-cache uv run --project backend pyright` | `0 errors` |
| Gate format | `UV_CACHE_DIR=/tmp/uv-cache uv run --project backend ruff format --check backend` | `already formatted` |
| Causal parents inc wealth | `pytest backend/tests/test_causal_trace.py::test_every_important_node_has_parent_including_wealth -v` | `PASSED` |
| Tuples immutable | `pytest backend/tests/test_causal_trace.py::test_trace_immutable_tuples -v` | `PASSED` |
| Drivers from trace | `pytest backend/tests/test_causal_trace.py::test_drivers_derived_from_trace_not_snapshot -v` | `PASSED` |
| Wealth-bps ranking | `pytest backend/tests/test_causal_trace.py::test_driver_ranking_deterministic_wealth_bps -v` | `PASSED` |
| Story drivers | `pytest backend/tests/test_causal_trace.py::test_story_drivers_are_paths_not_single_nodes -v` | `PASSED` |
| Structural chain | `pytest backend/tests/test_explanation.py::test_drought_to_wealth_structural_chain -v` | `PASSED` — chain ids present via parent_ids |
| CLI concise | `python backend/app/engine/demo.py --world drought --command hold` | `WHY?` with ≤3 story drivers, `wealth` |
| CLI verbose | `python backend/app/engine/demo.py --world drought --command hold --verbose` | concise + `FULL CAUSAL TRACE` with `inventory_value, wealth` |

Highest-risk: `pyright` strict with `tuple` fields + `computed_field` + `inventory_value`/`wealth` nodes — run `pyright` after step #2 and #3.

---

## Risks / Rollback

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Uv cache still broken (`~/.cache/uv/sdists-v9/.git`) | High | Low | Keep `UV_CACHE_DIR=/tmp/uv-cache` prefix for all `uv` invocations; fix outside Muse with `xattr -d ...; rm -f ...` |
| PlayerOutcome tuple migration breaks existing test | Medium | Medium | Keep `top_drivers` as computed tuple; update test to assert `tuple(d.label for d in drivers)` |
| Wealth attribution (splitting `wealth_delta` into story `impact_money`) is judgment | Medium | Medium | Document approximation in `turn.py`; test only that sum of `impact_money` is close to `wealth_delta` and ranking is deterministic, not exact decomposition |
| Trace validator too strict on zero-delta roots | Low | Low | Allow `farm_capacity` with `parent_ids==()` when `delta==0` |
| `pyright` tuple literal issues | Low | Low | Use `tuple[str, ...]` + `Field(default_factory=tuple)` explicitly |

**Rollback:** `git checkout main -- backend/app/domain/trace.py backend/app/engine/turn.py backend/app/engine/demo.py backend/app/domain/__init__.py backend/tests/` + `rm backend/tests/test_causal_trace.py backend/tests/test_explanation.py` + `git checkout main -- docs/plans/2026-08-09-section-4-causal-explanation.md`.

---

## Open Questions

None — all decisions discoverable locally. If reviewer prefers exact wealth decomposition formula different, note as follow-up; AC satisfied as long as drivers are wealth-bps ranked stories parented by trace.

---

**Next:** Awaiting approval, then implementation on `section/4-causal-explanation` per Work Plan steps 2–6. Do not auto-advance to Section 5.
