# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 3 — COMPLETE (2026-08-09)

**One-turn grain market kernel:** `resolve_turn` with explicit order `command → production → supply → price → settlement`, integer-safe price via basis points, drought reduces yield not price, causal trace with parent chain, bounded buy, CLI demo.

### What exists

```
backend/
  app/
    __init__.py              # empty package marker
    domain/
      __init__.py            # re-exports canonical types + trace
      types.py               # Money/... + GameState/PlayerState/MarketState(responsiveness,max_movement)+WorldCondition+PlayerCommand (frozen, ge=0)
      trace.py               # CausalNode/CausalTrace/DomainEffect/PlayerOutcome/TurnResolution (frozen)
    engine/
      __init__.py            # re-exports RNG + rounding + resolve_turn/TURN_ORDER
      rng.py                 # derive_seed/make_rng/rng_for — JSON canonical -> blake2b
      rounding.py            # mul_basis_points/apply_basis_points/div_round_half_up/clamp_non_negative
      turn.py                # resolve_turn + _target_price/_bounded_price — drought→farm_output→supply→price_pressure→price, buy clamped, TURN_ORDER explicit, RNG consumed
      demo.py                # CLI demo: before/command/world/chain/after + contrast
  tests/
    test_sanity.py
    test_engine_purity.py
    test_core_types.py
    test_determinism.py
    test_rounding.py
    test_turn_kernel.py      # AC #1,3,4,5,6: determinism + drought chain + negatives + buy cash/storage + trace + capacities + bounded + drivers
    test_invariants.py       # AC #2 + invariants: monotonic target/bounded price, no negatives, positive price
  pyproject.toml             # uv project: pytest + ruff + pyright (strict) + pydantic>=2.7
  uv.lock                    # 15 packages
  .venv/
Makefile
.gitignore
.python-version              # 3.12 (root only)
AGENTS.md / backend/AGENTS.md / frontend/AGENTS.md
DECISIONS.md (001-009)
BUILD_SPEC.md Status: Section 3 COMPLETE
docs/plans/
  2026-08-09-section-1-walking-skeleton.md
  2026-08-09-section-2-core-types.md
  2026-08-09-section-3-grain-market-kernel.md
frontend/                    # placeholder for Section 11
docs/
```

### Boundaries

- `backend/app/engine` and `backend/app/domain` are pure: no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk` imports. Enforced by AST rglob test. `pydantic` is now allowed in domain/engine for validated canonical types (Section 2). New `engine/turn.py` imports only `domain` + `rng`/`rounding`.
- Canonical state is frozen and has single source of truth for capacities: `PlayerState{cash, inventory, farm_capacity, storage_capacity}` — no `operations: list` embedding. `OperationState` exists as standalone type for Section 5+.
- Deterministic RNG: `derive_seed` uses JSON array canonical encoding so delimiter-containing strings cannot collide; global `random.*` and built-in `hash()` are banned via AST scan of all `engine/**/*.py`, not just `rng.py`. `resolve_turn` consumes `rng_for` substream (proves seed used) but core price is deterministic to preserve monotonicity.
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
pytest -v                  → 48 passed (7 core + 7 rounding + 11 determinism + 2 purity/sanity + 14 kernel + 7 invariants)
ruff check backend         → All checks passed
ruff format --check backend→ 18 files already formatted
pyright                    → 0 errors, 0 warnings
demo                       → uv run --project backend python backend/app/engine/demo.py --world drought --command hold  prints before/command/world/chain/after
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

Causal explanation (Section 4 — formalize DomainEffect/CausalNode/OutcomeDriver), two markets + river route (Section 5), headless prototype (Section 6), rivals (Section 7), etc. No FastAPI routes, DB/SQLAlchemy, React UI, content framework, LLMs.

### Follow-up obligations (from Section 3 review)

Must resolve before **Section 4**:
- Replace raw absolute-delta driver ranking with unit-aware, meaningful ranking (Section 4 owns `OutcomeDriver`).
- Formalize / harden causal trace (deeper validation of graph shape).
- Resolve RNG context ownership — derive `TurnContext` internally from `GameState` or validate `rng_context` equals `state`'s turn/seed/version; do not rely on caller to keep them in sync. Do not add jitter just because a stream exists; deterministic economics preferred.

Must resolve before **Section 6** (multi-turn prototype):
- Define `market.supply` semantics: stock on hand vs per-turn flow vs aggregate supply signal. Current `next_supply = supply + farm_output` is a persistent stock while `farm_output` also enters player `inventory` and `buy_grain` does not reduce regional supply — coherent for one turn but will monotonically accumulate over repeated turns. Design stock/flow accounting before the headless balance harness (tuning 5000/2000 is fine to defer to that harness).

Supply / RNG notes do not block a deliberately one-turn Section 3, but are hard gates before Section 6.

### Next milestone

**Section 4 — Causal Explanation and Outcome Model** — formalize `DomainEffect/CausalNode/CausalTrace/PlayerOutcome/OutcomeDriver` with ≤3 drivers derived from trace, full debug trace, CLI showing concise + debug.

