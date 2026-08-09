# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 2 — COMPLETE (2026-08-09)

**Core types + deterministic RNG:** canonical integer types, 6 domain models, BLAKE2b substreams via unambiguous JSON encoding, rounding helpers, all Section 2 AC green.

### What exists

```
backend/
  app/
    __init__.py              # empty package marker
    domain/
      __init__.py            # re-exports canonical types
      types.py               # Money/Quantity/BasisPoints/PriceMilliunits + GameState/PlayerState/MarketState/OperationState/InventoryState/TurnContext (frozen, ge=0)
    engine/
      __init__.py            # re-exports RNG + rounding
      rng.py                 # derive_seed/make_rng/rng_for — JSON canonical [run_seed,ver,turn,ns,eid,ord] -> blake2b(digest_size=8) -> int seed, no global random/hash()
      rounding.py            # mul_basis_points/apply_basis_points/div_round_half_up/clamp_non_negative (deterministic, no float)
  tests/
    test_sanity.py           # import-only harness test
    test_engine_purity.py    # AST rglob import-boundary guard for engine/ + domain/
    test_core_types.py       # AC #1,2: integer + negative rejection, frozen
    test_determinism.py      # AC #3,4,5,6: stable seeds + golden values + namespace divergence + global-random/hash() scan (all engine files) + delimiter-collision regression
    test_rounding.py         # AC #6: basis-points + div rounding
  pyproject.toml             # uv project: pytest + ruff + pyright (strict) + pydantic>=2.7
  uv.lock                    # 15 packages (adds pydantic, annotated-types)
  .venv/                     # created by uv sync --project backend
Makefile                     # test / lint / type / format / format-check wrappers
.gitignore                   # Python + uv + Vite + OS/IDE
.python-version              # 3.12 (root only)
AGENTS.md / backend/AGENTS.md / frontend/AGENTS.md
DECISIONS.md (001-009)
BUILD_SPEC.md Status: Section 2 COMPLETE
docs/plans/
  2026-08-09-section-1-walking-skeleton.md
  2026-08-09-section-2-core-types.md
frontend/                    # placeholder for Section 11 (Vite+React)
docs/
```

### Boundaries

- `backend/app/engine` and `backend/app/domain` are pure: no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk` imports. Enforced by AST rglob test. `pydantic` is now allowed in domain/engine for validated canonical types (Section 2).
- Canonical state is frozen and has single source of truth for capacities: `PlayerState{cash, inventory, farm_capacity, storage_capacity}` — no `operations: list` embedding (avoids mutable-list + duplicate-capacity incoherence). `OperationState` exists as standalone type for Section 5+.
- Deterministic RNG: `derive_seed` uses JSON array canonical encoding so delimiter-containing strings cannot collide; global `random.*` and built-in `hash()` are banned via AST scan of all `engine/**/*.py`, not just `rng.py`.
- `backend/pyproject.toml` is the single Python project. No `fastapi`/`sqlalchemy` until Section 10.
- Ruff/pyright scoped to `backend` only — `AGENTS.md` / plans not formatted.

### Normal verification

```bash
uv sync --project backend
make test              # = uv run --project backend pytest -v
make lint              # = ruff check backend
make type              # = pyright
make format-check      # = ruff format --check backend
make format            # actually formats backend/
```

### Last known green

```
uv sync --project backend  → Resolved 15 packages, 0 errors
pytest -v                  → 27 passed (7 core + 7 rounding + 11 determinism + 2 purity/sanity)
ruff check backend         → All checks passed
ruff format --check backend→ 13 files already formatted
pyright                    → 0 errors, 0 warnings
```

**Normal cache note:** `~/.cache/uv/sdists-v9/.git` is a 0-byte file with `com.apple.provenance` xattr blocking `uv` init. Fix in your Terminal outside Muse:

```bash
xattr -d com.apple.provenance ~/.cache/uv/sdists-v9/.git
rm ~/.cache/uv/sdists-v9/.git
uv cache prune
# then re-run the four gates above without UV_CACHE_DIR
```

After that, no environmental caveat remains.

### Decisions relevant to future work

- `uv` + Python 3.12, `ruff` (line-length 100, py312) + `pyright` strict (`reportMissingTypeStubs=warning`)
- Beta Acid layout `Router -> Service -> Client` deferred to Section 10; engine stays import-clean
- High autonomy within a Section; always `/plan` before Section, `/grill` then `/goal`; stop at gate and report
- Coverage tracked but not gating until Section 3-4; heavy unit on engine/domain/services, some integration, limited Playwright
- `backend/pyproject.toml` location; root `Makefile` wrappers; `backend/uv.lock` tracked
- Section 2 decisions: `pydantic` now for validated integer types; JSON canonical encoding for RNG; capacities single-source in `PlayerState`

### Intentionally missing (do not build early)

Market kernel (Section 3), causal trace (Section 4), two markets + river route (Section 5), headless prototype (Section 6), rivals (Section 7), etc. No FastAPI routes, DB/SQLAlchemy, React UI, content framework, LLMs.

### Next milestone

**Section 3 — One-Turn Grain Market Kernel** — implement `resolve_turn` for grain market: drought→production→supply→price pressure→price, with player commands (expand_farm/build_granary/buy_grain/hold), deterministic causal trace, and CLI demo.
