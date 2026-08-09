# STATE — Historical Empire

> Handoff snapshot for Muse / human. Concise and current, not a history log.

## Section 4 — COMPLETE (2026-08-09)

**Causal explanation and outcome model:** exact wealth decomposition (`cash_effect + quantity_value_effect + price_value_effect == wealth_delta`), immutable causal DAG with tuples, story drivers as exact wealth-bps ranked paths (not single nodes), filtered zero-impact stories, valuation subgraph `inventory/price → quantity/price revaluation → wealth`, RNG ownership validated, CLI concise/verbose.

### What exists

```
backend/
  app/
    __init__.py
    domain/
      __init__.py            # re-exports CausalEdge/OutcomeDriver + types
      types.py               # Money/... + GameState/PlayerState/MarketState+WorldCondition+PlayerCommand (frozen, ge=0)
      trace.py               # CausalNode(parent_ids:tuple)/CausalTrace(nodes:tuple, edges)/DomainEffect/OutcomeDriver/PlayerOutcome(drivers:tuple, top_drivers computed)/TurnResolution (frozen, validators: unique ids, parents before children, allowed roots world/command, farm_capacity only when delta==0, delta==after-before)
    engine/
      __init__.py            # re-exports RNG + rounding + resolve_turn/TURN_ORDER
      rng.py                 # derive_seed/make_rng/rng_for — JSON canonical -> blake2b
      rounding.py            # mul_basis_points/apply_basis_points/div_round_half_up/clamp_non_negative
      turn.py                # resolve_turn — command->production->supply->price->settlement->valuation, drought→farm_output→supply→price, exact valuation (_value), wealth nodes (quantity/price/cash/wealth), story drivers (command_cost, quantity_value, price_revaluation) filtered & ranked by exact wealth-bps, RNG validated
      demo.py                # CLI demo: before/command/world/WHY? (3 story drivers with impact_money/impact_bps/causal_node_ids) + after + contrast; --verbose adds FULL CAUSAL TRACE + DOMAIN EFFECTS + EDGES
  tests/
    test_sanity.py
    test_engine_purity.py
    test_core_types.py
    test_determinism.py
    test_rounding.py
    test_turn_kernel.py      # AC #1,3,4,5,6 + blocker 2 + TURN_ORDER->valuation + tuple parents
    test_invariants.py       # monotonic price, no negatives, positive price
    test_causal_trace.py     # exact wealth decomposition, immutable tuples, DAG allowed roots, wealth graph parents, driver determinism & wealth-bps, story paths filtered, RNG mismatch, storage-capped
    test_explanation.py      # drought→wealth structural chain exact, story drivers cover chain, concise≤3 & full trace, normal vs drought
  pyproject.toml             # uv project: pytest + ruff + pyright (strict) + pydantic>=2.7
  uv.lock
  .venv/
Makefile
.gitignore
.python-version              # 3.12 (root only)
AGENTS.md / backend/AGENTS.md / frontend/AGENTS.md
DECISIONS.md (001-009)
BUILD_SPEC.md Status: Sections 1-4 COMPLETE
docs/plans/
  2026-08-09-section-1-walking-skeleton.md
  2026-08-09-section-2-core-types.md
  2026-08-09-section-3-grain-market-kernel.md
  2026-08-09-section-4-causal-explanation.md  # exact valuation, tuples, story drivers
frontend/                    # placeholder for Section 11
docs/
```

### Boundaries

- `backend/app/engine` and `backend/app/domain` are pure: no `fastapi`, `sqlalchemy`, `httpx`, `asyncpg`, `openai`, `clerk`. Enforced by AST rglob test. `pydantic` allowed for validated canonical types. `engine/turn.py` imports only `domain` + `rng`/`rounding`.
- Canonical state is frozen with immutable tuples: `parent_ids: tuple[str,...]`, `nodes: tuple[CausalNode,...]`, `drivers: tuple[OutcomeDriver,...]`, `causal_node_ids: tuple[str,...]` — no mutable lists inside frozen models, DAG is authoritative.
- Wealth is structural, not post-hoc math: `value(qty,price)=qty*price//1000`, `wealth_before=cash_before+value(before)`, `quantity_value_effect=value(after,price_before)-value(before,price_before)`, `price_value_effect=value(after,price_after)-value(after,price_before)`, `cash_effect=cash_after-cash_before`, `wealth_delta=sum` exactly, with nodes `quantity_value_effect` parents `(inventory,price)`, `price_value_effect` parents `(inventory,price)`, `wealth` parents `(cash_effect,quantity_value_effect,price_value_effect)`.
- Story drivers are exact partitions: candidates `command_cost`/`quantity_value`/`price_revaluation` (plus storage/farm paths folded into quantity) filtered where `impact_money==0`, ranked by `impact_bps=abs(impact_money)*10000//max(wealth_before,1)` desc then `id` asc, `≤3` returned. No double-count, no counterfactual drought-vs-normal, sum of all drivers ≤ wealth_delta and sum of 3 exact effects == wealth_delta.
- Validator: unique ids, parents before children, no cycles, allowed roots `world`/`command` regardless of delta, `farm_capacity`/`storage_capacity` empty only when `delta==0`, all valuation nodes require parents, `delta==after-before` enforced, `edges` derived.
- Deterministic RNG: `rng_context` validated `== state.to_turn_context()` else `ValueError`; `derive_seed` via JSON array + blake2b, no global random/hash, price remains deterministic.
- `backend/pyproject.toml` single project, no `fastapi`/`sqlalchemy` until Section 10. Ruff/pyright scoped to `backend`.

### Normal verification

```bash
uv sync --project backend
make test              # = uv run --project backend pytest -v  (65 passed)
make lint              # = ruff check backend  (All checks passed)
make type              # = pyright  (0 errors)
make format-check      # = ruff format --check backend  (20 already formatted)
make format            # actually formats backend/
```

### Last known green

```
uv sync --project backend  → Resolved 15 packages, 0 errors
pytest -v                  → 65 passed (8 core + 7 rounding + 11 determinism + 2 purity/sanity + 15 kernel + 7 invariants + 11 causal_trace + 4 explanation)
ruff check backend         → All checks passed
ruff format --check backend→ 20 files already formatted
pyright                    → 0 errors, 0 warnings
demo                       → uv run --project backend python backend/app/engine/demo.py --world drought --command hold  prints BEFORE/COMMAND/WORLD/PLAYER OUTCOME/WHY? (2 story drivers, sum==wealth_delta)/AFTER
demo verbose               → same --verbose adds FULL CAUSAL TRACE (world→farm_output→supply→price→quantity/price revaluation→wealth) + DOMAIN EFFECTS + EDGES
```

Cache provenance fixed in YOLO (`~/.cache/uv/sdists-v9/.git` removed, `uv cache prune`), no `UV_CACHE_DIR` workaround needed. `.git/refs` provenance cleared for branch creation; `.git/objects` provenance remains but does not block Git (refs are authoritative).

### Decisions relevant to future work

- `uv` + Python 3.12, `ruff` (line-length 100, py312) + `pyright` strict
- Beta Acid layout deferred to Section 10; engine stays import-clean
- High autonomy within Section; `/plan` before Section, approve once; stop at gate and report
- Coverage tracked not gating until Sections 3-4; heavy unit on engine/domain
- `backend/pyproject.toml` location; root `Makefile` wrappers; `backend/uv.lock` tracked
- Section 2: `pydantic` for validated integer types; JSON canonical encoding for RNG; capacities single-source
- Section 3: `TURN_ORDER` explicit, drought reduces yield not price, buy clamped, integer price via basis points
- Section 4: exact wealth decomposition at old vs new price, immutable tuples for causal DAG, allowed roots world/command, story drivers as causal paths ranked by exact wealth-bps, filtered zero stories, RNG ownership validated, concise/verbose CLI

### Intentionally missing (do not build early)

Two markets + river route (Section 5), headless 5-turn prototype (Section 6), rivals Mira/Daran (Section 7), pressure arc (Section 8), balance harness (Section 9), etc. No FastAPI routes, DB/SQLAlchemy, React UI, content framework, LLMs.

### Follow-up obligations

Must resolve before **Section 6** (multi-turn prototype):
- Define `market.supply` semantics: stock vs per-turn flow vs aggregate signal. Current `next_supply = supply + farm_output` is persistent stock while `farm_output` also enters player `inventory` and `buy_grain` does not reduce regional supply — coherent for one turn but will monotonically accumulate over repeated turns. Design stock/flow accounting before headless balance harness (tuning 5000/2000 is fine to defer to that harness).

Section 4 follow-ups are now resolved: exact wealth decomposition, immutable tuples, story drivers exact wealth-bps, RNG validation.

### Next milestone

**Section 5 — Two Markets and One Trade Route** — Home Valley + River Town + River Route with transport cost/capacity/reliability, trade access, two prices, arbitrage via transport, deterministic.
