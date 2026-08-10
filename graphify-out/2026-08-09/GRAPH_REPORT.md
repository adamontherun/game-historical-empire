# Graph Report - game-historical-empire  (2026-08-09)

## Corpus Check
- 53 files · ~67,401 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 224 nodes · 558 edges · 13 communities (10 shown, 3 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cf228b40`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- resolve_turn
- MarketState
- test_determinism.py
- GameState
- test_two_markets_route.py
- test_rounding.py
- test_invariants.py
- turn.py
- BaseModel
- test_sanity.py
- historical-empire-backend

## God Nodes (most connected - your core abstractions)
1. `resolve_turn()` - 65 edges
2. `PlayerCommand` - 54 edges
3. `GameState` - 34 edges
4. `MarketState` - 27 edges
5. `InventoryState` - 26 edges
6. `PlayerState` - 25 edges
7. `_base_state()` - 18 edges
8. `_base_state()` - 18 edges
9. `_base_state()` - 15 edges
10. `derive_seed()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `test_operation_capacity_non_negative()` --calls--> `OperationState`  [EXTRACTED]
  backend/tests/test_core_types.py → backend/app/domain/types.py
- `_sample_state()` --calls--> `InventoryState`  [EXTRACTED]
  backend/app/engine/demo.py → backend/app/domain/types.py
- `resolve_turn()` --calls--> `InventoryState`  [EXTRACTED]
  backend/app/engine/turn.py → backend/app/domain/types.py
- `_base_state()` --calls--> `InventoryState`  [EXTRACTED]
  backend/tests/test_causal_trace.py → backend/app/domain/types.py
- `test_frozen_models_reject_mutation()` --calls--> `InventoryState`  [EXTRACTED]
  backend/tests/test_core_types.py → backend/app/domain/types.py

## Import Cycles
- None detected.

## Communities (13 total, 3 thin omitted)

### Community 0 - "resolve_turn"
Cohesion: 0.11
Nodes (42): PlayerCommand, Player turn command — one major action per turn (Sections 3–5)., Resolve one deterministic turn. Order is explicit: command -> production ->…, resolve_turn(), _base_state(), Section 4 — causal trace hardening, exact wealth decomposition, and story…, Wealth delta must equal cash + purchase + harvest + price effects exactly., Drivers must reference trace nodes, not snapshot diff. (+34 more)

### Community 1 - "MarketState"
Cohesion: 0.16
Nodes (26): InventoryState, MarketState, PlayerState, Player grain inventory — single good grain for Sections 2-4., Player economic exposure — single source of truth for capacities. For Sections…, Regional grain market — one market, one good (grain) for Section 3., Tests for canonical economic types — AC #1, #2., test_canonical_values_are_int() (+18 more)

### Community 2 - "test_determinism.py"
Cohesion: 0.11
Nodes (28): Engine package — deterministic RNG and rounding., derive_seed(), make_rng(), Deterministic RNG substreams via stable hash. Spec: never use global random…, Derive deterministic int seed from key material via BLAKE2b. Canonical…, Create isolated random.Random from int seed — no global state. Args: seed: Int…, Convenience: derive seed from key material and return Random. Args: run_seed:…, rng_for() (+20 more)

### Community 3 - "GameState"
Cohesion: 0.09
Nodes (28): Domain package — re-exports canonical types., CausalNode, CausalTrace, DomainEffect, OutcomeDriver, PlayerOutcome, BaseModel, Causal trace, domain effects, and player outcome for Sections 4–5. Structural… (+20 more)

### Community 4 - "test_two_markets_route.py"
Cohesion: 0.11
Nodes (26): _base_state(), Section 5 — Two Markets and One Trade Route acceptance tests. AC 1: Home Valley…, AC3: Route capacity limits shipped quantity., AC5: Player can complete turn staying in Home Valley (no trade)., AC6: Same state+command+world+seed => identical result, including River and…, Command that creates trade access must be deterministic and cost cash., Ship without established route should be blocked and not move grain., TURN_ORDER must include river and route phases and valuation. (+18 more)

### Community 5 - "test_rounding.py"
Cohesion: 0.18
Nodes (17): apply_basis_points(), clamp_non_negative(), div_round_half_up(), mul_basis_points(), Deterministic integer rounding helpers for canonical economic math. All…, Multiply value by basis points (10_000 = 100%) with floor division.…, Alias for mul_basis_points — semantic for price adjustments., Integer division rounding half away from zero for positive denominators. For… (+9 more)

### Community 6 - "test_invariants.py"
Cohesion: 0.31
Nodes (10): _bounded_price(), Bound movement toward target_price within max_movement_bps of current., Integer-safe target price from supply/demand., _target_price(), Invariant and property tests for Section 3 — AC #2, #4., test_bounded_price_monotonic_with_supply(), test_demand_unchanged_cannot_reduce_target_when_supply_falls(), test_price_stays_positive_extreme() (+2 more)

### Community 7 - "turn.py"
Cohesion: 0.17
Nodes (13): River Route — single route between Home Valley and River Town (Section 5).…, RouteState, main(), _print_state(), CLI demo for Sections 4–5 — prints before state, command, world, causal chain,…, _sample_state(), _affordable_quantity(), _cost_for_quantity() (+5 more)

## Knowledge Gaps
- **1 isolated node(s):** `historical-empire-backend`
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `resolve_turn()` connect `resolve_turn` to `MarketState`, `test_determinism.py`, `GameState`, `test_two_markets_route.py`, `test_invariants.py`, `turn.py`?**
  _High betweenness centrality (0.400) - this node is a cross-community bridge._
- **Why does `GameState` connect `GameState` to `resolve_turn`, `MarketState`, `test_two_markets_route.py`, `test_invariants.py`, `turn.py`?**
  _High betweenness centrality (0.196) - this node is a cross-community bridge._
- **Why does `PlayerCommand` connect `resolve_turn` to `MarketState`, `GameState`, `test_two_markets_route.py`, `test_invariants.py`, `turn.py`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `GameState` (e.g. with `CausalNode` and `CausalTrace`) actually correct?**
  _`GameState` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `historical-empire-backend` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `resolve_turn` be split into smaller, more focused modules?**
  _Cohesion score 0.10638297872340426 - nodes in this community are weakly interconnected._
- **Should `test_determinism.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11088709677419355 - nodes in this community are weakly interconnected._