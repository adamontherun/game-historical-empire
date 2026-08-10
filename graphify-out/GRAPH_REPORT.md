# Graph Report - game-historical-empire  (2026-08-09)

## Corpus Check
- 61 files · ~88,759 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 888 nodes · 1540 edges · 70 communities (60 shown, 10 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 53 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6db074af`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- PlayerCommand
- test_causal_trace.py
- test_determinism.py
- FiveTurnGame
- What You Must Do When Invoked
- InventoryState
- Plan — Section 1: Repository Contract and Walking Skeleton
- What You Must Do When Invoked
- Section 5 — Two Markets and One Trade Route — Plan
- test_sanity.py
- historical-empire-backend
- test_invariants.py
- Historical Empire — Agent Guide
- graphify reference: extra exports and benchmark
- Section 7 — COMPLETE (2026-08-09)
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
- Section 6 — Five-Turn Headless Prototype — Plan (Rev 2)
- Section 3 — One-Turn Grain Market Kernel — Plan
- Section 4 — Causal Explanation and Outcome Model — Plan
- BUILD_SPEC.md
- Section 2 — Core Economic Types and Deterministic Randomness — Plan
- SECTION 6 — Five-Turn Headless Prototype
- Decisions
- SECTION 11 — Mobile-First React Playable
- SECTION 7 — Deterministic Rivals
- SECTION 14 — Expand Agricultural Prototype to 10–12 Turns
- SECTION 3 — One-Turn Grain Market Kernel
- SECTION 5 — Two Markets and One Trade Route
- Part III — Global Technical Rules
- SECTION 22 — Architecture Expansion Test for Future Eras
- Frontend — Agent Guide
- Backend — Agent Guide
- 0. How to Use This Specification
- Part II — Global Game Design Rules
- SECTION 16 — Persistence and Save / Resume
- SECTION 17 — Grounded Advisor
- SECTION 12 — First Human Playtest and Refinement Gate
- Part VI — Eventual Product Direction
- SECTION 1 — Repository Contract and Walking Skeleton
- SECTION 10 — Minimal FastAPI Boundary
- SECTION 13 — City & Craft Transition Epilogue
- SECTION 15 — Content Model and Validation
- SECTION 18 — Bounded Free-Text Action Interpretation
- SECTION 19 — Authentication and Account Model
- SECTION 21 — Production Deployment and Observability
- SECTION 2 — Core Economic Types and Deterministic Randomness
- SECTION 4 — Causal Explanation and Outcome Model
- Part VIII — Agent Guardrails
- SECTION 8 — Pressure-Driven Event Arc
- turn.py
- SECTION 20 — Visual Asset System and Polish
- Section 7 — Deterministic Rivals — Plan (Rev 2)

## God Nodes (most connected - your core abstractions)
1. `PlayerCommand` - 88 edges
2. `resolve_turn()` - 85 edges
3. `FiveTurnGame` - 55 edges
4. `InventoryState` - 50 edges
5. `GameState` - 42 edges
6. `MarketState` - 32 edges
7. `PlayerState` - 30 edges
8. `RivalState` - 30 edges
9. `apply_rival_command()` - 25 edges
10. `ObservableContext` - 19 edges

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

## Communities (70 total, 10 thin omitted)

### Community 0 - "PlayerCommand"
Cohesion: 0.07
Nodes (59): PlayerCommand, Player turn command — one major action per turn (Sections 3–5)., WorldCondition, Resolve one deterministic turn. Order is explicit: command -> production ->…, resolve_turn(), Rivals must not mutate shared market availability — player supply same as…, test_player_market_isolation(), Section 4 — multi-step drought to wealth chain tests. (+51 more)

### Community 1 - "test_causal_trace.py"
Cohesion: 0.06
Nodes (42): Domain package — re-exports canonical types., CausalNode, CausalTrace, DomainEffect, OutcomeDriver, PlayerOutcome, BaseModel, Causal trace, domain effects, and player outcome for Sections 4–5. Structural… (+34 more)

### Community 2 - "test_determinism.py"
Cohesion: 0.11
Nodes (28): Engine package — deterministic RNG and rounding., derive_seed(), make_rng(), Deterministic RNG substreams via stable hash. Spec: never use global random…, Derive deterministic int seed from key material via BLAKE2b. Canonical…, Create isolated random.Random from int seed — no global state. Args: seed: Int…, Convenience: derive seed from key material and return Random. Args: run_seed:…, rng_for() (+20 more)

### Community 3 - "FiveTurnGame"
Cohesion: 0.05
Nodes (46): format_market_pulse(), format_player_state(), format_rivals(), format_route_state(), main(), parse_choice(), parse_choices_arg(), Thin CLI for the five-turn headless prototype — Section 6. Pure I/O around… (+38 more)

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native AGENTS.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 5 - "InventoryState"
Cohesion: 0.07
Nodes (74): GameState, InventoryState, MarketState, OperationState, PlayerState, BaseModel, Canonical economic types for Sections 2-5. Integer-only canonical state per…, River Route — single route between Home Valley and River Town (Section 5).… (+66 more)

### Community 6 - "Plan — Section 1: Repository Contract and Walking Skeleton"
Cohesion: 0.10
Nodes (19): 1. Create directory skeleton + `__init__.py` (no behavior), 2. Create `backend/pyproject.toml`, `backend/.python-version`, root `Makefile`, `.gitignore`, 3. Create trivial pure engine module, 4. Create trivial deterministic engine tests, 5. Update `DECISIONS.md:001` with verbatim bullets, 6. Verify baseline checks + generate lockfile, 7. Update `BUILD_SPEC.md` Status line only if all gates pass, Constraints And Non-goals (+11 more)

### Community 7 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 8 - "Section 5 — Two Markets and One Trade Route — Plan"
Cohesion: 0.11
Nodes (18): 1. Confirm workspace & branch → unblocks all edits, 2. Domain — add River Town and River Route types, keep Home alias, 3. Trace — add route/trade/river kinds, keep DAG validators compatible, 4. Engine — resolve two prices + route settlement, keep Home chain exact, 5. CLI — show both market pulses and route status, 6. Tests — prove AC 1–6 and preserve Section 3–4 invariants, 7. Docs & handoff, Constraints And Non-goals (+10 more)

### Community 13 - "test_invariants.py"
Cohesion: 0.11
Nodes (27): apply_basis_points(), clamp_non_negative(), div_round_half_up(), mul_basis_points(), Deterministic integer rounding helpers for canonical economic math. All…, Multiply value by basis points (10_000 = 100%) with floor division.…, Alias for mul_basis_points — semantic for price adjustments., Integer division rounding half away from zero for positive denominators. For… (+19 more)

### Community 14 - "Historical Empire — Agent Guide"
Cohesion: 0.12
Nodes (16): 10. API Contract (from Section 10, for reference), 11. Frontend Rules (from Section 11), 12. Render Deployment, 13. Knowledge Graph (Graphify), 14. What Not To Do, 15. STATE.md Freshness Contract, 1. Project, 2. Stack & Hosting (+8 more)

### Community 15 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 16 - "Section 7 — COMPLETE (2026-08-09)"
Cohesion: 0.18
Nodes (10): Boundaries, Decisions relevant to future work, Follow-up obligations, Intentionally missing (do not build early), Last known green, Next milestone, Normal verification, Section 7 — COMPLETE (2026-08-09) (+2 more)

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

### Community 34 - "Section 6 — Five-Turn Headless Prototype — Plan (Rev 2)"
Cohesion: 0.11
Nodes (18): 1. Confirm workspace & branch → unblocks all edits, 2. Kernel — define supply semantics (blocker, before prototype), 3. Prototype — `FiveTurnGame` state machine + revised authored 5-turn schedule, 4. CLI — thin interactive + non-interactive runner, 5. Tests — prove AC 1–7 (revised) and preserve invariants, 6. Demo/CLI polish & edge handling, 7. Docs & handoff, Constraints And Non-goals (+10 more)

### Community 35 - "Section 3 — One-Turn Grain Market Kernel — Plan"
Cohesion: 0.11
Nodes (17): 1. Domain extensions — `backend/app/domain/types.py`, 2. Trace/outcome domain — `backend/app/domain/trace.py`, 3. Engine core — `backend/app/engine/turn.py`, 4. CLI demo — `backend/app/engine/demo.py`, 5. Tests — `backend/tests/test_turn_kernel.py` + `backend/tests/test_invariants.py`, 6. Gates — `uv sync --project backend`, `make test`, `make lint`, `make type`, `make format-check`, plus manual `uv run --project backend python -m app.engine.demo`, Constraints and Non-goals, Context and Current Facts (+9 more)

### Community 36 - "Section 4 — Causal Explanation and Outcome Model — Plan"
Cohesion: 0.11
Nodes (17): 1. Confirm workspace & branch → unblocks all edits, 2. Domain — formalize `OutcomeDriver`, tuples, valuation kinds, correct roots → unblocks engine, 3. Engine — exact wealth subgraph + story drivers + exact wealth-bps ranking + RNG validation → unblocks tests/demo, 4. CLI — concise story drivers + full debug trace, 5. Tests — prove AC 1–5 plus exact totals and correct roots, 6. Gates & handoff, Constraints And Non-goals, Context And Current Facts (+9 more)

### Community 37 - "BUILD_SPEC.md"
Cohesion: 0.11
Nodes (18): 1. Product Thesis, 23. Systems Explicitly Deferred Until Proven Necessary, 29. Player Experience Success Criteria, 2. Signature Design Rule, 30. Technical Success Criteria, 35. First Active Section, 3. The Long-Term Hook, Acceptance criteria (+10 more)

### Community 38 - "Section 2 — Core Economic Types and Deterministic Randomness — Plan"
Cohesion: 0.15
Nodes (12): Constraints And Non-goals, Context And Current Facts, Goal, Grill Outcome (2026-08-09), Key Decisions, Open Questions, Recommended Approach, Risks / Rollback (+4 more)

### Community 39 - "SECTION 6 — Five-Turn Headless Prototype"
Cohesion: 0.17
Nodes (12): Acceptance criteria, CLI requirements, Exact prototype scope, Five-turn arc, Goal, SECTION 6 — Five-Turn Headless Prototype, Stop condition, Turn 1 — A Growing Settlement (+4 more)

### Community 40 - "Decisions"
Cohesion: 0.15
Nodes (12): 001 — Scope Strategy (2026-08-09), 002 — FastAPI Conventions (2026-08-09), 003 — Tooling (2026-08-09), 004 — Testing Strategy (2026-08-09), 005 — Frontend Stack (2026-08-09), 006 — Persistence (2026-08-09), 007 — Autonomy (2026-08-09), 008 — Plan Mode (2026-08-09) — revised 2026-08-09 (+4 more)

### Community 41 - "SECTION 11 — Mobile-First React Playable"
Cohesion: 0.20
Nodes (10): Acceptance criteria, Browser verification, Empire tableau, Explicitly out of scope, Goal, Primary flow, Required screen content, SECTION 11 — Mobile-First React Playable (+2 more)

### Community 42 - "SECTION 7 — Deterministic Rivals"
Cohesion: 0.22
Nodes (9): Acceptance criteria, Daran, Explicitly out of scope, Goal, In scope, Mira, Rivals, SECTION 7 — Deterministic Rivals (+1 more)

### Community 43 - "SECTION 14 — Expand Agricultural Prototype to 10–12 Turns"
Cohesion: 0.22
Nodes (9): Acceptance criteria, Content target, Contested opportunities, Goal, In scope, Preferred deep grain chain, Secondary path, SECTION 14 — Expand Agricultural Prototype to 10–12 Turns (+1 more)

### Community 44 - "SECTION 3 — One-Turn Grain Market Kernel"
Cohesion: 0.22
Nodes (9): Acceptance criteria, Drought rule, Goal, In scope, Market model, Opportunity cost, Required outputs, SECTION 3 — One-Turn Grain Market Kernel (+1 more)

### Community 45 - "SECTION 5 — Two Markets and One Trade Route"
Cohesion: 0.22
Nodes (9): Acceptance criteria, Goal, Home Valley, In scope, Optional mechanic, River Route, River Town, SECTION 5 — Two Markets and One Trade Route (+1 more)

### Community 46 - "Part III — Global Technical Rules"
Cohesion: 0.25
Nodes (8): 10. Simulation Authority, 11. Determinism, 12. Canonical Numeric State, 13. Pure Engine Boundary, 14. Causal Trace Is First-Class Output, 15. Keep Early Architecture Concrete, 16. Testing Priority, Part III — Global Technical Rules

### Community 47 - "SECTION 22 — Architecture Expansion Test for Future Eras"
Cohesion: 0.25
Nodes (8): Acceptance criteria, Architecture principle, Goal, In scope, Industrial fixture, Information or software fixture, SECTION 22 — Architecture Expansion Test for Future Eras, Stop condition

### Community 48 - "Frontend — Agent Guide"
Cohesion: 0.25
Nodes (7): API Contract, Frontend — Agent Guide, Stack, Testing, UI Principles, What to Build (Section 11), When to Build

### Community 49 - "Backend — Agent Guide"
Cohesion: 0.29
Nodes (6): Backend — Agent Guide, Conventions, Engine Rules (BUILD_SPEC.md §§11–14), Layout, Testing, When to Add DB

### Community 50 - "0. How to Use This Specification"
Cohesion: 0.29
Nodes (7): 0.1 Purpose, 0.2 Authority and precedence, 0.3 Agent execution protocol, 0.4 Section status, 0.5 Default development rule, 0. How to Use This Specification, Historical Empire — Ordered Build Specification

### Community 51 - "Part II — Global Game Design Rules"
Cohesion: 0.29
Nodes (7): 4. Player Decisions, Not Spreadsheet Operations, 5. One Meaningful Major Action per Turn, 6. Signals Before Consequences, 7. Rivals Are Strategic Signals, 8. Visible Compounding, 9. Outcome Reveal Is a Signature Interaction, Part II — Global Game Design Rules

### Community 52 - "SECTION 16 — Persistence and Save / Resume"
Cohesion: 0.29
Nodes (7): Acceptance criteria, Concurrency, Event sourcing position, Goal, In scope, SECTION 16 — Persistence and Save / Resume, Stop condition

### Community 53 - "SECTION 17 — Grounded Advisor"
Cohesion: 0.29
Nodes (7): Acceptance criteria, Architecture rule, Goal, Output, SECTION 17 — Grounded Advisor, Stop condition, Testing

### Community 54 - "SECTION 12 — First Human Playtest and Refinement Gate"
Cohesion: 0.29
Nodes (7): Agent work after playtest, Explicitly forbidden during this section, Go / no-go criteria, Goal, Playtest questions, SECTION 12 — First Human Playtest and Refinement Gate, Stop condition

### Community 55 - "Part VI — Eventual Product Direction"
Cohesion: 0.33
Nodes (6): 24. Future Agricultural MVP Shape, 25. Future Dynasty and Legacy Direction, 26. Future Market and Information Direction, 27. Future Rival Direction, 28. Future LLM Direction, Part VI — Eventual Product Direction

### Community 56 - "SECTION 1 — Repository Contract and Walking Skeleton"
Cohesion: 0.33
Nodes (6): Acceptance criteria, Explicitly out of scope, Goal, In scope, SECTION 1 — Repository Contract and Walking Skeleton, Stop condition

### Community 57 - "SECTION 10 — Minimal FastAPI Boundary"
Cohesion: 0.33
Nodes (6): Acceptance criteria, Explicitly out of scope, Goal, In scope, SECTION 10 — Minimal FastAPI Boundary, Stop condition

### Community 58 - "SECTION 13 — City & Craft Transition Epilogue"
Cohesion: 0.33
Nodes (6): Acceptance criteria, Concrete legacy, Goal, In scope, SECTION 13 — City & Craft Transition Epilogue, Stop condition

### Community 59 - "SECTION 15 — Content Model and Validation"
Cohesion: 0.33
Nodes (6): Acceptance criteria, Goal, In scope, Principle, SECTION 15 — Content Model and Validation, Stop condition

### Community 60 - "SECTION 18 — Bounded Free-Text Action Interpretation"
Cohesion: 0.33
Nodes (6): Acceptance criteria, Confirmation rule, Goal, SECTION 18 — Bounded Free-Text Action Interpretation, Stop condition, Unsupported intent

### Community 61 - "SECTION 19 — Authentication and Account Model"
Cohesion: 0.33
Nodes (6): Acceptance criteria, Child / public release gate, Goal, In scope, SECTION 19 — Authentication and Account Model, Stop condition

### Community 62 - "SECTION 21 — Production Deployment and Observability"
Cohesion: 0.33
Nodes (6): Acceptance criteria, Goal, Observability, Preferred architecture, SECTION 21 — Production Deployment and Observability, Stop condition

### Community 63 - "SECTION 2 — Core Economic Types and Deterministic Randomness"
Cohesion: 0.33
Nodes (6): Acceptance criteria, Explicitly out of scope, Goal, In scope, SECTION 2 — Core Economic Types and Deterministic Randomness, Stop condition

### Community 64 - "SECTION 4 — Causal Explanation and Outcome Model"
Cohesion: 0.33
Nodes (6): Acceptance criteria, Explicitly out of scope, Goal, In scope, SECTION 4 — Causal Explanation and Outcome Model, Stop condition

### Community 65 - "Part VIII — Agent Guardrails"
Cohesion: 0.40
Nodes (5): 31. Do Not Build Ahead, 32. Do Not Rewrite Working Systems Without Evidence, 33. Dependencies Require Justification, 34. Agent Completion Report Template, Part VIII — Agent Guardrails

### Community 66 - "SECTION 8 — Pressure-Driven Event Arc"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Goal, In scope, SECTION 8 — Pressure-Driven Event Arc, Stop condition

### Community 67 - "turn.py"
Cohesion: 0.09
Nodes (43): affordable_quantity(), compute_farm_output(), cost_for_quantity(), Shared actor-level economic primitives — Section 7 extraction. Single source of…, Settle harvest into inventory with storage cap. Returns…, Resolve ship_grain settlement with shared clamping. Uses pre-turn…, Shared expand_farm affordability/mutation. Returns (cash_after, farm_after,…, Cost in Money for quantity at price_milli (milliunits per unit). Floor division… (+35 more)

### Community 68 - "SECTION 20 — Visual Asset System and Polish"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Goal, In scope, SECTION 20 — Visual Asset System and Polish, Stop condition

### Community 70 - "Section 7 — Deterministic Rivals — Plan (Rev 2)"
Cohesion: 0.10
Nodes (20): 1 — Extract shared actor primitives (behavior-preserving, no market/trace change), 2 — Rival profile/state/result types, 3 — Integer scoring & deterministic choice, 4 — Rival execution via shared primitives + truthful headlines, 5 — Prototype integration with corrected timing, 6 — Structured threat plumbing, 7 — CLI reveal, 8 — Tests (behavioral, not scripted) (+12 more)

## Knowledge Gaps
- **402 isolated node(s):** `historical-empire-backend`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)`, `Step 1 - Ensure graphify is installed` (+397 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `resolve_turn()` connect `PlayerCommand` to `test_causal_trace.py`, `test_determinism.py`, `turn.py`, `FiveTurnGame`, `InventoryState`, `test_invariants.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `PlayerCommand` connect `PlayerCommand` to `test_causal_trace.py`, `turn.py`, `FiveTurnGame`, `InventoryState`, `test_invariants.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `FiveTurnGame` connect `FiveTurnGame` to `PlayerCommand`, `test_causal_trace.py`, `InventoryState`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `PlayerCommand` (e.g. with `FiveTurnGame` and `StrategicSummary`) actually correct?**
  _`PlayerCommand` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `FiveTurnGame` (e.g. with `TurnResolution` and `GameState`) actually correct?**
  _`FiveTurnGame` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `InventoryState` (e.g. with `FiveTurnGame` and `StrategicSummary`) actually correct?**
  _`InventoryState` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `GameState` (e.g. with `CausalNode` and `CausalTrace`) actually correct?**
  _`GameState` has 9 INFERRED edges - model-reasoned connections that need verification._