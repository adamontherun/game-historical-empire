# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 1 — COMPLETE (2026-08-09)

**Walking skeleton:** repository can install, lint, typecheck, and run a pure-engine import test with no gameplay logic.

### What exists

```
backend/
  app/
    __init__.py              # empty package marker
    domain/__init__.py       # empty — pure domain boundary
    engine/__init__.py       # empty — pure engine boundary
  tests/
    test_sanity.py           # import-only harness test (no placeholder API)
    test_engine_purity.py    # AST rglob import-boundary guard for engine/ + domain/
  pyproject.toml             # uv project: pytest + ruff + pyright (strict)
  uv.lock                    # 141 lines, reproducible (11 packages)
  .venv/                     # created by uv sync --project backend
Makefile                     # test / lint / type / format / format-check wrappers
.gitignore                   # Python + uv + Vite + OS/IDE
.python-version              # 3.12 (root only)
AGENTS.md / backend/AGENTS.md / frontend/AGENTS.md
DECISIONS.md (001-008)
BUILD_SPEC.md Status: Section 1 COMPLETE
docs/plans/2026-08-09-section-1-walking-skeleton.md
frontend/                    # placeholder for Section 11 (Vite+React)
docs/
```

### Boundaries

- `backend/app/engine` and `backend/app/domain` are pure: no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk` imports. Enforced by AST rglob test that will catch future `engine/randomness.py` etc.
- `backend/pyproject.toml` is the single Python project. No `fastapi` until Section 10; do not add `pydantic` early unless an approved Section plan demonstrates a concrete need.
- Ruff/pyright scoped to `backend` only — `AGENTS.md` / plans not formatted.

### Normal verification

```bash
# requires clean uv cache (see note below)
uv sync --project backend
make test              # = uv run --project backend pytest -v
make lint              # = ruff check backend
make type              # = pyright
make format-check      # = ruff format --check backend
make format            # actually formats backend/
```

### Last known green (with UV_CACHE_DIR workaround)

```
uv sync --project backend  → Resolved 11 packages, 0 errors
pytest -v                  → 3 passed (1 sanity + 2 purity)
ruff check backend         → All checks passed
ruff format --check backend→ 7 files already formatted
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

### Intentionally missing (do not build early)

Real economy logic, `Money`/`Quantity` types, deterministic RNG, `GameState`, markets, rivals, trade routes, FastAPI routes, DB/SQLAlchemy, React UI, content framework, LLMs.

### Next milestone

**Section 2 — Core Economic Types and Deterministic Randomness** — define minimal `GameState`/`PlayerState`/`MarketState`/`OperationState`/`InventoryState`/`TurnContext` + deterministic RNG via stable hash (BLAKE2/SHA-256 over `run_seed|ruleset_version|turn|namespace|entity_id|ordinal`), integer `Money`/`Quantity`/`BasisPoints`/`PriceMilliunits` with tested rounding.
