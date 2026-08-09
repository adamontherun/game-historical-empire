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
