# Graph Report - game-historical-empire  (2026-08-10)

## Corpus Check
- 76 files · ~116,740 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1109 nodes · 1831 edges · 90 communities (79 shown, 11 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 30 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ddbbe1a7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SECTION 9 — Headless Strategy and Balance Harness
- test_pressure_arc.py
- harness.py
- test_five_turn_prototype.py
- What You Must Do When Invoked
- run_batch
- Plan — Section 1: Repository Contract and Walking Skeleton
- What You Must Do When Invoked
- Section 5 — Two Markets and One Trade Route — Plan
- test_sanity.py
- historical-empire-backend
- Section 8 plan — consolidated review (round 2, against Rev 3)
- Historical Empire — Agent Guide
- graphify reference: extra exports and benchmark
- Section 9 — COMPLETE (2026-08-10)
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
- Section 9 plan — consolidated review (round 1)
- Section 8 plan — consolidated review (round 1)
- engine/__init__.py
- InventoryState
- Section 8 — Pressure-Driven Event Arc — Plan (Rev 4 — incorporates R1–R8 + grill Q1–Q7 + review round 2 F1–F5)
- Section 7 — Deterministic Rivals — Plan (Rev 2)
- test_deterministic_rivals.py
- SECTION 8 — Pressure-Driven Event Arc
- PlayerCommand
- turn.py
- Section 9 — Headless Strategy and Balance Harness — Plan (Rev 2 — regional_output fix, per review round 1)
- trace.py
- Section 9 — implementation review, round 2 (consolidated)
- score_rival_command
- prototype.py
- FiveTurnGame
- RivalPreferences
- Section 8 implementation — consolidated review (round 3, against commit 28a0963)
- SECTION 20 — Visual Asset System and Polish
- cli.py
- WorldCondition
- Section 9 — review round 3 (consolidated) — SUPERSEDES round 2 on the route
- Section 9 — review round 4 (consolidated, final) — SUPERSEDES rounds 2 and 3
- Orchestration Guide — how BUILD_SPEC sections get built
- Part VIII — Agent Guardrails

## God Nodes (most connected - your core abstractions)
1. `PlayerCommand` - 85 edges
2. `resolve_turn()` - 85 edges
3. `FiveTurnGame` - 60 edges
4. `InventoryState` - 45 edges
5. `GameState` - 34 edges
6. `MarketState` - 27 edges
7. `PlayerState` - 25 edges
8. `RivalState` - 24 edges
9. `apply_rival_command()` - 24 edges
10. `run_batch()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `BatchConfig` --uses--> `FiveTurnGame`  [INFERRED]
  backend/app/engine/harness.py → backend/app/engine/prototype.py
- `SeedResult` --uses--> `FiveTurnGame`  [INFERRED]
  backend/app/engine/harness.py → backend/app/engine/prototype.py
- `PolicyAggregate` --uses--> `FiveTurnGame`  [INFERRED]
  backend/app/engine/harness.py → backend/app/engine/prototype.py
- `BatchResult` --uses--> `FiveTurnGame`  [INFERRED]
  backend/app/engine/harness.py → backend/app/engine/prototype.py
- `format_rivals()` --references--> `FiveTurnGame`  [EXTRACTED]
  backend/app/cli.py → backend/app/engine/prototype.py

## Import Cycles
- None detected.

## Communities (90 total, 11 thin omitted)

### Community 0 - "SECTION 9 — Headless Strategy and Balance Harness"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Goal, In scope, SECTION 9 — Headless Strategy and Balance Harness, Stop condition

### Community 1 - "test_pressure_arc.py"
Cohesion: 0.08
Nodes (28): PressureState, BaseModel, model_validator, Pressure domain — Section 8 world-pressure arc types. Small, frozen, validated…, One step of the authored pressure arc — frozen, validated. Exactly 7 fields per…, next_world_known_for_turn(), pressure_for_turn(), WorldCondition (+20 more)

### Community 2 - "harness.py"
Cohesion: 0.16
Nodes (22): BatchResult, _can_afford(), format_markdown(), policy_cash_preserving(), policy_production_heavy(), policy_random_legal(), policy_storage_heavy(), policy_trade_heavy() (+14 more)

### Community 3 - "test_five_turn_prototype.py"
Cohesion: 0.13
Nodes (22): _choices(), _hold(), Section 6 — Five-Turn Headless Prototype acceptance tests. AC1: exactly 5…, AC5 non-dominance: no one policy wins every meaningful outcome. Hold may win…, Helper to build choice list from type strings like 'buy_grain:20'., Demand must be explicit in causal graph as parent of supply and price., Every authored signal must not assert a mechanic not in the model., Regression: summary must show true initial Home/River prices, not Turn-1-after… (+14 more)

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native AGENTS.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 5 - "run_batch"
Cohesion: 0.17
Nodes (22): BatchConfig, Run batch — deterministic, pure, no global random., run_batch(), default_start_state(), Tuned start state — Section 9 retuned for binding constraints (storage…, Section 9 — Balance harness acceptance tests. Covers AC1-6 with confound-…, New invariant: drought raises price even with farm_capacity=0 via regional., Regression: starting storage must be scarce enough that granary matters. Idle… (+14 more)

### Community 6 - "Plan — Section 1: Repository Contract and Walking Skeleton"
Cohesion: 0.10
Nodes (19): 1. Create directory skeleton + `__init__.py` (no behavior), 2. Create `backend/pyproject.toml`, `backend/.python-version`, root `Makefile`, `.gitignore`, 3. Create trivial pure engine module, 4. Create trivial deterministic engine tests, 5. Update `DECISIONS.md:001` with verbatim bullets, 6. Verify baseline checks + generate lockfile, 7. Update `BUILD_SPEC.md` Status line only if all gates pass, Constraints And Non-goals (+11 more)

### Community 7 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 8 - "Section 5 — Two Markets and One Trade Route — Plan"
Cohesion: 0.11
Nodes (18): 1. Confirm workspace & branch → unblocks all edits, 2. Domain — add River Town and River Route types, keep Home alias, 3. Trace — add route/trade/river kinds, keep DAG validators compatible, 4. Engine — resolve two prices + route settlement, keep Home chain exact, 5. CLI — show both market pulses and route status, 6. Tests — prove AC 1–6 and preserve Section 3–4 invariants, 7. Docs & handoff, Constraints And Non-goals (+10 more)

### Community 13 - "Section 8 plan — consolidated review (round 2, against Rev 3)"
Cohesion: 0.25
Nodes (7): Already resolved — no action (convergence check), F1 — The AC1/AC3 instrument still confounds "heeded the warning" with "chose a different production lever" (BLOCKING, highest priority), F2 — `PressureState` still permits the invalid combination R1 was meant to eliminate (BLOCKING), F3 — `causal_source_id` and the trace `reason_code` are two code paths computing one fact (should-fix), F4 — File location for `PressureStage`/`PressureState` is still hedged (should-fix, cheap), F5 — Validation Plan should state the final repo gates explicitly (should-fix, housekeeping), Section 8 plan — consolidated review (round 2, against Rev 3)

### Community 14 - "Historical Empire — Agent Guide"
Cohesion: 0.12
Nodes (16): 10. API Contract (from Section 10, for reference), 11. Frontend Rules (from Section 11), 12. Render Deployment, 13. Knowledge Graph (Graphify), 14. What Not To Do, 15. STATE.md Freshness Contract, 1. Project, 2. Stack & Hosting (+8 more)

### Community 15 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 16 - "Section 9 — COMPLETE (2026-08-10)"
Cohesion: 0.20
Nodes (9): Boundaries, Decisions relevant, Intentionally missing, Last known green, Next milestone, Normal verification, Section 9 — COMPLETE (2026-08-10), STATE — Historical Empire (+1 more)

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
Cohesion: 0.14
Nodes (13): 1. Product Thesis, 23. Systems Explicitly Deferred Until Proven Necessary, 29. Player Experience Success Criteria, 2. Signature Design Rule, 30. Technical Success Criteria, 35. First Active Section, 3. The Long-Term Hook, Final Architectural Principle (+5 more)

### Community 38 - "Section 2 — Core Economic Types and Deterministic Randomness — Plan"
Cohesion: 0.15
Nodes (12): Constraints And Non-goals, Context And Current Facts, Goal, Grill Outcome (2026-08-09), Key Decisions, Open Questions, Recommended Approach, Risks / Rollback (+4 more)

### Community 39 - "SECTION 6 — Five-Turn Headless Prototype"
Cohesion: 0.17
Nodes (12): Acceptance criteria, CLI requirements, Exact prototype scope, Five-turn arc, Goal, SECTION 6 — Five-Turn Headless Prototype, Stop condition, Turn 1 — A Growing Settlement (+4 more)

### Community 40 - "Decisions"
Cohesion: 0.11
Nodes (17): 001 — Scope Strategy (2026-08-09), 002 — FastAPI Conventions (2026-08-09), 003 — Tooling (2026-08-09), 004 — Testing Strategy (2026-08-09), 005 — Frontend Stack (2026-08-09), 006 — Persistence (2026-08-09), 007 — Autonomy (2026-08-09), 008 — Plan Mode (2026-08-09) — revised 2026-08-09 (+9 more)

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

### Community 65 - "Section 9 plan — consolidated review (round 1)"
Cohesion: 0.20
Nodes (9): E1 — The engine is completely seed-invariant (confirms Q6, more strongly than stated), E2 — Decision 4's ±2 supply perturbation does not fix the degeneracy (BLOCKING), E3 — A wider start-state band does not fix it either (rules out the obvious alternative), E4 — The real finding: the game currently has a universally dominant strategy, and it is "do nothing" (BLOCKING — changes Section 9's scope), E5 — Decision 4 should be replaced, not tuned, E6 — Decision 6's `win_rate >= 0.05` floor is unsound as written, Keep as-is, Section 9 plan — consolidated review (round 1) (+1 more)

### Community 66 - "Section 8 plan — consolidated review (round 1)"
Cohesion: 0.18
Nodes (10): Keep as-is (both reviewers agree), R1 — Pressure must be the single source of truth for the turn (BLOCKING), R2 — Delete `world_modifiers` (BLOCKING), R3 — Trace root: no numeric hash, and no validator change (BLOCKING), R4 — T2/T3 prose must be mechanically truthful (BLOCKING), R5 — AC3 must test preparation, not balance (BLOCKING), R6 — AC1 needs the same instrument, R7 — Fix the validation commands (+2 more)

### Community 67 - "engine/__init__.py"
Cohesion: 0.06
Nodes (55): Engine package — deterministic RNG and rounding., derive_seed(), make_rng(), Deterministic RNG substreams via stable hash. Spec: never use global random…, Derive deterministic int seed from key material via BLAKE2b. Canonical…, Create isolated random.Random from int seed — no global state. Args: seed: Int…, Convenience: derive seed from key material and return Random. Args: run_seed:…, rng_for() (+47 more)

### Community 68 - "InventoryState"
Cohesion: 0.15
Nodes (31): Domain package — re-exports canonical types., GameState, InventoryState, MarketState, OperationState, PlayerState, BaseModel, Canonical economic types for Sections 2-5. Integer-only canonical state per… (+23 more)

### Community 69 - "Section 8 — Pressure-Driven Event Arc — Plan (Rev 4 — incorporates R1–R8 + grill Q1–Q7 + review round 2 F1–F5)"
Cohesion: 0.09
Nodes (22): 1 — Domain pressure types (no behavior change yet), 2 — Pressure arc + pure helpers, 3 — Prototype refactor to drive from pressure (keep TURN_SPECS compat), 4 — Turn kernel signature + trace integration (pressure → world chain), 5 — Rivals & settlement keep structured threat (no scoring rewrite), 6 — CLI + summary polish, 7 — New Section 8 acceptance tests (exact specification per R5/R6 + Q1/Q2/Q5 + F1), Closeout Checklist (F5 — literal last step) (+14 more)

### Community 70 - "Section 7 — Deterministic Rivals — Plan (Rev 2)"
Cohesion: 0.10
Nodes (20): 1 — Extract shared actor primitives (behavior-preserving, no market/trace change), 2 — Rival profile/state/result types, 3 — Integer scoring & deterministic choice, 4 — Rival execution via shared primitives + truthful headlines, 5 — Prototype integration with corrected timing, 6 — Structured threat plumbing, 7 — CLI reveal, 8 — Tests (behavioral, not scripted) (+12 more)

### Community 71 - "test_deterministic_rivals.py"
Cohesion: 0.14
Nodes (26): Inventory value in Money at price_milli., value_for(), apply_rival_command(), BaseModel, Economic settlement context post player market resolution., Execute one rival's full turn via shared primitives with correct timing. Buy…, Economic state — cash/inventory/capacities/route, no headline., Wealth = cash + inventory value at home_price. (+18 more)

### Community 72 - "SECTION 8 — Pressure-Driven Event Arc"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Goal, In scope, SECTION 8 — Pressure-Driven Event Arc, Stop condition

### Community 73 - "PlayerCommand"
Cohesion: 0.06
Nodes (82): PlayerCommand, River Route — single route between Home Valley and River Town (Section 5).…, Player turn command — one major action per turn (Sections 3–5, sell_grain added…, RouteState, pressure_for_world(), Return canonical test pressure for a WorldCondition (G1 helper)., Resolve one deterministic turn. Order is explicit: pressure_stage -> world ->…, Non-player regional output after world effect — reuses same drought primitive. (+74 more)

### Community 74 - "turn.py"
Cohesion: 0.13
Nodes (25): affordable_quantity(), compute_farm_output(), cost_for_quantity(), Shared actor-level economic primitives — Section 7 extraction. Single source of…, Resolve a sell_grain command — inverse of buy, at Home price. Args: cash: cash…, Settle harvest into inventory with storage cap. Returns…, Resolve ship_grain settlement with shared clamping. Uses pre-turn…, Cost in Money for quantity at price_milli (milliunits per unit). Floor division… (+17 more)

### Community 75 - "Section 9 — Headless Strategy and Balance Harness — Plan (Rev 2 — regional_output fix, per review round 1)"
Cohesion: 0.12
Nodes (15): Constraints And Non-goals, Context And Current Facts (verified against code), Fit to Stack & Hosting, Goal, Grill — Headless Stress Test (Rev 2, answered from code/evidence, folded into plan), Implementation Authority, Key Decisions (all settled — no open choices), Open Questions (+7 more)

### Community 76 - "trace.py"
Cohesion: 0.10
Nodes (20): CausalNode, CausalTrace, DomainEffect, OutcomeDriver, PlayerOutcome, BaseModel, model_validator, Causal trace, domain effects, and player outcome for Sections 4–5. Structural… (+12 more)

### Community 77 - "Section 9 — implementation review, round 2 (consolidated)"
Cohesion: 0.18
Nodes (10): D1 — `storage_heavy`'s core investment buys capacity nobody needs (BLOCKING), D2 — The river route cannot repay its own establishment cost (BLOCKING), D3 — Two policies are still strawmen, so the balance table is not yet evidence, D4 — Production ending below hold is acceptable; do not tune it away, D5 — Upkeep / farm maintenance was measured and rejected, Keep as-is, Section 9 — implementation review, round 2 (consolidated), What to change (+2 more)

### Community 78 - "score_rival_command"
Cohesion: 0.13
Nodes (25): choose_rival_command(), _expected_return(), _exposure_bps(), ObservableContext, Information visible to rivals when choosing (pre-turn)., Rough integer expected return in Money for scoring (not canonical wealth).…, Risk factor: penalize if post-command cash would be low., Exposure factor: Mira penalizes farm concentration, Daran rewards it. (+17 more)

### Community 79 - "prototype.py"
Cohesion: 0.11
Nodes (14): _next_world_known_for_turn(), BaseModel, PlayerCommand, Five-turn headless prototype — Section 8 pressure-driven arc. Orchestrates…, Wealth = cash + inventory value at Home price (milli)., Concise end-of-run summary — both human and structured (now with rivals)., Build pre-turn observable context for rival choice (structured, not prose)., One turn's authored world and signal — plain strings, not a DSL. (+6 more)

### Community 80 - "FiveTurnGame"
Cohesion: 0.09
Nodes (14): FiveTurnGame, GameState, In-memory 5-turn game — owns GameState, history, and session rivals. Rivals are…, Derived headlines per turn for UI convenience., Current pressure stage, None when game is complete (Q3)., test_harness_uses_pressure_not_bare_string(), Canonical hold-5 run must have ≥1 turn where Mira/Daran choose different types…, test_canonical_run_has_three_diffs() (+6 more)

### Community 81 - "RivalPreferences"
Cohesion: 0.40
Nodes (4): _headline_for(), Immutable preference vector — bps per command, frozen so profile cannot mutate., Derive truthful headline from reason_code and actual quantities. Partial…, RivalPreferences

### Community 82 - "Section 8 implementation — consolidated review (round 3, against commit 28a0963)"
Cohesion: 0.22
Nodes (8): Closeout (unchanged from F5), G1 — Remove the `PressureState | str` legacy shim (BLOCKING), G2 — Work Plan §6 (CLI + StrategicSummary stage display) was never implemented (BLOCKING), G3 — STATE.md contains a provably false provenance claim (BLOCKING), G4 — DECISIONS.md 012 contradicts its own rationale (BLOCKING), G5 — Pressure node label should derive from stage, not title (should-fix), G6 — Prefer a `mode="before"` validator over `object.__setattr__` (should-fix, minor), Section 8 implementation — consolidated review (round 3, against commit 28a0963)

### Community 83 - "SECTION 20 — Visual Asset System and Polish"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Goal, In scope, SECTION 20 — Visual Asset System and Polish, Stop condition

### Community 84 - "cli.py"
Cohesion: 0.27
Nodes (11): format_market_pulse(), format_player_state(), format_rivals(), format_route_state(), main(), parse_choice(), parse_choices_arg(), Thin CLI for the five-turn headless prototype — Section 6. Pure I/O around… (+3 more)

### Community 87 - "Section 9 — review round 3 (consolidated) — SUPERSEDES round 2 on the route"
Cohesion: 0.20
Nodes (9): Keep as-is, R1 — Retraction: round 2's route fix was buying a passing grade, R2 — Transport cost, not capacity, is what makes the route a trap, R3 — River Town is not a market at its shipped scale, R4 — Gate math is floating-point, which breaks eight sections of integer discipline, R5 — Tie handling in `run_batch` is biased and convoluted, Section 9 — review round 3 (consolidated) — SUPERSEDES round 2 on the route, What to change (+1 more)

### Community 88 - "Section 9 — review round 4 (consolidated, final) — SUPERSEDES rounds 2 and 3"
Cohesion: 0.13
Nodes (14): Do not, Final target config, R1 — The granary does not repay its cost, and `test_build_granary_not_worthless` cannot see it, R2 — But the granary is not broken. `policy_storage_heavy` is a third strawman, R3 — Revert `route.capacity` to 20. Transport cost was the entire route fix, R4 — Retract round 3's River Town rescale entirely, R5 — State the price-taking boundary explicitly instead of pretending to fix it, R6 — `hold rank ≥3` must be computed over the four intentional policies, not five (+6 more)

### Community 89 - "Orchestration Guide — how BUILD_SPEC sections get built"
Cohesion: 0.20
Nodes (9): 1. The loop, per section, 2. Driving Muse headlessly, 3. Driving ChatGPT, 4. Verification discipline (non-negotiable), 5. Standing decisions (set by the product owner), 6. Recurring failure patterns to watch for, 7. Where things live, 8. Known upcoming blockers (+1 more)

### Community 93 - "Part VIII — Agent Guardrails"
Cohesion: 0.40
Nodes (5): 31. Do Not Build Ahead, 32. Do Not Rewrite Working Systems Without Evidence, 33. Dependencies Require Justification, 34. Agent Completion Report Template, Part VIII — Agent Guardrails

## Knowledge Gaps
- **506 isolated node(s):** `001 — Scope Strategy (2026-08-09)`, `002 — FastAPI Conventions (2026-08-09)`, `003 — Tooling (2026-08-09)`, `004 — Testing Strategy (2026-08-09)`, `005 — Frontend Stack (2026-08-09)` (+501 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `resolve_turn()` connect `PlayerCommand` to `test_pressure_arc.py`, `engine/__init__.py`, `InventoryState`, `test_five_turn_prototype.py`, `test_deterministic_rivals.py`, `turn.py`, `trace.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `FiveTurnGame` connect `FiveTurnGame` to `test_pressure_arc.py`, `harness.py`, `test_five_turn_prototype.py`, `run_batch`, `test_deterministic_rivals.py`, `PlayerCommand`, `prototype.py`, `cli.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `PlayerCommand` connect `PlayerCommand` to `test_pressure_arc.py`, `test_five_turn_prototype.py`, `InventoryState`, `engine/__init__.py`, `test_deterministic_rivals.py`, `turn.py`, `score_rival_command`, `FiveTurnGame`, `RivalPreferences`, `cli.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `PlayerCommand` (e.g. with `ObservableContext` and `RivalPreferences`) actually correct?**
  _`PlayerCommand` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `FiveTurnGame` (e.g. with `BatchConfig` and `BatchResult`) actually correct?**
  _`FiveTurnGame` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `InventoryState` (e.g. with `ObservableContext` and `RivalPreferences`) actually correct?**
  _`InventoryState` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `GameState` (e.g. with `CausalNode` and `CausalTrace`) actually correct?**
  _`GameState` has 6 INFERRED edges - model-reasoned connections that need verification._