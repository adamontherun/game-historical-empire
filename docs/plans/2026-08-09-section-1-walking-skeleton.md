# Plan — Section 1: Repository Contract and Walking Skeleton

## Goal

Create the smallest repository structure and development contract needed to build and test a pure Python game engine. No gameplay beyond a trivial test fixture. Prove the repo can install, lint, typecheck, and run a deterministic engine test.

`BUILD_SPEC.md:608` — Status: NOT STARTED. This plan covers only Section 1 scope.

## Success Criteria

What must be true for Section 1 to be done (maps to acceptance criteria):

1. `uv sync` from a clean checkout installs backend dependencies without error (run from `backend/` where `backend/pyproject.toml` lives, or via `uv sync --project backend`)
2. Single command runs backend tests successfully — `make test` and `uv run --project backend pytest` both pass, trivial engine test passes
3. Linting and type checking commands exist and pass — `make lint`, `make type`, and the underlying `uv run --project backend ruff check .` / `ruff format --check .` / `pyright` (strict with `reportMissingTypeStubs=warning`)
4. `backend/app/engine` and `backend/app/domain` import no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk` — verified by `backend/tests/test_engine_purity.py` (source grep + `sys.modules` check)
5. `DECISIONS.md` records the scope strategy with verbatim 3 bullets from spec — gate checks exact strings
6. No future systems are scaffolded (no `routers/`, `services/`, `clients/`, `models/`, `schemas/`, `database.py`, `main.py`, rivals, content loader, LLM code)

Stop condition: the repository can run a trivial pure-engine test and all baseline checks pass. Do not build Section 2+.

## Context And Current Facts

- Repo contains only `BUILD_SPEC.md`, `AGENTS.md` (root + `backend/`/`frontend/`), `DECISIONS.md`, empty `backend/`, `frontend/`, `docs/` — no Python config, no source, no tests yet [observed `ls -R`].
- Decisions settled (DECISIONS.md 001–008): `uv` + Python 3.12, `ruff` + `pyright` strict, Beta Acid layout (`Routers -> Services -> Clients`), functions-over-classes, heavy unit tests on engine/domain/services, Vite+React later, plan-mode required, high autonomy.
- `DECISIONS.md:001` covers scope strategy in paraphrase; grill requires verbatim 3 bullets from `BUILD_SPEC.md:636` to guarantee gate 5 string-match — will be updated in implementation.
- Hosting is Render but no `render.yaml` needed until Section 10/16 — explicitly out of scope.
- Python 3.12 on Render, matches reference app (`>=3.10`), aligns with `AGENTS.md:2`.
- Grill settled: `backend/pyproject.toml` (not root), root `Makefile` wrappers, keep deps minimal (no FastAPI/Pydantic in Section 1), `pyright` strict with `reportMissingTypeStubs=warning`, simple purity test.

## Constraints And Non-goals

- **In scope:** directory skeleton `backend/app/domain`, `backend/app/engine`, `backend/tests`, `frontend/`, `docs/`; baseline Python project config at `backend/pyproject.toml`; root `Makefile` wrappers; `uv` lockfile; trivial deterministic engine module + two tests; verbatim `DECISIONS.md` update; purity guard.
- **Out of scope (BUILD_SPEC.md:644):** real economy logic, FastAPI routes, `fastapi`/`pydantic`/`sqlalchemy`/`httpx` runtime deps, database, React UI, rivals, content framework, LLM integration, authentication, deployment, `render.yaml`, Alembic, game types beyond trivial fixture.
- **Constraints:** `backend/app/engine` and `backend/app/domain` must remain import-clean; only the `Status` line of `BUILD_SPEC.md` may be updated after gates pass; don't invent abstractions before 2 use cases.

## Key Decisions

| Decision | Settled choice | Why | Alternative rejected |
|---|---|---|---|
| **Project config location** | `backend/pyproject.toml` with `[tool.pytest.ini_options] testpaths = ["tests"]` and `pythonpath = ["."]` semantics via `backend` as project root | Isolates backend as its own `uv` project; `uv sync --project backend` works from repo root; `uv run --project backend pytest` is the canonical test command; avoids root-level `pythonpath = ["backend"]` indirection that `pyright` may not honor | Single `pyproject.toml` at repo root with `pythonpath = ["backend"]` — simpler but rejected in grill (extraPaths for pyright, Render expects backend as service root) |
| **Package layout** | `backend/app/__init__.py`, `backend/app/domain/__init__.py`, `backend/app/engine/__init__.py`, `backend/tests/__init__.py` | Satisfies `BUILD_SPEC.md:620` explicitly; `app` importable as `app.engine` when `backend` is on `PYTHONPATH` / project root | Flat `backend/engine/` — violates spec path |
| **Dependencies** | Minimal — only what Section 1 uses: `pytest>=9`, `pytest-asyncio>=1`, `ruff>=0.8`, `pyright>=1.1` (or `basedpyright`) as dev deps; no `fastapi`, `pydantic`, `sqlalchemy`, `httpx` | Keeps Section 1 lean, satisfies gate 6 (no premature scaffolding); FastAPI/Pydantic deferred to Section 10 per BUILD_SPEC | Include FastAPI/Pydantic now — scope creep flagged in grill and explicitly excluded this revision |
| **Root Makefile** | Add `Makefile` at repo root with `test`, `lint`, `type`, `format` wrappers delegating to `uv run --project backend ...` | Gives stable one-command contract (`make test`) alongside direct `uv` commands; satisfies "commands exist" for both audiences (human + CI) | No Makefile — would satisfy gates but grill chose wrapper for stability |
| **Engine fixture** | `backend/app/engine/__init__.py` exposes `def add(a: int, b: int) -> int: return a + b` (+ `__all__`) | Trivial deterministic pure function, fully typed, easy determinism check, no economy assumptions, import-clean | `echo` or `GameState` stub — `add` is clearer for determinism smoke |
| **Test layout** | `backend/tests/test_sanity.py` + `backend/tests/test_engine_purity.py` | `test_sanity` proves harness + determinism; `test_engine_purity` enforces gate 4 via source grep + `sys.modules` check | Single test file — conflates harness vs purity enforcement |
| **Tool config** | `ruff` in `backend/pyproject.toml` (`line-length 100`, `target-version py312`); `pyright` in same `pyproject.toml` with `typeCheckingMode = "strict"` + `reportMissingTypeStubs = "warning"` + `extraPaths` if needed | Single config file per project, matches grilled decision; `ruff check` + `ruff format --check` as CI gates | Separate `ruff.toml` / `pyrightconfig.json` — more files, same effect |
| **Test runner mode** | `asyncio_mode = "auto"` in `backend/pyproject.toml` | Matches reference app, enables future `async def test_*` without decorator; harmless for sync test | Omit — would require retrofit at Section 3 |

## Recommended Approach

Keep `backend/` as the Python project root (`backend/pyproject.toml`, `backend/uv.lock`). Add a tiny root `Makefile` that delegates to `uv run --project backend ...` so both `make test` and direct `uv` commands satisfy the gates. Implement a single pure `engine` function (no I/O, no randomness, no imports) and two tiny tests: sanity + purity guard. Update `DECISIONS.md:001` to copy the verbatim 3 bullets from spec. Verify with both `uv` and `make` entry points before marking complete.

No `backend/main.py`, no `backend/database.py`, no `backend/app/routers|services|clients|models|schemas|errors` yet — those are Section 10+.

## Work Plan

Order matters — earlier steps unblock later verification.

### 1. Create directory skeleton + `__init__.py` (no behavior)
- **Surface:** filesystem
- **Files:** `backend/app/__init__.py`, `backend/app/domain/__init__.py`, `backend/app/engine/__init__.py`, `backend/tests/__init__.py`, ensure `frontend/.gitkeep` and `docs/.gitkeep` exist (backend/AGENTS.md etc. already exist)
- **Dependency:** none
- **Acceptance:** `ls -R backend/app` shows only `__init__.py` files

### 2. Create `backend/pyproject.toml`, `backend/.python-version`, root `Makefile`, `.gitignore`
- **Surface:** `backend/pyproject.toml` + repo root `Makefile`
- **`backend/pyproject.toml` content:** `[project] name = "historical-empire-backend"`, `requires-python >=3.12`, `[dependency-groups].dev = ["pytest>=9","pytest-asyncio>=1","ruff>=0.8","pyright>=1.1"]`; `[tool.pytest.ini_options] testpaths = ["tests"]`, `asyncio_mode = "auto"`; `[tool.ruff]` `line-length = 100`, `target-version = "py312"`; `[tool.ruff.format]`; `[tool.pyright]` `typeCheckingMode = "strict"`, `reportMissingTypeStubs = "warning"` (+ `extraPaths` = `[]` if needed)
- **`.python-version`:** `3.12` in `backend/` (and optionally repo root for `uv` discovery)
- **`Makefile` at repo root (grilled decision):**
  ```make
  .PHONY: test lint type format
  test:    ; uv run --project backend pytest -v
  lint:    ; uv run --project backend ruff check .
  type:    ; uv run --project backend pyright
  format:  ; uv run --project backend ruff format --check .
  ```
- **`.gitignore` entries:** `.venv/`, `__pycache__/`, `.pytest_cache/`, `uv.lock`? (keep `uv.lock` tracked per `uv` convention — do not ignore)
- **Dependency:** 1

### 3. Create trivial pure engine module
- **Surface:** `backend/app/engine/__init__.py`
- **Content:** ~6 lines: `from __future__ import annotations` + `__all__ = ["add"]` + `def add(a: int, b: int) -> int: return a + b`; no imports of web/DB/LLM packages; fully typed
- **Dependency:** 2

### 4. Create trivial deterministic engine tests
- **Surface:** `backend/tests/test_sanity.py`, `backend/tests/test_engine_purity.py`
- **`test_sanity.py`:** `from app.engine import add; def test_add_deterministic() -> None: assert add(2,3)==5; assert add(2,3)==add(2,3)`
- **`test_engine_purity.py`:** reads `backend/app/engine/__init__.py` and `backend/app/domain/__init__.py` sources, asserts none of `import fastapi`, `import sqlalchemy`, `import httpx`, `import asyncpg`, `import openai`, `import clerk` appear; also `import app.engine` then checks `sys.modules` contains none of those keys
- **Dependency:** 3

### 5. Update `DECISIONS.md:001` with verbatim bullets
- **Surface:** `DECISIONS.md`
- **Change:** Ensure the entry contains exactly:
  - `the original product vision is intentionally broader than the first playable`
  - `this ordered specification is the current implementation authority`
  - `future systems must not be built early without an active section requiring them`
  (in addition to existing Decision/Rationale/Consequence prose)
- **Dependency:** none (can happen in parallel with 3–4)

### 6. Verify baseline checks + generate lockfile
- **Surface:** shell
- **Commands (must all pass):**
  ```bash
  uv sync --project backend
  uv run --project backend pytest -v
  make test
  uv run --project backend ruff check .
  uv run --project backend ruff format --check .
  uv run --project backend pyright
  make lint
  make type
  grep -r "import fastapi" backend/app/engine || echo "clean"
  ```
- **Generates:** `backend/uv.lock`
- **Dependency:** 2–5

### 7. Update `BUILD_SPEC.md` Status line only if all gates pass
- **Change:** `**Status:** NOT STARTED` → `**Status:** COMPLETE` for Section 1 only (line 608 block)
- **Dependency:** 6

No frontend work. No `backend/main.py` / `database.py` / `app/routers|services|clients` until Section 10.

## Validation Plan

Concrete evidence for each acceptance criterion — run after Work Plan 6:

| Gate | Command / Check | Expected evidence |
|---|---|---|
| 1. Install | `rm -rf backend/.venv && uv sync --project backend` (or `cd backend && uv sync`) | Exit 0, `backend/.venv` created, no resolution errors |
| 2. Test (direct) | `uv run --project backend pytest -v` | `2 passed` (sanity + purity) |
| 2. Test (make) | `make test` | Same `2 passed` — wrapper delegates correctly |
| 3a. Lint exists | `make lint` and `uv run --project backend ruff check .` | Exit 0 |
| 3b. Format exists | `make format` and `uv run --project backend ruff format --check .` | Exit 0 |
| 3c. Type exists | `make type` and `uv run --project backend pyright` | Exit 0 with `typeCheckingMode strict` |
| 4. Engine purity | `uv run --project backend pytest backend/tests/test_engine_purity.py -v` + `grep -R "import fastapi\|import sqlalchemy" backend/app/engine backend/app/domain` | Test passes, grep returns no matches |
| 5. DECISIONS.md wording | `grep -c "this ordered specification is the current implementation authority" DECISIONS.md && grep -c "future systems must not be built early" DECISIONS.md` | Each ≥1 |
| 6. No future scaffolding | `ls -R backend/app && ls backend/*.py 2>&1` | Only `app/__init__.py`, `app/domain/__init__.py`, `app/engine/__init__.py`, `tests/__init__.py`; no `main.py`, `database.py`, `routers/`, `services/`, `clients/`, `models/`, `schemas/` |
| Determinism smoke | `uv run --project backend pytest backend/tests/test_sanity.py -v` twice | Identical output both runs |

Run all gates in one shell sequence before marking complete.

## Risks / Rollback

- **Risk:** `pyright` strict fails on trivial `__init__.py` due to missing `py.typed` or `extraPaths` misconfig — mitigated with `reportMissingTypeStubs = "warning"` and `extraPaths` if needed; if still noisy, switch to `basedpyright` in `backend/pyproject.toml` without changing Section scope.
- **Risk:** `backend/pyproject.toml` vs root `Makefile` drift (Makefile's `uv run --project backend` must match backend project name) — verify both entry points in Validation Plan.
- **Risk:** `uv` not on CI — keep `uv` as primary per grill; fallback is `pip install -e backend` but not implemented in Section 1.
- **Rollback:** Revert with `rm -rf backend/app/domain backend/app/engine backend/tests backend/pyproject.toml backend/uv.lock backend/.venv Makefile backend/.python-version && git restore BUILD_SPEC.md DECISIONS.md` (DECISIONS.md wording reverts). Plan file itself is safe to keep.

## Implementation outcome (audit superseded draft assumptions)

During implementation the draft plan was superseded by audit findings. The following were removed or narrowed to keep Section 1 minimal:

- `pytest-asyncio` / `asyncio_mode = auto` — removed; add `pytest-asyncio` only when genuine async tests are introduced
- duplicate `backend/.python-version` — removed, keep root `.python-version` only
- placeholder `add(a, b)` in `backend/app/engine/__init__.py` — removed; `__init__.py` files are empty, `test_sanity.py` now proves only that `app.engine`/`app.domain` import
- grep/`sys.modules`-based purity test — replaced with recursive AST `rglob("*.py")` import-boundary test covering future `engine/*.py` and `domain/*.py` files
- repo-wide Ruff targets (`ruff check .` / `ruff format .`) — narrowed to `ruff check backend` / `ruff format backend` so `AGENTS.md` and plans are not formatted

## Open Questions

- None — grill-settled. One verified assumption: `DECISIONS.md:001` will be edited to include verbatim 3 bullets; `Makefile` is a thin wrapper only and does not constitute future-system scaffolding.

---

**No implementation is part of this plan revision** — this file was rewritten in place per request. Awaiting approval to proceed to implementation via `/goal`.
