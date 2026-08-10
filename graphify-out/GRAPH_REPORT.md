# Graph Report - game-historical-empire  (2026-08-09)

## Corpus Check
- 53 files · ~67,712 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 375 nodes · 687 edges · 34 communities (23 shown, 11 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `797e8012`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_two_markets_route.py
- GameState
- test_determinism.py
- trace.py
- What You Must Do When Invoked
- test_rounding.py
- test_invariants.py
- What You Must Do When Invoked
- BaseModel
- test_sanity.py
- historical-empire-backend
- resolve_turn
- Historical Empire — Agent Guide
- graphify reference: extra exports and benchmark
- Section 5 — COMPLETE (2026-08-09)
- graphify reference: extra exports and benchmark
- graphify reference: query, path, explain
- graphify reference: query, path, explain
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native AGENTS.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- .agents/skills/graphify/references/extraction-spec.md
- CLAUDE.md
- .claude/CLAUDE.md
- .claude/skills/graphify/references/extraction-spec.md

## God Nodes (most connected - your core abstractions)
1. `resolve_turn()` - 65 edges
2. `PlayerCommand` - 54 edges
3. `GameState` - 34 edges
4. `MarketState` - 27 edges
5. `InventoryState` - 26 edges
6. `PlayerState` - 25 edges
7. `_base_state()` - 18 edges
8. `_base_state()` - 18 edges
9. `Historical Empire — Agent Guide` - 15 edges
10. `_base_state()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `CausalNode` --uses--> `GameState`  [INFERRED]
  backend/app/domain/trace.py → backend/app/domain/types.py
- `CausalTrace` --uses--> `GameState`  [INFERRED]
  backend/app/domain/trace.py → backend/app/domain/types.py
- `DomainEffect` --uses--> `GameState`  [INFERRED]
  backend/app/domain/trace.py → backend/app/domain/types.py
- `OutcomeDriver` --uses--> `GameState`  [INFERRED]
  backend/app/domain/trace.py → backend/app/domain/types.py
- `PlayerOutcome` --uses--> `GameState`  [INFERRED]
  backend/app/domain/trace.py → backend/app/domain/types.py

## Import Cycles
- None detected.

## Communities (34 total, 11 thin omitted)

### Community 0 - "test_two_markets_route.py"
Cohesion: 0.10
Nodes (28): _base_state(), Section 5 — Two Markets and One Trade Route acceptance tests. AC 1: Home Valley…, AC3: Route capacity limits shipped quantity., AC4: Profitability depends on market supply/demand divergence, not scripted…, AC5: Player can complete turn staying in Home Valley (no trade)., AC6: Same state+command+world+seed => identical result, including River and…, Command that creates trade access must be deterministic and cost cash., Ship without established route should be blocked and not move grain. (+20 more)

### Community 1 - "GameState"
Cohesion: 0.12
Nodes (40): Domain package — re-exports canonical types., GameState, InventoryState, MarketState, OperationState, PlayerState, Canonical economic types for Sections 2-5. Integer-only canonical state per…, Lightweight turn identity for RNG derivation. (+32 more)

### Community 2 - "test_determinism.py"
Cohesion: 0.11
Nodes (28): Engine package — deterministic RNG and rounding., derive_seed(), make_rng(), Deterministic RNG substreams via stable hash. Spec: never use global random…, Derive deterministic int seed from key material via BLAKE2b. Canonical…, Create isolated random.Random from int seed — no global state. Args: seed: Int…, Convenience: derive seed from key material and return Random. Args: run_seed:…, rng_for() (+20 more)

### Community 3 - "trace.py"
Cohesion: 0.11
Nodes (19): CausalNode, CausalTrace, DomainEffect, OutcomeDriver, PlayerOutcome, BaseModel, Causal trace, domain effects, and player outcome for Sections 4–5. Structural…, Player-visible economic effect derived from trace. (+11 more)

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native AGENTS.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 5 - "test_rounding.py"
Cohesion: 0.18
Nodes (17): apply_basis_points(), clamp_non_negative(), div_round_half_up(), mul_basis_points(), Deterministic integer rounding helpers for canonical economic math. All…, Multiply value by basis points (10_000 = 100%) with floor division.…, Alias for mul_basis_points — semantic for price adjustments., Integer division rounding half away from zero for positive denominators. For… (+9 more)

### Community 6 - "test_invariants.py"
Cohesion: 0.31
Nodes (10): _bounded_price(), Bound movement toward target_price within max_movement_bps of current., Integer-safe target price from supply/demand., _target_price(), Invariant and property tests for Section 3 — AC #2, #4., test_bounded_price_monotonic_with_supply(), test_demand_unchanged_cannot_reduce_target_when_supply_falls(), test_price_stays_positive_extreme() (+2 more)

### Community 7 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 13 - "resolve_turn"
Cohesion: 0.09
Nodes (48): PlayerCommand, Player turn command — one major action per turn (Sections 3–5)., _affordable_quantity(), _cost_for_quantity(), Resolve one deterministic turn. Order is explicit: command -> production ->…, Cost in Money for quantity at price_milli (milliunits per unit). Floor division…, Max quantity affordable at price_milli with cash, floored cost., Inventory value in Money at price_milli. (+40 more)

### Community 14 - "Historical Empire — Agent Guide"
Cohesion: 0.12
Nodes (15): 10. API Contract (from Section 10, for reference), 11. Frontend Rules (from Section 11), 12. Render Deployment, 13. Knowledge Graph (Graphify), 14. What Not To Do, 1. Project, 2. Stack & Hosting, 3. Authority & Execution (+7 more)

### Community 15 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 16 - "Section 5 — COMPLETE (2026-08-09)"
Cohesion: 0.18
Nodes (10): Boundaries, Decisions relevant to future work, Follow-up obligations, Intentionally missing (do not build early), Last known green, Next milestone, Normal verification, Section 5 — COMPLETE (2026-08-09) (+2 more)

### Community 17 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 18 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 19 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 20 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 21 - "graphify reference: commit hook and native AGENTS.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native AGENTS.md integration, graphify reference: commit hook and native AGENTS.md integration

### Community 22 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 23 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 24 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 25 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **107 isolated node(s):** `What exists`, `Boundaries`, `Normal verification`, `Last known green`, `Decisions relevant to future work` (+102 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `resolve_turn()` connect `resolve_turn` to `test_two_markets_route.py`, `GameState`, `test_determinism.py`, `test_invariants.py`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `GameState` connect `GameState` to `test_two_markets_route.py`, `trace.py`, `resolve_turn`, `test_invariants.py`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `PlayerCommand` connect `resolve_turn` to `test_two_markets_route.py`, `GameState`, `test_invariants.py`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `GameState` (e.g. with `CausalNode` and `CausalTrace`) actually correct?**
  _`GameState` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `What exists`, `Boundaries`, `Normal verification` to the rest of the system?**
  _107 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_two_markets_route.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09852216748768473 - nodes in this community are weakly interconnected._
- **Should `GameState` be split into smaller, more focused modules?**
  _Cohesion score 0.11563367252543941 - nodes in this community are weakly interconnected._