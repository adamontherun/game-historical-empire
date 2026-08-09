# Section 2 — Core Economic Types and Deterministic Randomness — Plan

**Date:** 2026-08-09
**Branch:** `section/2-core-types` (from `origin/main` at `d14d957`)
**Spec Authority:** `BUILD_SPEC.md` Section 2 (Status: NOT STARTED) + global §§11-13 + `DECISIONS.md` 001-009 + user answers 2026-08-09

---

## Goal

Create the minimum canonical types and deterministic RNG interface needed to implement the one-turn grain market in Section 3, with integer-only canonical state, stable substream derivation, and explicit rounding helpers. Stop when Section 3 can be built on top without rework.

## Success Criteria

- `GameState`, `PlayerState`, `MarketState`, `OperationState`, `InventoryState`, `TurnContext` exist in `backend/app/domain` (or `engine`) and cover the 10 required concepts: `cash`, `grain inventory`, `farm capacity`, `storage capacity`, `regional supply`, `regional demand`, `grain price`, `current turn`, `run_seed`, `ruleset_version`.
- Canonical economic values are `int`-only at runtime (`Money`, `Quantity`, `BasisPoints`, `PriceMilliunits` aliases) and invalid negatives are rejected where appropriate (AC #1, #2).
- Deterministic substream derivation via stable hash (`BLAKE2b` over `run_seed|ruleset_version|turn|namespace|entity_id|ordinal`) returns identical `random.Random` streams for identical key material and distinct streams for different namespaces (AC #3, #4). No `random` global, no `hash()` (AC #5).
- Explicit integer rounding helpers exist for any % arithmetic (e.g. `apply_basis_points`, `div_round`) with deterministic, tested behavior.
- Tests cover rounding and deterministic seed derivation (AC #6).
- `make test && make lint && make type && make format-check` pass on clean checkout. Engine/Domain purity guard still passes (no `fastapi`/`sqlalchemy`/`httpx` imports).

## Context And Current Facts

- Repo at `d14d957` (`main` merged `section/1-walking-skeleton`). `BUILD_SPEC.md:671` Section 2 is `NOT STARTED`; `STATE.md` marks Section 1 COMPLETE and describes Section 2 as next milestone.
- Current `backend/app/domain/__init__.py` and `backend/app/engine/__init__.py` are empty markers. `backend/tests/test_engine_purity.py` enforces purity via AST `rglob` — will fail if new modules import `fastapi`/`sqlalchemy`/`httpx`/`asyncpg`/`openai`/`clerk`. `test_sanity.py` is import-only harness (3 tests total). `backend/pyproject.toml` has `dependencies=[]`, dev deps `pytest>=9`, `ruff>=0.8`, `pyright>=1.1 strict`, `python >=3.12`, `line-length 100`. No `pydantic` yet.
- `DECISIONS.md` 006 says in-memory sessions until Section 16, so no DB work in Section 2. 002 mandates Beta Acid layering future, but `domain`/`engine` stay sync and pure. 004 says heavy unit on `engine`/`domain`, some integration, limited Playwright — coverage tracked not gating.
- User 2026-08-09: (1) use `pydantic` now, (2-5) use judgement within spec. So we may add `pydantic>=2` to `backend/pyproject.toml` now (Section 10 would anyway need it, but Section 2 can justify it for validated integer types).
- Required numeric invariants: §12 `10_000 bps = 100%`, `Money=int`, etc. Determinism §11 lists key material `run_seed|ruleset_version|turn|system_namespace|entity_id|ordinal`.
- Section 3 preview needs: `supply`, `demand`, `base_price`, `current_price`, `responsiveness`, `max per-turn movement`, `world condition normal|drought`, commands `expand_farm|build_granary|buy_grain|hold` — so Section 2 types must be forward-compatible without implementing that logic.

## Constraints And Non-goals

**Must satisfy:**
- Pure `backend/app/engine` + `backend/app/domain` — no FastAPI/React/SQLAlchemy/Clerk/LLM imports.
- Integer-only canonical state; quantized transient `Decimal` must be explicit; rounding deterministic and tested.
- Determinism via stable hash, not `random` global or `hash()`.

**Explicitly out of scope (BUILD_SPEC §2):**
- All 8 age schemas, generic business schema registry, JSON content loader, rivals (`Mira`/`Daran`), routes, API (`POST /api/v1/games`), persistence, domain event persistence, market formula, drought price mutation, buying validation beyond type-level negatives.
- Do not scaffold `frontend` or `render.yaml` changes. Do not add `sqlalchemy`/`fastapi`/`httpx` deps.
- Keep abstractions minimal — no universal mechanism before 2 concrete uses (§15). Two markets/route are Section 5, not now.

## Key Decisions

1. **Pydantic for domain types (user-approved).** Chose `pydantic.BaseModel` + `Annotated[int, Field(ge=0)]` over `dataclass` because user explicitly said "pydantic now" and it gives `pyright` strict typing + runtime `ValidationError` for AC #2 with less boilerplate. Alternative `dataclass + __post_init__` rejected: would need manual validators and still not provide JSON schema for free later. Risk: adds `pydantic` dep early — acceptable; Section 10 needs it anyway and purity guard allows `pydantic` (not in deny-list; only FastAPI/DB/LLM denied). Will pin `pydantic>=2.7` in `backend/pyproject.toml` and add `pydantic-core`.
2. **File layout: `backend/app/domain/` holds types, `backend/app/engine/` holds RNG + rounding.**
   - `backend/app/domain/types.py` — aliases + `GameState`/`PlayerState`/`MarketState`/`OperationState`/`InventoryState`/`TurnContext`.
   - `backend/app/engine/rng.py` — pure sync deterministic derivation (`derive_seed`, `make_rng`, `rng_for`).
   - `backend/app/engine/rounding.py` — `apply_basis_points`, `div_round_*` helpers.
   Alternative single-file `domain/models.py` rejected: `rng` and `rounding` are engine utilities with different test concerns; split keeps imports clean and satisfies "plain functions over classes" + purity.
   All three import only `pydantic`/`hashlib`/`random`/`typing`.
3. **Integer type strategy: aliases + constrained validation.**
   - `Money = Annotated[int, Field(ge=0, strict=True)]` etc. `BasisPoints` allowed `0..100_000?` but spec only requires `ge=0` where invalid — so `Money`/`Quantity`/`PriceMilliunits` enforce `ge=0`, `BasisPoints` allow any `int` but helpers will validate `0..10_000` where used. Rejected `NewType` alone (no runtime check, fails AC #2).
4. **Aggregate shape (judgement):**
   - `InventoryState{grain: Quantity}` — single good grain for Sec 2-4.
   - `OperationState{id: str, kind: Literal["farm","granary"], capacity: Quantity, level: int =1}` — minimal to represent farm capacity vs storage capacity without generic registry.
   - `PlayerState{cash: Money, inventory: InventoryState, operations: list[OperationState], farm_capacity: Quantity, storage_capacity: Quantity}` — `farm_capacity`/`storage_capacity` kept as explicit ints for Sec 2-3 market logic; `operations` list retained for Sec 5 extensibility but optional.
   - `MarketState{supply: Quantity, demand: Quantity, base_price: PriceMilliunits, current_price: PriceMilliunits}` — only fields Sec 2 requires; `responsiveness`/`max_movement` deferred to Sec 3 (not stubbed).
   - `GameState{turn: int, run_seed: str, ruleset_version: str, player: PlayerState, market: MarketState}` + `TurnContext{turn: int, run_seed: str, ruleset_version: str}` as lightweight derived view for RNG calls (avoids passing full GameState into `rng_for`). `run_seed` as `str` (opaque) + `ruleset_version` as `str` to match determinism key material.
   Alternative flat `GameState` rejected: nesting matches Sec 3-4 `resolve_turn(state, command, world_context, rng_context)` shape and keeps `domain` testable.
5. **RNG API: pure functions, BLAKE2b, `random.Random` substreams.**
   - `def derive_seed(run_seed: str, ruleset_version: str, turn: int, namespace: str, entity_id: str, ordinal: int) -> int` — canonical serialization `f"{run_seed}|{ruleset_version}|{turn}|{namespace}|{entity_id}|{ordinal}"` encoded `utf-8`, `hashlib.blake2b(digest_size=8).hexdigest()` -> `int(...,16)` masked to `2**63-1` for `Random` seed stability across Python versions. Deterministic, no `hash()`.
   - `def make_rng(seed: int) -> random.Random` and `def rng_for(turn_ctx: TurnContext, namespace: str, entity_id: str, ordinal: int =0) -> random.Random` convenience. Different namespaces produce different `seed` (AC #4) because namespace in key material. No global `random` usage (enforced by rgrep in tests).
   - Chose BLAKE2b over SHA-256: faster, stable, stdlib, `digest_size=8` gives 64-bit seed sufficient for `Random`; SHA-256 alternative would work but 256-bit int larger than needed. Both meet spec ("BLAKE2 or SHA-256").
6. **Rounding helpers (judgement for Sec 3 forward):**
   - `def mul_basis_points(value: int, bps: int) -> int` = `value * bps // 10_000` with explicit floor (deterministic, no float). Provide `apply_basis_points` alias. Add `div_round_half_up(n: int, d: int) -> int` for responsive price math later. Keep helpers sync, pure, `pyright` strict. Rejected no-helpers: AC #6 requires rounding tests, so add at least one.
7. **Testing location:** Keep `backend/tests/test_*` flat for Sec 2 (existing convention), add `test_determinism.py`, `test_rounding.py`, `test_core_types.py`. Do not yet create `tests/unit_tests/` subdir (would churn Sec 1's `testpaths = ["tests"]`); defer directory restructure to Sec 3 if needed. All tests via `uv run --project backend pytest -v`.

## Recommended Approach

Add `pydantic` dep, define integer-constrained types with `ge=0` validation, define 6 domain models with only Sec 2-4 fields, implement BLAKE2b deterministic derivation returning `random.Random`, add rounding helpers, write focused unit tests for negative rejection, stable seeds, namespace divergence, and rounding. Keep all new code import-pure.

## Work Plan

1. **Branch + config** — verify `section/2-core-types` at `d14d957`, update `backend/pyproject.toml` to add `pydantic>=2.7` to `dependencies`, run `uv sync --project backend` (expect `uv.lock` update, ~8 new packages). No code yet. Validate `make lint`/`make type` still pass with no usages.
   - Files: `backend/pyproject.toml`, `backend/uv.lock`
   - Depends: none
2. **Canonical numerics + rounding** — create `backend/app/engine/rounding.py` with `Money` re-export? Actually aliases live in `domain/types.py`; `rounding.py` holds pure functions `mul_basis_points`, `apply_basis_points`, `div_round_half_up`, `clamp_non_negative`. Strict types, Google-style docstrings only on public APIs per AGENTS §8.
   - Files: `backend/app/engine/rounding.py`
   - Depends: #1 for `pyright` types (but no pydantic import needed here)
3. **Deterministic RNG** — create `backend/app/engine/rng.py` with `derive_seed`, `make_rng`, `rng_for` (takes `TurnContext` or raw keys). Uses only `hashlib`, `random`, `typing`. No global random. Docstring explains canonical serialization.
   - Files: `backend/app/engine/rng.py`, `backend/app/domain/types.py` must define `TurnContext` first *or* make `rng.py` take raw `str/int` args to avoid circular import — choose raw args for #3, then add `rng_for` overload after #4. Split into two commits: `derive_seed` pure, then convenience wrapper.
   - Depends: #2 (ordering not strict, but #4 defines `TurnContext`)
4. **Domain types** — create `backend/app/domain/types.py` (or `models.py`? choose `types.py` to match spec language) defining `Money`, `Quantity`, `BasisPoints`, `PriceMilliunits` as `Annotated`, plus 6 models with `ge=0` where appropriate, `ConfigDict(frozen=True)` for determinism, explicit `field_validator` for negatives. Include `GameState`, `PlayerState`, `MarketState`, `OperationState`, `InventoryState`, `TurnContext`. Ensure `from __future__ import annotations`, `pyright` strict.
   - Files: `backend/app/domain/types.py`, update `backend/app/domain/__init__.py` to re-export.
   - Depends: #1
5. **Tests** — add `backend/tests/test_core_types.py` (negative rejection), `backend/tests/test_rounding.py` (mul/bps/div cases), `backend/tests/test_determinism.py` (stable seed same material -> same ints, different namespace -> different, ordinal changes, `random.Random` determinism, grep no `random.` global). Ensure `test_engine_purity.py` still passes (new files import only allowed libs).
   - Files: `backend/tests/test_*.py`
   - Depends: #2-4
6. **Docs + gates** — update `STATE.md` next-milestone note? *Do not* mark Section 2 COMPLETE until gates pass — only `Status` line update after all AC pass per §0.4. Run full gates: `uv sync --project backend`, `make test`, `make lint`, `make type`, `make format-check`. Fix any `ruff`/`pyright` issues. Update `docs/plans/` already done.
   - Files: `STATE.md` (only if needed for handoff, not Status yet)
   - Depends: #5

Order is linear 1->4->2/3 can parallel, then 5->6. If prefer 2 commits, split #4 into types then RNG wrapper.

## Validation Plan

- **Gate 1 — install:** `uv sync --project backend` -> Resolved N packages, 0 errors. Evidence: command output.
- **Gate 2 — unit:** `uv run --project backend pytest -v` (or `make test`) -> expect existing 3 + new ~15-20 tests, all passed. Must show AC #1-6 covered: negative validation raises `ValidationError`, `derive_seed("s1","v1",1,"ns","e1",0) == derive_seed(...)` stable, `ns_a != ns_b` seeds differ, no `random.*` global in `backend/app/engine/rng.py` (grep), rounding `mul_basis_points(1000, 5000)==500` etc.
- **Gate 3 — lint:** `make lint` -> `ruff check backend` All checks passed.
- **Gate 4 — type:** `make type` -> `pyright` 0 errors, 0 warnings (test for strict).
- **Gate 5 — format:** `make format-check` -> `ruff format --check backend` 7+ files already formatted; else `make format`.
- **Gate 6 — purity:** `pytest backend/tests/test_engine_purity.py -v` -> 2 passed (no forbidden imports).
- **Manual:** `rg -n "import random|from random|random\.(random|randint|choice|shuffle)" backend/app/engine --no-ignore` should only show `import random` + `random.Random` construction in `rng.py`, not global calls. `rg -n "hash\(\)" backend/app` -> 0.

Highest-risk validation: `pyright` strict with `Annotated` + `BaseModel` `ge=0` — may require `Field(strict=True)` tuning to satisfy AC #2 without false negatives for `BasisPoints`.

## Risks / Rollback

- **Risk:** Adding `pydantic` early could mask Section 1's zero-dep purity intent or bloat `uv.lock`. Mitigation: only `pydantic` + `pydantic-core` + `annotated-types`; no `fastapi` yet. Rollback: `git checkout main -- backend/pyproject.toml backend/uv.lock` and revert to `dataclass`.
- **Risk:** Over-modeling `GameState` (too many fields) violates "only fields needed by Sec 2-4" and creates rework for Sec 3 market formula. Mitigation: keep minimal per Work Plan #4, leave `responsiveness` for Sec 3.
- **Risk:** Hash serialization instability (e.g. `int` vs `str` for `run_seed`) would break AC #3 determinism across future runs. Mitigation: fix canonical `f"{run_seed}|{ruleset_version}|{turn}|{namespace}|{entity_id}|{ordinal}"` and test with golden values in `test_determinism.py`.
- **Risk:** `ruff`/`pyright` strict failures on new files. Mitigation: run gates locally before commit; keep `from __future__ import annotations` and explicit return types.
- **Rollback:** `git reset --hard origin/main` + `git branch -D section/2-core-types` if plan rejected; no DB/remote state to clean.

## Open Questions

None after user answers — all 5 answered: pydantic now, judgement for others, follow spec. Remaining minor choices (file names `types.py` vs `models.py`, `blake2b` digest size) are judgement calls documented above and do not need user input. If user prefers `sha256` over `blake2b`, can swap in implementation without spec change.

## Grill Outcome (2026-08-09)

Pressure-tested via `/grill` (5 decision-forcing questions):

1. **Rounding scope** — Keep minimal helpers now (`apply_basis_points` + `div_round_half_up`) — *approved*. Not scope creep; meets AC#6 and prevents Sec 3 retrofit.
2. **File layout** — 3 files `domain/types.py` + `engine/rng.py` + `engine/rounding.py` — *approved*. Preserves purity isolation.
3. **OperationState stub** — Keep `PlayerState` with explicit `farm_capacity`/`storage_capacity` + optional `operations: list[OperationState]` — *approved*. Not premature abstraction; supports Sec 2-4 without generic registry.
4. **RNG serialization** — Lock canonical `f"{run_seed}|{ruleset_version}|{turn}|{namespace}|{entity_id}|{ordinal}"` + `blake2b(digest_size=8)` -> `int` and add 2 golden seed values in tests — *approved*. Guarantees AC#3 stability.
5. **Purity vs Pydantic** — Allow `pydantic`/`annotated_types` in `domain`/`engine`; purity guard should permit it (only `fastapi`/`sqlalchemy`/`httpx`/`asyncpg`/`openai`/`clerk` remain blocked) — *approved*.

No plan changes required; draft already reflected these. Proceed to final approval.

---

**Next:** Awaiting final approval via `request_user_input`, then `/goal` implementation on `section/2-core-types`.
