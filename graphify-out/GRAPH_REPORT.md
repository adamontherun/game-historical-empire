# Graph Report - game-historical-empire  (2026-08-10)

## Corpus Check
- 137 files · ~203,344 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1721 nodes · 2885 edges · 137 communities (113 shown, 24 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 131 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f2f21c22`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SECTION 9 — Headless Strategy and Balance Harness
- test_pressure_arc.py
- PlayerCommand
- test_five_turn_prototype.py
- What You Must Do When Invoked
- mappers.py
- Plan — Section 1: Repository Contract and Walking Skeleton
- What You Must Do When Invoked
- Section 5 — Two Markets and One Trade Route — Plan
- test_sanity.py
- historical-empire-backend
- Section 8 plan — consolidated review (round 2, against Rev 3)
- Historical Empire — Agent Guide
- graphify reference: extra exports and benchmark
- Section 13 — IN PROGRESS — City & Craft Transition Epilogue (2026-08-10)
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
- test_determinism.py
- Audit — Sections 1-10 Full-Codebase (Muse, 2026-08-10)
- Section 8 — Pressure-Driven Event Arc — Plan (Rev 4 — incorporates R1–R8 + grill Q1–Q7 + review round 2 F1–F5)
- Section 7 — Deterministic Rivals — Plan (Rev 2)
- test_balance_harness.py
- test_causal_trace.py
- Section 11 — Design Direction (Claude, design authority)
- Section 10 plan — consolidated review (round 1)
- Section 9 — Headless Strategy and Balance Harness — Plan (Rev 2 — regional_output fix, per review round 1)
- FiveTurnGame
- Section 9 — implementation review, round 2 (consolidated)
- Section 10 — Minimal FastAPI Boundary — Plan
- InventoryState
- SHOULD-FIX
- typescript
- Section 8 implementation — consolidated review (round 3, against commit 28a0963)
- turn.py
- Section 10 plan — consolidated review (round 2)
- test_two_markets_route.py
- test_api.py
- Section 9 — review round 3 (consolidated) — SUPERSEDES round 2 on the route
- Section 9 — review round 4 (consolidated, final) — SUPERSEDES rounds 2 and 3
- Orchestration Guide — how BUILD_SPEC sections get built
- 2. SHOULD-FIX
- App.tsx
- Section 13 — Plan Review, Round 1
- harness.py
- rivals.py
- api/__init__.py
- MarketState
- Section 11 — Mobile-First React Playable — Plan
- 3. Design rulings — the vague spots, now decided
- Section 10 implementation — review round 3
- prettier
- compilerOptions
- Audit — Sections 1–10, Consolidated Review Round 2
- GameState
- Section 12 — Playtest Gate Instrumentation — Plan
- devDependencies
- scripts
- compilerOptions
- package.json
- dependencies
- Section 12 — First Human Playtest: Facilitator Script
- eslint-plugin-react-hooks
- test_explanation.py
- @playwright/test
- cli.py
- Section 13 — Design Direction (Claude, design authority)
- @testing-library/user-event
- @types/node
- @types/react-dom
- Section 13 — City & Craft Transition Epilogue — Plan
- @vitejs/plugin-react
- commit.test.tsx
- test_invariants.py
- test_rounding.py
- @testing-library/jest-dom
- default_start_state
- SECTION 20 — Visual Asset System and Polish
- Part VIII — Agent Guardrails
- test_no_float_in_rival_scoring
- test_rival_state_has_no_headline
- jsdom

## God Nodes (most connected - your core abstractions)
1. `PlayerCommand` - 118 edges
2. `resolve_turn()` - 94 edges
3. `FiveTurnGame` - 84 edges
4. `GameState` - 58 edges
5. `InventoryState` - 53 edges
6. `MarketState` - 35 edges
7. `PlayerState` - 33 edges
8. `RivalState` - 31 edges
9. `EightTurnGame` - 27 edges
10. `Decisions` - 27 edges

## Surprising Connections (you probably didn't know these)
- `GameSession` --uses--> `PlayerCommand`  [INFERRED]
  backend/app/api/sessions.py → backend/app/domain/types.py
- `GameSession` --uses--> `FiveTurnGame`  [INFERRED]
  backend/app/api/sessions.py → backend/app/engine/prototype.py
- `format_rivals()` --references--> `FiveTurnGame`  [EXTRACTED]
  backend/app/cli.py → backend/app/engine/prototype.py
- `EightTurnGame` --uses--> `PressureState`  [INFERRED]
  backend/app/engine/prototype.py → backend/app/domain/pressure.py
- `FiveTurnGame` --uses--> `PressureState`  [INFERRED]
  backend/app/engine/prototype.py → backend/app/domain/pressure.py

## Import Cycles
- None detected.

## Communities (137 total, 24 thin omitted)

### Community 0 - "SECTION 9 — Headless Strategy and Balance Harness"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Goal, In scope, SECTION 9 — Headless Strategy and Balance Harness, Stop condition

### Community 1 - "test_pressure_arc.py"
Cohesion: 0.08
Nodes (29): PressureState, BaseModel, model_validator, One step of the authored pressure arc — frozen, validated. Exactly 7 fields per…, next_world_known_for_turn(), pressure_for_turn(), Pressure arc — Section 8 authored 5-turn arc. Hard-coded, deterministic, no…, Derive world for turn idx from pressure arc. (+21 more)

### Community 2 - "PlayerCommand"
Cohesion: 0.16
Nodes (28): PlayerCommand, Player turn command — one major action per turn (Sections 3–5, sell_grain…, Resolve one deterministic turn. Order is explicit: pressure_stage -> world ->…, Non-player regional output after world effect — reuses same drought primitive., _regional_output_after_world(), resolve_turn(), B2: largest offered quantity must be one the engine resolves unclamped., test_choices_engine_agreement_unclamped() (+20 more)

### Community 3 - "test_five_turn_prototype.py"
Cohesion: 0.13
Nodes (22): _choices(), _hold(), Section 6 — Five-Turn Headless Prototype acceptance tests. AC1: exactly 5…, AC5 non-dominance: no one policy wins every meaningful outcome. Hold may win…, Helper to build choice list from type strings like 'buy_grain:20'., Demand must be explicit in causal graph as parent of supply and price., Every authored signal must not assert a mechanic not in the model., Regression: summary must show true initial Home/River prices, not Turn-1-after… (+14 more)

### Community 4 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native AGENTS.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 5 - "mappers.py"
Cohesion: 0.06
Nodes (66): choice_map_for(), choices_for(), _completion_summary(), _market_view(), _outcome_view(), GameView, Mappers: FiveTurnGame -> GameView. Pure, no mutation., Map choice_id -> PlayerCommand for current revision. (+58 more)

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

### Community 16 - "Section 13 — IN PROGRESS — City & Craft Transition Epilogue (2026-08-10)"
Cohesion: 0.20
Nodes (9): Boundaries, Decisions relevant, Intentionally missing, Last known green, Next milestone, Normal verification, Section 13 — IN PROGRESS — City & Craft Transition Epilogue (2026-08-10), STATE — Historical Empire (+1 more)

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
Cohesion: 0.07
Nodes (27): 001 — Scope Strategy (2026-08-09), 002 — FastAPI Conventions (2026-08-09), 003 — Tooling (2026-08-09), 004 — Testing Strategy (2026-08-09), 005 — Frontend Stack (2026-08-09), 006 — Persistence (2026-08-09), 007 — Autonomy (2026-08-09), 008 — Plan Mode (2026-08-09) — revised 2026-08-09 (+19 more)

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

### Community 67 - "test_determinism.py"
Cohesion: 0.12
Nodes (23): derive_seed(), Derive deterministic int seed from key material via BLAKE2b. Canonical…, Tests for deterministic RNG — AC #3, #4, #5., Ensure deterministic hash uses hashlib, not built-in hash()., RNG serialization must not collide on delimiter-containing strings. Old naive…, AC #5: engine must not use global random functions (all files)., test_delimiter_collision_regression(), test_derive_seed_golden_values() (+15 more)

### Community 68 - "Audit — Sections 1-10 Full-Codebase (Muse, 2026-08-10)"
Cohesion: 0.06
Nodes (30): 1.1 SHOULD-FIX — `turn.py` sell path emits `inventory_after_buy` alias with sell delta (modelling lie, trace consumer will misread), 1.2 SHOULD-FIX — `mappers.py` ship quantity underestimates post-harvest capacity (offered choice smaller than engine allows), 1.3 NIT — `domain/trace.py:58-72` dead first branch (unreachable validator), 1.4 UNPROVEN (not filed as BLOCKING) — `actor.resolve_buy` reason priority when both cash and storage bind, 1 — REAL BUGS (proven with input → wrong output, or unreachable invariant), 2.1 `test_api.py:268-279` `test_gameview_internal_consistency` — tautological, 2.2 `test_balance_harness.py:186-207` `test_build_granary_not_worthless` — necessary but not sufficient, 2.3 `test_invariants.py:44-69` `test_bounded_price_monotonic_with_supply` — dead loop, then trivial monotonic check (+22 more)

### Community 69 - "Section 8 — Pressure-Driven Event Arc — Plan (Rev 4 — incorporates R1–R8 + grill Q1–Q7 + review round 2 F1–F5)"
Cohesion: 0.09
Nodes (22): 1 — Domain pressure types (no behavior change yet), 2 — Pressure arc + pure helpers, 3 — Prototype refactor to drive from pressure (keep TURN_SPECS compat), 4 — Turn kernel signature + trace integration (pressure → world chain), 5 — Rivals & settlement keep structured threat (no scoring rewrite), 6 — CLI + summary polish, 7 — New Section 8 acceptance tests (exact specification per R5/R6 + Q1/Q2/Q5 + F1), Closeout Checklist (F5 — literal last step) (+14 more)

### Community 70 - "Section 7 — Deterministic Rivals — Plan (Rev 2)"
Cohesion: 0.10
Nodes (20): 1 — Extract shared actor primitives (behavior-preserving, no market/trace change), 2 — Rival profile/state/result types, 3 — Integer scoring & deterministic choice, 4 — Rival execution via shared primitives + truthful headlines, 5 — Prototype integration with corrected timing, 6 — Structured threat plumbing, 7 — CLI reveal, 8 — Tests (behavioral, not scripted) (+12 more)

### Community 71 - "test_balance_harness.py"
Cohesion: 0.22
Nodes (16): BatchConfig, model_validator, Run batch — deterministic, pure, no global random., run_batch(), Section 9 — Balance harness acceptance tests. Covers AC1-6 with confound-…, Matched control: policy_storage_heavy must beat itself with build_granary…, Matched control: policy_trade_heavy must beat itself with secure_route…, AC2: no universally dominant (median_ratio <1.60) and no dead (median… (+8 more)

### Community 72 - "test_causal_trace.py"
Cohesion: 0.11
Nodes (26): CausalNode, One step in the causal chain with explicit parent links., Lightweight turn identity for RNG derivation., Derive TurnContext for RNG calls., TurnContext, pressure_for_world(), Return canonical test pressure for a WorldCondition (G1 helper)., _base_state() (+18 more)

### Community 73 - "Section 11 — Design Direction (Claude, design authority)"
Cohesion: 0.10
Nodes (19): 0.1 Prices are milliunits; cash is whole coins, 0.2 `rival_headlines` is `null` on turn 0, 0.3 `turn` is a 0-based index of the *upcoming* decision, 0.4 Choice count is 6–8, not 2–4, 0.5 `latest_outcome` context ≠ top-level context, 0. Non-negotiable facts about the payload (measured, not assumed), 1.1 Palette, 1.2 Pressure drives the atmosphere (+11 more)

### Community 74 - "Section 10 plan — consolidated review (round 1)"
Cohesion: 0.18
Nodes (10): B1 — BLOCKING: the plan makes the balance harness's scripted policies into the player's only legal moves, B2 — The causal trace must not be behind a debug flag or a query param, B3 — The AC4 test has one vacuous step and one circular step, B4 — `empire_summary.operations` is invented structure, B5 — Internal contradiction: `run_seed` is required for reproduction but absent from `GameView`, B6 — `next_margin` should be one engine helper, not a third copy of the same expression, B7 — Smaller items, Keep as-is (+2 more)

### Community 75 - "Section 9 — Headless Strategy and Balance Harness — Plan (Rev 2 — regional_output fix, per review round 1)"
Cohesion: 0.12
Nodes (15): Constraints And Non-goals, Context And Current Facts (verified against code), Fit to Stack & Hosting, Goal, Grill — Headless Stress Test (Rev 2, answered from code/evidence, folded into plan), Implementation Authority, Key Decisions (all settled — no open choices), Open Questions (+7 more)

### Community 76 - "FiveTurnGame"
Cohesion: 0.10
Nodes (9): FiveTurnGame, In-memory 5-turn game — owns GameState, history, and session rivals. Rivals are…, Derived headlines per turn for UI convenience., test_harness_uses_pressure_not_bare_string(), Canonical hold-5 run must have ≥1 turn where Mira/Daran choose different types…, test_canonical_run_has_three_diffs(), test_headlines_derived_and_visible_after_first_turn(), test_rival_determinism_same_seed() (+1 more)

### Community 77 - "Section 9 — implementation review, round 2 (consolidated)"
Cohesion: 0.18
Nodes (10): D1 — `storage_heavy`'s core investment buys capacity nobody needs (BLOCKING), D2 — The river route cannot repay its own establishment cost (BLOCKING), D3 — Two policies are still strawmen, so the balance table is not yet evidence, D4 — Production ending below hold is acceptable; do not tune it away, D5 — Upkeep / farm maintenance was measured and rejected, Keep as-is, Section 9 — implementation review, round 2 (consolidated), What to change (+2 more)

### Community 78 - "Section 10 — Minimal FastAPI Boundary — Plan"
Cohesion: 0.06
Nodes (33): Constraints And Non-goals, Context And Current Facts, Goal, K1 — Where `GameView` lives (pure engine boundary, global §13), K2 — `choice_id`: what it IS and how it prevents mutation (AC2) — **REVISED per B1/B6**, K3 — Revision semantics (where, increment, failure, atomicity) — **REVISED per B7/C5**, K4 — AC4 "no frontend formula needed" — **REVISED per B2/B3/B4/B5/C1/C3/C4**, K5 — AC5 "engine imports no FastAPI" enforced by TEST (+25 more)

### Community 79 - "InventoryState"
Cohesion: 0.15
Nodes (33): InventoryState, Player inventory — grain for Sections 2-4, finished_goods added Section 13., apply_rival_command(), choose_rival_command(), ObservableContext, BaseModel, Information visible to rivals when choosing (pre-turn)., Economic settlement context post player market resolution. (+25 more)

### Community 80 - "SHOULD-FIX"
Cohesion: 0.08
Nodes (23): Audit — Sections 1–10, Consolidated Review Round 1, B1 — `make type` has never run pyright in strict mode. The type gate is not the gate we think it is., B2 — The API hides legal moves from the player. `choices_for` models the coming harvest for `buy` and ignores it for `ship`, under-offering in both directions., B3 — Two acceptance tests are non-falsifiable. Both survive deletion of the feature they name., B4 — Rival headlines report total failure on partial fills. The rival sold, and the game says it didn't., BLOCKING, Explicitly checked and found clean, How to read this (+15 more)

### Community 82 - "Section 8 implementation — consolidated review (round 3, against commit 28a0963)"
Cohesion: 0.22
Nodes (8): Closeout (unchanged from F5), G1 — Remove the `PressureState | str` legacy shim (BLOCKING), G2 — Work Plan §6 (CLI + StrategicSummary stage display) was never implemented (BLOCKING), G3 — STATE.md contains a provably false provenance claim (BLOCKING), G4 — DECISIONS.md 012 contradicts its own rationale (BLOCKING), G5 — Pressure node label should derive from stage, not title (should-fix), G6 — Prefer a `mode="before"` validator over `object.__setattr__` (should-fix, minor), Section 8 implementation — consolidated review (round 3, against commit 28a0963)

### Community 83 - "turn.py"
Cohesion: 0.09
Nodes (29): Shared actor-level economic primitives — Section 7 extraction. Single source of…, Resolve a sell_grain command — inverse of buy, at Home price. Args: cash: cash…, Settle harvest into inventory with storage cap. Returns…, Resolve ship_grain settlement with shared clamping. Uses pre-turn…, Shared expand_farm affordability/mutation. Returns (cash_after, farm_after,…, Shared build_granary affordability/mutation. Returns (cash_after,…, Shared secure_route affordability/mutation. Returns (cash_after, route_after,…, Resolve craft_goods — grain -> finished_goods capped by labour. Returns… (+21 more)

### Community 84 - "Section 10 plan — consolidated review (round 2)"
Cohesion: 0.20
Nodes (9): C1 — Correction to round 1's B4: `OperationState` is not invented, C2 — Correction to round 1's B2 reasoning (conclusion unchanged), C3 — NEW BLOCKER: `completion_summary: StrategicSummary` smuggles a history endpoint into `GameView`, C4 — NEW BLOCKER: current-turn context and latest-outcome context are conflated, C5 — `GET` must take the same per-session lock, or it can return a torn view, C6 — Test dependencies are missing, C7 — Cleanup confirmations, Section 10 plan — consolidated review (round 2) (+1 more)

### Community 85 - "test_two_markets_route.py"
Cohesion: 0.09
Nodes (30): River Route — single route between Home Valley and River Town (Section 5).…, RouteState, _base_state(), Section 5 — Two Markets and One Trade Route acceptance tests. AC 1: Home Valley…, AC2: Transport cost can erase apparent arbitrage profit., AC3: Route capacity limits shipped quantity., AC4: Profitability depends on market supply/demand divergence, not scripted…, AC5: Player can complete turn staying in Home Valley (no trade). (+22 more)

### Community 86 - "test_api.py"
Cohesion: 0.20
Nodes (24): asyncio, _choose(), _clear_store(), client(), _create_game(), _get_game(), Section 10 API tests — AC1-4 + C3/C4/B1 guards., Internal consistency — labelled as such, not AC4 evidence (B3 circular). (+16 more)

### Community 87 - "Section 9 — review round 3 (consolidated) — SUPERSEDES round 2 on the route"
Cohesion: 0.20
Nodes (9): Keep as-is, R1 — Retraction: round 2's route fix was buying a passing grade, R2 — Transport cost, not capacity, is what makes the route a trap, R3 — River Town is not a market at its shipped scale, R4 — Gate math is floating-point, which breaks eight sections of integer discipline, R5 — Tie handling in `run_batch` is biased and convoluted, Section 9 — review round 3 (consolidated) — SUPERSEDES round 2 on the route, What to change (+1 more)

### Community 88 - "Section 9 — review round 4 (consolidated, final) — SUPERSEDES rounds 2 and 3"
Cohesion: 0.13
Nodes (14): Do not, Final target config, R1 — The granary does not repay its cost, and `test_build_granary_not_worthless` cannot see it, R2 — But the granary is not broken. `policy_storage_heavy` is a third strawman, R3 — Revert `route.capacity` to 20. Transport cost was the entire route fix, R4 — Retract round 3's River Town rescale entirely, R5 — State the price-taking boundary explicitly instead of pretending to fix it, R6 — `hold rank ≥3` must be computed over the four intentional policies, not five (+6 more)

### Community 89 - "Orchestration Guide — how BUILD_SPEC sections get built"
Cohesion: 0.20
Nodes (9): 1. The loop, per section, 2. Driving Muse headlessly, 3. Driving ChatGPT, 4. Verification discipline (non-negotiable), 5. Standing decisions (set by the product owner), 6. Recurring failure patterns to watch for, 7. Where things live, 8. Known upcoming blockers (+1 more)

### Community 90 - "2. SHOULD-FIX"
Cohesion: 0.11
Nodes (18): 0. What is genuinely green, 1. BLOCKING, 2. SHOULD-FIX, 3. Not asked for, 4. Instruction to Muse, I10 — Quantity toggles sit outside their verb card, I11 — Two e2e assertions are weaker than they look, I12 — Zero deltas presented as changes (+10 more)

### Community 91 - "App.tsx"
Cohesion: 0.06
Nodes (49): commitChoice(), createGame(), getGame(), req(), useCommit(), useCreateGame(), useGame(), CausalNode (+41 more)

### Community 92 - "Section 13 — Plan Review, Round 1"
Cohesion: 0.20
Nodes (9): 1. What is settled — keep as planned, 2. BLOCKING — the AC1 control arm is testing the wrong thing, 3. RULING — Q5 (demand decay): keep the curve, and stop treating it as taste, 4. RULING — Q6 (`hire_labour`): ship it, capped at 1/turn, and it consumes the turn, 5. SHOULD-FIX — Crisis Reputation currently rewards passivity, not crisis, 6. SHOULD-FIX — state the labour cap interaction with Land Network explicitly, 7. Not asked for, 8. Instruction to Muse (+1 more)

### Community 93 - "harness.py"
Cohesion: 0.14
Nodes (19): BatchResult, _can_afford(), format_markdown(), policy_cash_preserving(), policy_production_heavy(), policy_random_legal(), policy_storage_heavy(), policy_trade_heavy() (+11 more)

### Community 94 - "rivals.py"
Cohesion: 0.13
Nodes (25): compute_farm_output(), cost_for_quantity(), Cost in Money for quantity at price_milli (milliunits per unit). Floor division…, Inventory value in Money at price_milli., Compute farm output for given capacity and world. Returns (farm_output,…, value_for(), _capital_bps(), _expected_return() (+17 more)

### Community 96 - "MarketState"
Cohesion: 0.15
Nodes (22): Domain package — re-exports canonical types., Pressure domain — Section 8 world-pressure arc types. Small, frozen, validated…, MarketState, OperationState, PlayerState, BaseModel, Canonical economic types for Sections 2-5. Integer-only canonical state per…, Economic operation — stub for farm/granary, extensible later. Represents a farm… (+14 more)

### Community 97 - "Section 11 — Mobile-First React Playable — Plan"
Cohesion: 0.07
Nodes (29): Appendix — Measured payload excerpts, Constraints And Non-goals, Context And Current Facts, Decision surface — see K4 above (B1 verbatim, B6 cost, R1 no arrows, B4 revision), Exact unit-conversion boundary (`format.ts`) — see K2 above, File layout for `frontend/` (scaffolded from scratch), Goal, Grill — Decision-Forcing Questions, Answers, and Consequences (retained per §1) (+21 more)

### Community 98 - "3. Design rulings — the vague spots, now decided"
Cohesion: 0.06
Nodes (33): 0. Status, 1. Settled by the grill — confirmed, do not relitigate, 2. BLOCKING, 3. Design rulings — the vague spots, now decided, 4. Correction to the DECISIONS 023 rationale — my argument was wrong, 5. Context change — rebase required, 6. Remaining should-fix, 7. Explicitly NOT being asked for (+25 more)

### Community 99 - "Section 10 implementation — review round 3"
Cohesion: 0.50
Nodes (3): D1 — BLOCKING: `test_available_choices_turn_invariant` cannot detect the defect it exists for, D2 — Secondary, Section 10 implementation — review round 3

### Community 101 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, allowImportingTsExtensions, forceConsistentCasingInFileNames, isolatedModules, jsx, lib, module, moduleResolution (+15 more)

### Community 102 - "Audit — Sections 1–10, Consolidated Review Round 2"
Cohesion: 0.25
Nodes (7): Audit — Sections 1–10, Consolidated Review Round 2, Not carried forward, R1 — BLOCKING. The type-gate fix excluded the test suite from type checking entirely., R2 — SHOULD-FIX. Buy is still capped by a harness-policy constant, which DECISIONS 017 forbids., R3 — SHOULD-FIX. A production `await` was added to serve a test; make it a documented decision., Verified good — round 1 genuinely fixed these, Work order

### Community 103 - "GameState"
Cohesion: 0.11
Nodes (22): PlayerOutcome, BaseModel, Causal trace, domain effects, and player outcome for Sections 4–5. Structural…, Concise player outcome for the turn reveal., Full result of resolving one turn., TurnResolution, GameState, Top-level canonical game state for Sections 2-5. For backward compatibility,… (+14 more)

### Community 104 - "Section 12 — Playtest Gate Instrumentation — Plan"
Cohesion: 0.11
Nodes (17): 1. Where to store the sequence, 2. Run-record format, 3. Completion screen placement, 4. Clipboard with graceful fallback (AC7), 5. Testing shape, Constraints and Non-goals, Context and Current Facts, Goal (+9 more)

### Community 105 - "devDependencies"
Cohesion: 0.12
Nodes (17): eslint, @eslint/js, devDependencies, eslint, @eslint/js, globals, @testing-library/react, @types/react (+9 more)

### Community 106 - "scripts"
Cohesion: 0.17
Nodes (12): scripts, build, dev, e2e, format, format:check, lint, lint:fix (+4 more)

### Community 107 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, allowSyntheticDefaultImports, composite, module, moduleResolution, skipLibCheck, include, playwright.config.ts (+2 more)

### Community 108 - "package.json"
Cohesion: 0.25
Nodes (7): engines, node, name, packageManager, private, type, version

### Community 109 - "dependencies"
Cohesion: 0.29
Nodes (7): dependencies, react, react-dom, @tanstack/react-query, react, react-dom, @tanstack/react-query

### Community 110 - "Section 12 — First Human Playtest: Facilitator Script"
Cohesion: 0.22
Nodes (8): 1. Before you start, 2. The three questions, 3. Observation sheet, 4. Classification — do this after each session, while it is fresh, 5. Go / no-go, 6. Handing back to the agent, 7. What is already true, so you needn't test for it, Section 12 — First Human Playtest: Facilitator Script

### Community 112 - "test_explanation.py"
Cohesion: 0.33
Nodes (8): Section 4 — multi-step drought to wealth chain tests., Same command, different world should produce different driver impacts., Drought chain must be structurally present via parent_ids and exact wealth math., _state(), test_concise_le_three_full_trace_preserved(), test_drought_to_wealth_structural_chain_exact(), test_normal_vs_drought_different_drivers(), test_story_drivers_cover_wealth_chain()

### Community 114 - "cli.py"
Cohesion: 0.27
Nodes (11): format_market_pulse(), format_player_state(), format_rivals(), format_route_state(), main(), parse_choice(), parse_choices_arg(), Thin CLI for the five-turn headless prototype — Section 6. Pure I/O around… (+3 more)

### Community 115 - "Section 13 — Design Direction (Claude, design authority)"
Cohesion: 0.22
Nodes (8): 1. The thesis, stated operationally, 2. Lowest-complexity mechanic that delivers it, 3. Legacies — earned, deterministic, and one must bite, 4. AC1 must be MEASURED, not argued, 5. Scope boundary — engine first, minimal UI reuse, 6. Turn budget, 7. What is out of scope, Section 13 — Design Direction (Claude, design authority)

### Community 119 - "Section 13 — City & Craft Transition Epilogue — Plan"
Cohesion: 0.05
Nodes (40): 0. Reading list (what this plan rests on), 10. Risks / Rollback, 11. Open Questions, 12. Self-grill, 1. Goal, 2. AC1 / AC2 measurement design — fixed before any run, 3. Success Criteria, 4. Context and Current Facts (+32 more)

### Community 125 - "test_invariants.py"
Cohesion: 0.31
Nodes (10): _bounded_price(), Bound movement toward target_price within max_movement_bps of current., Integer-safe target price from supply/demand., _target_price(), Invariant and property tests for Section 3 — AC #2, #4., test_bounded_price_monotonic_with_supply(), test_demand_unchanged_cannot_reduce_target_when_supply_falls(), test_price_stays_positive_extreme() (+2 more)

### Community 129 - "test_rounding.py"
Cohesion: 0.18
Nodes (17): apply_basis_points(), clamp_non_negative(), div_round_half_up(), mul_basis_points(), Deterministic integer rounding helpers for canonical economic math. All…, Multiply value by basis points (10_000 = 100%) with floor division.…, Alias for mul_basis_points — semantic for price adjustments., Integer division rounding half away from zero for positive denominators. For… (+9 more)

### Community 131 - "default_start_state"
Cohesion: 0.18
Nodes (13): _epilogue_command(), format_four_arm(), FourArmResult, _median(), BaseModel, Four-arm epilogue harness — Section 13 AC1 measurement. Arms (paired, same…, Uniform epilogue policy: craft if possible, else sell finished, else sell…, run_four_arm() (+5 more)

### Community 132 - "SECTION 20 — Visual Asset System and Polish"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Goal, In scope, SECTION 20 — Visual Asset System and Polish, Stop condition

### Community 133 - "Part VIII — Agent Guardrails"
Cohesion: 0.40
Nodes (5): 31. Do Not Build Ahead, 32. Do Not Rewrite Working Systems Without Evidence, 33. Dependencies Require Justification, 34. Agent Completion Report Template, Part VIII — Agent Guardrails

## Knowledge Gaps
- **853 isolated node(s):** `historical-empire-backend`, `name`, `private`, `version`, `type` (+848 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PlayerCommand` connect `PlayerCommand` to `MarketState`, `test_pressure_arc.py`, `default_start_state`, `test_five_turn_prototype.py`, `mappers.py`, `test_balance_harness.py`, `GameState`, `test_causal_trace.py`, `FiveTurnGame`, `InventoryState`, `test_explanation.py`, `cli.py`, `turn.py`, `test_invariants.py`, `test_api.py`, `test_two_markets_route.py`, `harness.py`, `rivals.py`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `FiveTurnGame` connect `FiveTurnGame` to `MarketState`, `test_pressure_arc.py`, `PlayerCommand`, `default_start_state`, `test_five_turn_prototype.py`, `mappers.py`, `test_balance_harness.py`, `GameState`, `InventoryState`, `cli.py`, `test_two_markets_route.py`, `test_api.py`, `harness.py`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `resolve_turn()` connect `PlayerCommand` to `MarketState`, `test_pressure_arc.py`, `test_rounding.py`, `test_five_turn_prototype.py`, `mappers.py`, `GameState`, `test_causal_trace.py`, `test_balance_harness.py`, `InventoryState`, `test_explanation.py`, `turn.py`, `test_two_markets_route.py`, `test_api.py`, `test_invariants.py`, `rivals.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `PlayerCommand` (e.g. with `GameSession` and `FourArmResult`) actually correct?**
  _`PlayerCommand` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `FiveTurnGame` (e.g. with `GameSession` and `FourArmResult`) actually correct?**
  _`FiveTurnGame` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `GameState` (e.g. with `CausalNode` and `CausalTrace`) actually correct?**
  _`GameState` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `InventoryState` (e.g. with `EightTurnGame` and `FiveTurnGame`) actually correct?**
  _`InventoryState` has 10 INFERRED edges - model-reasoned connections that need verification._