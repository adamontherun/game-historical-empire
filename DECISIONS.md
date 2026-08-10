# Decisions

Record of accepted decisions that constrain implementation. `BUILD_SPEC.md` active Section takes precedence; this file records choices that refine it.

## 001 — Scope Strategy (2026-08-09)

- **Context:** The product vision in `BUILD_SPEC.md` Part I describes a multi-era dynasty game (8 economic regimes). The first playable is a 5-turn Agricultural grain prototype.
- **Decision:** `BUILD_SPEC.md` is the current implementation authority. Future systems (all eight ages, spoilage, credit, brands, automation, generic content framework, LLMs for rival economy) must not be built early without an active Section requiring them.
- **Scope contract (verbatim from `BUILD_SPEC.md:636`):**
  - the original product vision is intentionally broader than the first playable
  - this ordered specification is the current implementation authority
  - future systems must not be built early without an active section requiring them
- **Rationale:** Prove the core loop (observe → choose → commit → consequence → understand → adapt) before expanding scope. Keeps architecture concrete.
- **Consequence:** Agents work Section-by-Section, stop at each gate, and only update the `Status` line after acceptance criteria pass.

## 002 — FastAPI Conventions (2026-08-09)

- **Decision:** Follow [Beta Acid FastAPI Reference App](https://github.com/betaacid/FastAPI-Reference-App) conventions for the backend:
  - `Router -> Service -> Database Client -> Database` (and `-> Networking Client -> external API`)
  - Services and DB clients are plain module-level functions receiving dependencies as args; `Depends` only at the edge in `app/dependencies.py`
  - Classes only when holding real state/resources (e.g., `httpx.AsyncClient` pool)
  - File naming: `characters_service.py`, not `characters.py`
  - Async I/O (`AsyncSession`, `httpx.AsyncClient`), pure `domain/` stays sync
  - Transaction boundary in `get_db_session`; clients only `add`/`flush`
  - Lazy engine creation so imports don't require `DATABASE_URL`
- **Consequence:** `backend/app/engine` and `domain` remain pure and import no FastAPI/SQLAlchemy code.

## 003 — Tooling (2026-08-09)

- **Decision:** `uv` + Python 3.12, `ruff` (lint+format) + `pyright` strict, `pytest`. Add `pytest-asyncio` only when genuine async tests are introduced. Conventional Commits. OpenAPI at `/docs`.
- **Consequence:** Section 1 gates require `ruff check`, `ruff format --check`, and `pyright` to pass.

## 004 — Testing Strategy (2026-08-09)

- **Decision:** Heavy unit coverage for `engine`/`domain`/`services` (mocked, no DB/network), some integration tests (real Postgres with rollback via `integration_client`), limited Playwright for critical 5-turn mobile flow only. Coverage is tracked but not blocking until Sections 3–4 stabilize; future target is 90%+ on engine/domain/services, 80%+ overall.
- **Consequence:** No coverage gate blocks PRs initially; `pytest --cov` reports are informational.

## 005 — Frontend Stack (2026-08-09)

- **Decision:** Vite + React + TypeScript + TanStack Query. Mobile-first (`390×844` excellent, desktop usable). Backend exposes presentation-oriented `GameView` with optimistic `revision` concurrency.
- **Consequence:** Frontend added at Section 11; no SSR framework needed.

## 006 — Persistence (2026-08-09)

- **Decision:** In-memory sessions until Section 16. At Section 16: Postgres + SQLAlchemy async + Alembic (sync migrations), snapshot-first persistence.
- **Consequence:** No `DATABASE_URL` required before Section 10; `render.yaml` remains minimal until then.

## 007 — Autonomy (2026-08-09)

- **Decision:** Agent is highly autonomous within an active Section — do not check in frequently. Check in only for genuine ambiguity (two interpretations would change accepted behavior), blocked dependencies, or scope-expanding decisions. After each Section, stop, report (files changed, commands, tests/results, risks), and wait for go-ahead before the next Section.

## 008 — Plan Mode (2026-08-09) — revised 2026-08-09

- **Decision:** Section workflow is `/plan` (creates draft in `docs/plans/`) → Approve / Request changes (single gate) → implement. The former `/grill` and `/goal` skills are not part of the required path — grill-type pressure testing, when needed, is surfaced as open questions inside the plan itself. The Muse approval gate is the only gate.

## 009 — Feature Branch per Section (2026-08-09)

- **Decision:** Create feature branch `section/<n>-<slug>` at the **start** of each Section (before `/plan`), and push it to GitHub `adamontherun` after implementation (`git push -u origin section/<n>-<slug>`), including the Section's files + updated `STATE.md`.

## 010 — Five-Turn Authored Arc & Supply-as-Stock (2026-08-09)

- **Context:** Section 6 is the first multi-turn prototype. `MarketState.supply` was previously `next = stock + farm_output` with no consumption, which monotonically accumulated over repeated turns and would collapse prices. The review gate required defining supply semantics before building the 5-turn loop.
- **Decision:** Define `MarketState.supply` as a regional market-availability signal/index at the start of the turn, **not** a literal conserved physical stock. Home Valley signal evolves as `signal_next = max(0, signal + farm_output - demand)` where `demand` is the regional consumption index for the turn; price is set on `signal_next` via the existing `_target_price` guard (`max(signal_next,1)`). The same `farm_output` also enters player inventory — for this prototype no conservation is implied between the regional signal and player inventory (coherent ownership/flow accounting is deferred to Section 14). River Town signal remains stable (exogenous) for Section 6. `TURN_SPECS` is a hardcoded 5-element authored arc (T1 normal high demand, T2 normal surplus weak, T3 normal warning, T4 drought, T5 normal aftermath) with truthful prose that describes actual state (surplus emergent from accumulation, not per-turn harvest differences). Determinism is via choices (`same seed+choices → same`), not via seed variation, and cross-seed "no dominant strategy" is deferred to Sections 8/9 (but Section 6 now demonstrates tradeoffs, see AC5 non-dominance test).
- **Consequence:** The 5-turn game is bounded (no accumulation hack), signals are truthful, and the three scripted policies (farm-heavy, storage-heavy, trade-heavy) plus hold are each exactly 5 legal commands and diverge with tradeoffs. `FiveTurnGame` owns `GameState`+`history` outside the frozen `GameState`, calls `resolve_turn` once per turn with validated `rng_context`, and enforces exactly 5 submissions with `start_state.turn == 0`. CLI `backend/app/cli.py` is thin (interactive + `--choices` non-interactive).
- **Rationale:** Minimal coherent economics without requiring literal stock conservation; keeps the kernel as authority and makes the drought → farm_output → signal → price chain inspectable. A true physical-stock model with ownership would add unnecessary complexity for the 5-turn proof.

## 011 — Deterministic Rivals — Shared Primitives, Structured Threat, Integer Scoring (2026-08-09)

- **Context:** Section 7 adds Mira/Daran. The naive plan duplicated harvest/buy/storage/ship math in `rivals.py` with same constants, which would drift. Scoring used floats with epsilon tie, parsed signal prose for threat, and mixed personality with starting resources. History stored only headlines.
- **Decision:** (1) Extract shared actor primitives to `backend/app/engine/actor.py` (`compute_farm_output`, `resolve_buy`, `resolve_storage_settlement`, `resolve_shipment`, `value_for`/`cost_for_quantity` plus `YIELD_PER_CAPACITY`/`DROUGHT_BPS`/`COSTS`) and have both `turn.py` and `rivals.py` call them — `turn.py` keeps market resolution and trace, no generic engine. (2) Two-phase timing: rivals choose from pre-turn `ObservableContext{world_now, next_world_known, home_price_pre…}`, player/world market resolves, then rivals settle with `buy@pre_home`, `shipment@resolved_river`, `valuation@resolved_home`. (3) Integer/bps scoring `score = expected_return × pref_bps × capital_bps × risk_bps × exposure_bps` via `mul_basis_points`/`div_round_half_up`, prefs as bps (Mira 4500/15000/13000/14500 farm-averse, Daran 16000/7000 farm-hungry), exact integer tie → `rng_for(..., "rival", rival_id, 0)` only. (4) Structured threat `next_world_known` (`_next_world_known_for_turn(idx)==drought` only on T3 warning, derived from `TURN_SPECS` index, never `signal.contains("warning")`). (5) Separate `RivalProfile` (prefs/risk/exposure) vs `RivalState` (cash/inventory/farm/storage/route, no headline) with identical-state personality tests (≥2 diffs, Mira storage/trade > Daran, Daran farm > Mira). (6) Store full `RivalTurnResult{rival_id, before, command, after, headline, cash/qty/price/wealth deltas}` as `rival_history: tuple[tuple[Mira,Daran],5]`, derive `rival_headlines_history`, headline only in turn result. Wealth includes price revaluation `cash_effect+quantity_value_effect+price_value_effect`. (7) Replace scripted T3 headline assert with behavioral tests across surplus/warning/drought/lowcash/tight contexts (Mira prep > baseline and prep>farm on warning, Daran farm>prep, fingerprint suite). Rivals remain session-owned in `FiveTurnGame`, isolated from shared availability signal (isolation test), not in `GameState`.
- **Consequence:** No duplicated economy, stable integer determinism, threat drives behavior without prose parsing, personality proven independent of starting resources, full history enables determinism/debugging/API projection and correct no-money-creation invariant, behavioral tests avoid backward-designing scores to headlines.
- **Rationale:** Author cause (`TURN_SPECS` warning → structured `next_world_known`) then simulate consequences via scoring → rival action → truthful headline, keeping the same economic rules and timing as the player.

## 012 — Pressure as Turn-Derived Session-Authored Arc (2026-08-10)

- **Context:** Section 8 adds a world-pressure arc `normal→early_dry→worsening_dry→drought→aftermath`. The risk was storing pressure as canonical `GameState` field, creating a second source of truth that could hold `early_dry`+`drought` (F1/F2), and scattering the causal_source_id formula between domain and engine (F3). The 5-turn game is still in-memory (no persistence until Section 16), and rivals already model turn-derived `next_world_known` without canonical storage.
- **Decision:** (1) Model pressure in a distinct `backend/app/domain/pressure.py` (not `types.py` catch-all) as `PressureStage` literal + frozen `PressureState{pressure_id, stage, activation_turn, world, signal, title, causal_source_id}` — exactly 7 fields, no `world_modifiers`. Validator enforces biconditional `stage=="drought" <=> world=="drought"` (every other stage => `world=="normal"`) and that `causal_source_id == f"pressure:{pressure_id}:{stage}"` (single source; explicit override must match or raise). (2) Author the single hard-coded `PRESSURE_ARC: tuple[PressureState,5]` in `backend/app/engine/pressure.py` (activation_turn==index validated at import, truthful rainfall prose, T2 title keeps `Surplus`, no JSON loader/weighted sampler/DSL). (3) Keep pressure **turn-derived/session-authored** (R1/F2): `FiveTurnGame` owns progression via `pressure_for_turn(idx)` / `next_world_known_for_turn(idx)` (only `worsening_dry→drought`, not prose parsing) and exposes `current_pressure: PressureState|None` (`None` when `is_complete`, else `pressure_for_turn(len(history))`); `TURN_SPECS` is derived `tuple(TurnSpec(world=p.world,... for p in PRESSURE_ARC))` for backward compat. (4) `resolve_turn(state, command, pressure: PressureState, rng_context)` derives `world = pressure.world` internally (legacy bare `"normal"/"drought"` string still accepted via shim for pre-8 tests) and emits leading `pressure_stage` node (`kind="pressure"`, `delta=None`, `reason_code=pressure.causal_source_id` directly, not recomputed) as parent of `world` (`pressure_stage→world→farm_output→home_supply→home_price→…→wealth`), preserving systemic `drought→farm_output→supply→price` and admitting via existing `trace.py` delta-None fallback (no validator loosening). `TURN_ORDER` updated to `pressure_stage -> world -> command -> ...`. (5) AC1/AC3 instrument is mechanism+warning-isolated: both histories share T1 `hold` (timing) and avoid `expand_farm` in either arm (so `home_supply` formula provably yields identical T4 market); test asserts equality pre-condition `supply 100==100`, `price 4750==4750`, `farm_output 60==60` (seed-8-useful) before asserting threshold-free exposure difference `price_value 130 vs 104`, `inventory 250 vs 200`, `wealth 130 vs 104` (fully affordable, no `insufficient_*`). (6) Structural smallness is proven by field count and file-text scan (no `json`/`random`/`weighted`/`sampler`), not line count.
- **Consequence:** Pressure is deterministic and inspectable (`pressure_for_turn`, `current_pressure`, trace) without canonical duplication, the invalid `early_dry+drought` state is impossible at construction time, the causal_source_id cannot silently diverge between domain and trace, and the warning usefulness test actually proves the warning mattered rather than that policies differ.
- **Rationale:** Single source of truth for `world` (one PRESSURE_ARC, one PressureState, one derive in `resolve_turn`) keeps the five-turn story coherent and anticipatory without adding a generic content framework until Section 15.
