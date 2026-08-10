# Section 9 — Headless Strategy and Balance Harness — Plan

**Date:** 2026-08-10
**Branch:** `section/9-balance-harness` (from `origin/main` at Section 8 merge)
**Spec Authority:** `BUILD_SPEC.md` Section 9 (Status: NOT STARTED) + global §§10–16 + `DECISIONS.md` 001–012 + `STATE.md` §8
**Related:** `backend/app/domain/pressure.py`, `backend/app/domain/types.py`, `backend/app/engine/pressure.py`, `backend/app/engine/prototype.py`, `backend/app/engine/turn.py`, `backend/app/engine/actor.py`, `backend/app/engine/rivals.py`, `backend/app/engine/rng.py`, `backend/app/cli.py`, `backend/app/engine/__init__.py`

---

## Goal

Prove the five-turn Agricultural prototype has no obviously broken economy before building the browser UI. Add a **headless balance harness** that runs hundreds of deterministic five-turn games across scripted policies and many seeds, aggregates wealth / cash / inventory / price / swing metrics, and emits CI-comparable output. Correct the Section 8 shortcut temptation: headless callers use `PRESSURE_NORMAL` / `PRESSURE_DROUGHT` / `pressure_for_world` / `PRESSURE_ARC` — never a bare `"normal"/"drought"` string overload on `resolve_turn`.

## Success Criteria (maps to Section 9 AC + global rules)

1. **AC1 — Hundreds of games quickly.** One command runs ≥200 five-turn games (5 policies × 40 seeds) in < 5s wall clock on CI (no DB/network). `backend/app/cli.py` is the CLI entry point — invocation is `uv run --project backend python backend/app/cli.py --balance ...` (see Validation Plan for exact flags).
2. **AC2 — No universally dominant strategy.** Across the representative seed batch, the highest win-rate among the five policies is < 0.80 and no policy has median final wealth > 1.6× the next-best median. "Win" per seed = highest `final_wealth` (cash + inventory×home_price/1000) among the five policies on that seed. Thresholds are generous and survive ±20% cost/price tweaks — they catch a truly broken runaway (e.g. buy_grain free) not a mild tuning edge. See Key Decision 6 for confound control.
3. **AC3 — No routine impossible negative state.** Across the full batch, zero occurrences of `cash < 0`, `grain < 0`, `storage < 0`, `price ≤ 0`, or `supply < 0`, and no `insufficient_*` that indicates a policy construction bug (harness policies are affordability-aware). Caught by exhaustive per-turn invariant checks, not by absence of exceptions.
4. **AC4 — Price ranges stay within deliberate bounds.** Every observed `Home` price ∈ `[2000, 9000]` and `River` price ∈ `[2000, 10000]` (milliunits), and no single-turn price jump exceeds `max_movement_bps` (2000 = 20%) unless the target price justifies it — proven by `_bounded_price` property. Bounds are 2–2.5× base (5000/5200) and well inside `int` positivity; a `price *= 1.4` direct drought mutation would violate.
5. **AC5 — Same batch configuration reproduces identical aggregate results.** Re-running the same `(seeds, policies, ruleset_version)` batch yields byte-identical JSON output and identical per-policy aggregates (mean/median/win-rate) — proven by double-run equality test that hashes the output, not by re-running the harness with the same RNG it produced. No global `random`, no `hash()`, integers only; seed substreams via `rng_for(run_seed, version, turn, namespace, entity, ordinal)` with BLAKE2.
6. **AC6 — Output easy to compare in CI/local.** The balance command prints a human-readable markdown table to stdout and an optional `--json-out` file with stable keys and sorted policies. Exit code 0 on all invariants/price/dominance passing, non-zero with a one-line reason on failure — suitable for `make test` and CI diff.
7. **Housekeeping.** `engine` + `domain` remain pure (no `fastapi`/`sqlalchemy`/`httpx` imports); `resolve_turn(state, command, pressure: PressureState, rng_context)` signature unchanged from Section 8; no bare-string shim added; no Section 10/11/15 material (no FastAPI, no React, no content loader/JSON DSL, no DB).

---

## Context And Current Facts (verified against code)

- **Spec §9:** Five scripted policies (production-heavy, storage-heavy, trade-heavy, cash-preserving, random legal), many deterministic seeds, metrics (final wealth, cash lows, inventory, drought exposure, win rate, median, bankrupt/near-bankrupt, price ranges, largest single-turn swing), targets (no dominant, no dead, preparation mitigates bad luck, legible ranges). AC1–6 as above.
- **Pressure (Section 8):** `backend/app/domain/pressure.py` defines `PressureStage` + frozen `PressureState{pressure_id, stage, activation_turn, world, signal, title, causal_source_id}` (7 fields, validator `stage=="drought" <=> world=="drought"` and `causal_source_id == f"pressure:{id}:{stage}"`). `backend/app/engine/pressure.py` defines `PRESSURE_ARC: tuple[PressureState,5]` (normal→early_dry→worsening_dry→drought→aftermath, truthful rainfall prose) + `PRESSURE_NORMAL`/`PRESSURE_DROUGHT`/`pressure_for_world` (bare-string replacement, G1) + `pressure_for_turn(idx)` / `next_world_known_for_turn(idx)`. `prototype.py:64-66` derives `TURN_SPECS` from `PRESSURE_ARC` (single source). `turn.py:122` is now `resolve_turn(state, command, pressure: PressureState, rng_context)` with leading `pressure_stage` node (`reason_code=pressure.causal_source_id`, parent of `world`, chain `pressure→world→farm_output→supply→price→…→wealth`).
- **Prototype:** `FiveTurnGame` (`prototype.py:189`) owns `state:GameState` + `history:5` + `rival_history:5×(Mira,Daran)` session-owned, isolated from shared `market.supply` signal; `turn_limit=5`, `turn==0` enforced; `submit` does two-phase (rivals choose pre→player resolve via `resolve_turn` with `pressure_for_turn(idx)` and `state.to_turn_context()` → rivals settle `buy@pre_home`, `ship@resolved_river`, valuation `@resolved_home`). `default_start_state` cash 1000 grain 20 farm 10 storage 200 Home 100/90/5000 River 80/130/5200 route 800/20/10000. `StrategicSummary` and `current_pressure` (`None` when complete) expose inspectability.
- **Actor:** `actor.py` single source for `YIELD_PER_CAPACITY=10`, `DROUGHT_YIELD_REDUCTION_BPS=4000`, `EXPAND_FARM_COST=500`, `BUILD_GRANARY_COST=300`, `ROUTE_ESTABLISH_COST=400`, `compute_farm_output`, `resolve_buy` (affordability+storage clamp), `resolve_shipment`, etc. `turn.py` keeps `_target_price/_bounded_price` and trace.
- **Numerics & RNG:** Canonical `Money/Quantity/PriceMilliunits ge=0`, `BasisPoints` int, `rounding.py` helpers, `rng.py` `derive_seed/make_rng/rng_for` via JSON-canonical + blake2b, no global random, no `hash()`. Existing determinism tests at `test_determinism.py`, `test_five_turn_prototype.py:76-89`.
- **CLI:** `backend/app/cli.py` is the CLI (not `engine/cli.py`). Invocation `uv run --project backend python backend/app/cli.py --choices "hold,..." --seed X --version 1.0`. Already displays per-turn `World/Pressure stage`, `Home/River price`, `WHY? drivers`, rival headlines. This is the real harness CLI path — AC1's command extends this file, not a new binary.
- **Tests:** 122 passing (`make test` = `uv run --project backend pytest -v`). `test_pressure_arc.py` covers arc order, 7-field exact, biconditional, causal_source_id single source, mechanism-isolated warning, trace chain, `current_pressure` None when complete.

---

## Constraints And Non-goals

- **Hard constraints:** Determinism per `BUILD_SPEC.md §11` (same `state+command+pressure+rng_context+seed → same`), canonical integers per §12, pure `engine`/`domain` per §13, causal trace parent chain preserved, no global `random`/`hash()`, `resolve_turn` keeps `PressureState` arg (no bare-string convenience overload).
- **Do not build:** Section 10 FastAPI (`POST /api/v1/games` etc.), Section 11 React, Section 15 content loader/JSON DSL/`world_modifiers`, additional goods/rivals/turns, credit/spoilage/automation, LLMs for economy.
- **Do not regress:** 122 existing tests stay green; `trace.py` validator not loosened; `TURN_ORDER` unchanged.

---

## Key Decisions (all settled — no open choices)

| # | Decision | Choice | Why | Alternative Rejected |
|---|----------|--------|-----|----------------------|
| 1 | **Harness location & shape** | New `backend/app/engine/harness.py` (pure, sync) + CLI extension in `backend/app/cli.py` (`--balance` flag group). `harness.py` owns: `Policy` protocol `(state, pressure, rng_context) -> PlayerCommand`, five policy factories, `BatchConfig{seed_prefix, n_seeds, policies, version}`, `SeedResult`/`PolicyAggregate`/`BatchResult` frozen models, `run_batch(config) -> BatchResult`, `format_markdown`/`to_json`. No new package, no `backend/app/balance/` directory. | Keeps engine pure and discoverable; `FiveTurnGame` stays the turn orchestrator; harness is a thin batch runner, not a second engine. | Separate `balance/` top-level package, FastAPI harness endpoint, or new binary outside `cli.py` — all add surface for no reason. |
| 2 | **No bare-string shim (Section 8 review guard)** | `harness.py` and all tests call `resolve_turn` only via `FiveTurnGame.submit` (which internally passes `PressureState`) or directly with `PRESSURE_NORMAL`/`PRESSURE_DROUGHT`/`pressure_for_world`/`pressure_for_turn`. `harness.py` **does not** accept `world: str` and does not add `if isinstance(pressure, str)` overload. Grep CI asserts `resolve_turn.*str` not present in harness. | Section 8 deliberately removed the shortcut; Section 9 is where it would be tempting for headless callers. Use the provided constants. | Convenience `world: Literal["normal","drought"]` overload, `pressure: PressureState | str` union — rejected. |
| 3 | **Policy definitions — deterministic & affordability-aware** | Five policies as pure functions (no I/O), each maps `(idx, observable_state) -> command` using only `state`+`pressure`+`rng_context` and `actor` cost helpers, validated against `PlayerCommand` frozen model. <br>• **production-heavy:** `expand_farm` while `cash >= EXPAND_FARM_COST + 200` buffer for first two turns, else `hold`; never `buy_grain`/`secure_route` (isolates farm vs market). <br>• **storage-heavy:** `build_granary` T1 if affordable, then `buy_grain:min(20, affordable, storage-inventory)` T2–T3 (pre-drought), then `hold`/`ship_grain` T5. <br>• **trade-heavy:** `secure_route` T1 if affordable, `buy_grain:10` T2, `ship_grain: min(10, inventory, capacity)` T4–T5 when `route.established`. <br>• **cash-preserving:** `hold` all 5 (minimal exposure, maximal cash). <br>• **random_legal:** uniform choice among `available_commands()` filtered by affordability (`cash >= cost` for expand/build/route, `affordable_quantity>0` for buy, `inventory>0 and route.established` for ship) using `rng_for(seed, version, turn, "harness", policy_id, 0).random()` → index. Never emits an invalid quantity. | Each policy is **legible**, **affordability-aware** (so AC3 negative-state test is meaningful, not just "policy issued impossible buy"), and **deterministically seeded** (random uses `rng_for`, others ignore RNG but remain deterministic per seed). They differ in exactly one strategic posture, enabling the confound analysis in Decision 6. | Fixed 5-length literal lists ignoring state (would emit unaffordable buys and make AC3 spurious), adaptive RL-style policies, or policies that parse `signal` prose — all rejected. |
| 4 | **Seed strategy — headless batch is deterministic even with fixed arc** | Batch enumerates `seeds = [f"{prefix}-{i:04d}" for i in range(n_seeds)]` (default `prefix="harness"`, `n_seeds=200`, `version` from `BatchConfig`). World arc is fixed (`PRESSURE_ARC`) per spec — seed variation drives only (a) `random_legal` choice via `rng_for` and (b) a **harness-only** micro-perturbation to initial `market.supply` of `±2` units derived as `perturb = (blake2(seed) % 5) - 2` applied once to `default_start_state().market.supply` (clamped ≥0) so Home `signal_next` has tiny seed-to-seed jitter without changing demand/price logic. The perturbation is documented as harness-owned, not engine-owned, and is **zero for deterministic policies' expected value** (mean 0). This makes the seed sweep non-degenerate for determinism/perf testing while keeping the authored drought as the dominant effect. | Without this, a fixed arc + fixed scripts yields identical wealth every seed — win-rate would be degenerate (100% for the best script) and AC2 would be unfalsifiable; with this, win-rate reflects true policy robustness plus tiny world jitter, and AC5 determinism is still exact (same seeds → same perturbation). | No perturbation (degenerate sweep), or full world randomization / weighted sampler (Section 15 DSL, rejected), or per-seed demand perturbation >5 (would dominate price signal). |
| 5 | **Metrics collected per game & per batch** | Per-game: `seed, policy_id, choices[5], final_wealth, wealth_delta_total, cash_low, peak_inventory, final_cash, final_grain, price_home_series[5], price_river_series[5], largest_single_turn_wealth_delta, bankrupt (cash==0 and grain==0) count`. Per-policy aggregate: `n, mean/median/min/max final_wealth, median cash_low, median peak_inventory, win_rate (wins/n_seeds), price_min/max, max_swing_max, bankrupt_count`. Per-batch: `overall price_min/max, global max_swing, any_negative_state flag, seed_count, policy_count, total_games = n_seeds * n_policies`. All integers; wealth via `_wealth(state)` = `cash + grain*home_price//1000`. | Covers every `Measure:` bullet in §9 (final wealth, cash lows, inventory, drought exposure via T4 wealth split, win rate, median, bankrupt, price ranges, largest swing) without inventing new economy. | Adding P&L attribution or Sharpe-like ratios — out of scope. |
| 6 | **Operationalizing "no dominant / no dead" — confound-controlled** | Pass iff **all** hold: <br>(a) `max_win_rate < 0.80` (no policy wins ≥80% of seeds — "essentially every" = 80%); <br>(b) `max_median / second_max_median < 1.60` (top median not 60%+ ahead); <br>(c) every non-random policy has `win_rate ≥ 0.05` and `median_final_wealth ≥ 0.70 × overall_median` (no dead strategy). <br>Thresholds are **generous** (survive ±20% cost tweaks) and **falsifiable** (a free-buy bug would push win_rate→1.0 and median ratio→>2). <br>**Confound control (addresses Sections 7–8 recurring defect):** The harness test for AC2 asserts the batch is not degenerate — checks that `random_legal` has `win_rate > 0` and that deterministic policies' `price_home_series` variance across seeds is >0 (perturbation applied), and that the win-rate comparison uses **same seeds for every policy** (paired design). A spurious pass where policies differ in affordability (e.g. one always unaffordable) is ruled out by per-policy `insufficient_*` count == 0. | Makes "dominant/dead" testable without magic. Paired seeds + affordability check prevents the classic spurious pass where two policies differed in more than the one variable under study. | Pure win-rate threshold without median ratio, or 0.50 threshold (too strict, would flag mild tuning as failure), or no confound check — rejected. |
| 7 | **Price & swing bounds — deliberate, traceable to engine** | `Home ∈ [2000, 9000]`, `River ∈ [2000, 10000]`, `largest_single_turn_wealth_delta ≤ 2000` (generous vs current max ~130). Bounds derived as `base ± max_movement_bps` over 5 turns: `5000 * (1 ± 0.20)^5 ≈ [1638, 12441]` tightened to above. A single-turn price move > `max_movement_bps` is allowed only if `before_price` already at bound. Test asserts every `price_home_series` entry in bounds and every `abs(price[t]-price[t-1]) ≤ before*0.20 + 1` (rounding). | Deliberate (tied to `max_movement_bps=2000`), integer, survives parameter tweaks (widening to 2500 bps would still pass). Catches `price *= 1.4` drought bug. | Ad-hoc bounds like `[0, 20000]` (too loose to catch bugs) or per-turn exact price assertions (too brittle). |
| 8 | **Output & exit semantics for CI** | `python backend/app/cli.py --balance --seeds 200 --json-out /tmp/balance.json` prints markdown table to stdout (columns: policy | n | win_rate | median_wealth | mean_wealth | median_cash_low | price_range | bankrupt) and writes JSON with keys `config:{seed_prefix,n_seeds,version,policies}`, `aggregates:{policy_id: {...}}`, `overall:{...}`, `per_seed:[...]`. Deterministic key order (`sort_keys=True`, policy order fixed). Exit 0 if AC2/3/4 pass, exit 2 with `FAIL: <reason>` line if any fail (never silent). No DB, no file besides optional `--json-out`. | AC6 "easy to compare in CI or local" — `diff` on JSON is stable; exit code integrates with `make test`. | HTML report, sqlite, or LLM summary — rejected. |
| 9 | **Performance budget** | `run_batch` is a tight loop over `FiveTurnGame(seed).run(policy_choices)` — no async, no subprocess, no DB. Target < 5s for 200 games (1000 turns) on CI; measured via `time` in validation. No rayon/multiprocessing in v1 (additive later if needed). | AC1 "quickly" — 1000 turns is trivial Python (< 0.5s expected). | Parallel workers or `asyncio.gather` — premature. |
| 10 | **Determinism proof — harness-specific** | Harness determinism test does **two full `run_batch` calls with identical `BatchConfig`** and asserts `json.dumps(result, sort_keys=True)` equality plus per-policy aggregate equality. It does **not** compare harness output to a harness-generated golden file (which would be tautological). A second test asserts that changing `seed_prefix` changes at least one aggregate (sensitivity). Uses `rng_for` only; no `random`/`hash()`. | AC5 "same batch configuration reproduces identical aggregate results" — proven by independent double-run, not self-comparison. | Single-run snapshot test — rejected as non-proof. |
| 11 | **Bankrupt / near-bankrupt definition** | `bankrupt = (final_cash == 0 and final_grain == 0)` (true zero, not near). `near_bankrupt = (final_cash < 100 and final_grain < 5)` — reported but not a gate (informational). AC3 gate is **no impossible negative state** (`cash<0` etc.) across all turns, not bankrupt frequency. | Spec lists "bankrupt / near-bankrupt conditions if applicable" — keep exact gate narrow, report near-bankrupt for tuning. | Defining bankrupt as `wealth < 0` (impossible since wealth≥0) or `cash < 0` (already AC3). |
| 12 | **No Section 10/11/15 leakage** | Harness lives in `engine/` (pure), CLI flag is additive in `cli.py` (no `fastapi` import), no JSON content loader, no `content_version`, no `world_modifiers`, no `render.yaml`, no React component. `STATE.md`/`DECISIONS.md` updates only. | Keeps Section 9 scope tight. | Content-driven pressure arcs, API wrapper — rejected. |

---

## Recommended Approach

Stay additive and keep the kernel as authority. Implement in dependency order:

1. **Domain (no new types):** No new `domain/` models. Reuse `GameState`, `PlayerState`, `MarketState`, `PlayerCommand`, `PressureState`, `TurnContext`. If a harness-specific `BatchConfig`/`BatchResult` is needed, define it in `engine/harness.py` as frozen Pydantic models (not `domain/`).

2. **Engine — `backend/app/engine/harness.py` (new, ~180 lines):**
   - `POLICY_IDS = ("production_heavy","storage_heavy","trade_heavy","cash_preserving","random_legal")`
   - `Policy` protocol: `def __call__(state: GameState, pressure: PressureState, ctx: TurnContext, rng: random.Random | None) -> PlayerCommand` — but implemented as plain functions with `rng_for` internally for `random_legal`.
   - Five policy functions as in Decision 3, each pure, affordability-aware, using `actor.RESOLVE_*` cost constants and `actor.affordable_quantity`.
   - `BatchConfig{seed_prefix: str, n_seeds: int, version: str, policy_ids: tuple[str,5]}` (frozen).
   - `SeedResult`, `PolicyAggregate`, `BatchResult` (frozen, with `price_min/max`, `win_rate`, etc.).
   - `run_batch(config) -> BatchResult`: for each seed `f"{prefix}-{i:04d}"` and each policy, build `start_state = _perturbed_start_state(seed)` (Decision 4, harness-only, using `blake2b` over seed), then `game = FiveTurnGame(seed, version, start_state)` and run 5 turns by calling the policy each turn: `cmd = policy(game.state, game.current_pressure, game.state.to_turn_context())`, `game.submit(cmd)`. Collect per-turn prices for ranges/swings, enforce per-turn `cash/inv/price >=0` invariant. Compute aggregates, win counts (per seed, argmax `final_wealth` among 5, tie broken deterministically by policy order). No global random.
   - Helpers: `_perturbed_start_state(seed)`, `_largest_swing(history)`, `format_markdown(result)`, `to_json(result)`.

3. **CLI — `backend/app/cli.py` (additive, ~60 lines):**
   - Add `argparse` flags `--balance` (store_true), `--seeds int` (default 200), `--seed-prefix str` (default "harness"), `--json-out path`, `--balance-version str` (default "1.0").
   - When `--balance` set: build `BatchConfig`, call `run_batch`, print markdown, optionally write JSON, evaluate AC2/3/4 gates (Decision 6/7), exit 2 on failure with `FAIL: dominant strategy ...` / `FAIL: price out of bounds ...` / `FAIL: negative state ...`, else exit 0. Never imports `fastapi`.
   - Keep existing `--choices` / interactive paths untouched.

4. **Re-export (optional):** Expose `run_batch`/`BatchConfig` via `backend/app/engine/__init__.py` for tests.

---

## Work Plan (ordered, no unrelated cleanup)

1. **Create `backend/app/engine/harness.py`** per Decisions 1–5, with `run_batch` + five policies + `BatchConfig`/`BatchResult` + markdown/json helpers. Strict types, `pyright` clean, no `random`/`hash()`/`json` loader for pressure.
2. **Extend `backend/app/cli.py`** per Decision 8 (add `--balance` flags, batch run, markdown/json output, exit semantics). Keep `parse_choice`/`parse_choices_arg` untouched.
3. **Update `backend/app/engine/__init__.py`** to re-export `run_batch`/`BatchConfig` if tests import via engine package (or tests import directly from `harness`).
4. **Tests — `backend/tests/test_balance_harness.py` (new, 8 tests):**
   - `test_harness_runs_hundreds_quickly` — `run_batch(n_seeds=200)` completes <5s, returns `total_games == 1000`.
   - `test_no_dominant_strategy_paired` — batch `n_seeds=100`, asserts `max_win_rate < 0.80` and `max_median/second_max < 1.60`, plus paired-seed and `insufficient_* == 0` confound guards. Documents what spurious pass would look like (e.g. one policy unaffordable).
   - `test_no_dead_strategy` — every non-random policy `win_rate ≥ 0.05` and `median ≥ 0.70 * overall_median`.
   - `test_no_impossible_negative_state` — exhaustive per-turn `cash/inv/supply/price >=0` across full batch, no `cash<0` etc.
   - `test_price_ranges_within_deliberate_bounds` — every Home/River price in `[2000,9000]/[2000,10000]` and per-turn movement ≤ `max_movement_bps` envelope.
   - `test_largest_swing_bounded` — `global max_swing ≤ 2000` and per-game swing matches `max(abs(wealth_delta))`.
   - `test_determinism_same_batch_identical` — double-run with same `BatchConfig` yields identical JSON and aggregates; changing `seed_prefix` changes at least one aggregate.
   - `test_harness_uses_pressure_not_bare_string` — `grep` `harness.py` for `resolve_turn.*PRESSURE`/`pressure_for_` and asserts no `resolve_turn(..., "normal"` / `"drought"` literal; also invokes `run_batch` and checks trace contains `pressure_stage` nodes with `reason_code` starting `pressure:`.
5. **No other file changes** besides `STATE.md`/`DECISIONS.md`/`BUILD_SPEC.md Status` at closeout (freshness contract).

---

## Validation Plan (exact commands, no placeholders)

Run every command from repo root. All are real paths — `backend/app/cli.py` is the CLI.

```bash
# 1. Install & gate checks (Section 1 gates)
uv sync --project backend
uv run --project backend ruff check backend
uv run --project backend ruff format --check backend
uv run --project backend pyright

# 2. Unit tests — full suite must stay green (122 existing + 8 new = 130)
uv run --project backend pytest -v

# 3. Harness batch — headless run, human-readable + JSON, AC2/3/4 gates
uv run --project backend python backend/app/cli.py --balance --seeds 200 --seed-prefix harness --version 1.0
uv run --project backend python backend/app/cli.py --balance --seeds 200 --seed-prefix harness --version 1.0 --json-out /tmp/balance.json
cat /tmp/balance.json | python3 -m json.tool | head -80

# 4. Determinism double-run (AC5) — byte-identical
uv run --project backend python backend/app/cli.py --balance --seeds 100 --seed-prefix harness --json-out /tmp/a.json
uv run --project backend python backend/app/cli.py --balance --seeds 100 --seed-prefix harness --json-out /tmp/b.json
diff /tmp/a.json /tmp/b.json && echo "deterministic: identical"
# Changing prefix must change output
uv run --project backend python backend/app/cli.py --balance --seeds 100 --seed-prefix other --json-out /tmp/c.json
diff /tmp/a.json /tmp/c.json | head -20  # must differ

# 5. Performance gate (AC1) — hundreds of games quickly
time uv run --project backend python backend/app/cli.py --balance --seeds 200 --seed-prefix perf  # expect <5s

# 6. Price & negative-state gates (AC3/4) — exit 2 on violation
uv run --project backend python backend/app/cli.py --balance --seeds 200  # exit 0 if bounds pass, 2 if fail

# 7. Purity — engine/domain import no web/DB/LLM (existing test)
uv run --project backend pytest backend/tests/test_engine_purity.py -v

# 8. No bare-string shim (Section 8 guard)
grep -rn "resolve_turn" backend/app/engine/harness.py | grep -v "PRESSURE\|pressure_for" && echo "FAIL: bare string" || echo "no bare string"
grep -rn '\"normal\"\|\"drought\"' backend/app/engine/harness.py | grep resolve_turn && echo "FAIL" || echo "ok"

# 9. Freshness — file tree & STATE.md sync (pre-push)
git status --short
graphify update .  # code-only, no API cost
```

**Highest-risk validation:** `test_no_dominant_strategy_paired` — if thresholds are too tight, it flakes on cost tweaks; if too loose, it passes spuriously. Mitigated by generous 0.80/1.60/0.05/0.70 thresholds plus paired-seed and affordability guards, and by documenting the spurious-pass confound explicitly in the test docstring.

---

## Risks / Rollback

- **Risk: `random_legal` variance too low to make win-rate non-degenerate.** Mitigation: Decision 4 micro-perturbation (±2 supply) plus random policy's RNG ensures variance; test asserts variance >0 before checking dominance.
- **Risk: Bounds too tight and future cost tweak fails AC4 spuriously.** Mitigation: Bounds are generous (2× base) and tied to `max_movement_bps`; test failure message prints observed vs bound for easy tuning.
- **Risk: Harness loop regresses determinism via global `random`.** Mitigation: `rng_for` only, `grep` for `import random` in `harness.py` fails CI, determinism double-run test.
- **Rollback:** Delete `backend/app/engine/harness.py` and the `--balance` flag block in `cli.py`; no engine change to revert. `BUILD_SPEC.md` Section 9 stays `NOT STARTED` until re-landed.

---

## Grill — Headless Stress Test (decision-forcing questions, answered from code/evidence, folded into plan)

> Because this session is headless, each question is answered inline from code and computed evidence. No interactive prompt is needed. Items that genuinely require the human product owner are marked **ESCALATE**.

**Q1 — Why not just add `resolve_turn(..., world: str)` convenience overload for headless callers?**
*Recommended:* Do not. *Answer:* Section 8 removed it (many places fixed), and `pressure.py:63-92` already provides `PRESSURE_NORMAL`/`PRESSURE_DROUGHT`/`pressure_for_world` as the mechanical replacement (G1). Re-adding a `str|PressureState` union would reintroduce the single-source violation `world` vs `pressure.world` (F2). Plan Decision 2 keeps only `PressureState` and adds a grep guard. **Settled.**

**Q2 — Five policies: are fixed 5-length literal lists sufficient, or should policies be adaptive bots?**
*Recommended:* Adaptive bots (functions of `state/pressure/ctx`) as in Decision 3. *Answer:* Fixed lists like `["hold"]*5` always produce `insufficient_*` for `buy_grain` when storage is full, making AC3 spurious (failure looks like strategy failure, not construct bug). Bots that call `affordable_quantity`/`storage-inventory` stay legal and prove the economy, not the list. The Section 7 rivals already use this pattern (`choose_rival_command(ObservableContext)`). **Folded into Decision 3.** *No escalation.*

**Q3 — AC2 "no universally dominant strategy" — what is the precise pass/fail? Isn't any threshold magic?**
*Recommended:* Generous triple gate as in Decision 6. *Answer:* Spec says "avoid magic thresholds without justification; prefer assertions that survive parameter tweaks." The plan uses **three** checks: `max_win_rate < 0.80` (80% = "essentially every"), `max_median/second_max < 1.60`, and `every non-random win_rate ≥ 0.05`. Each is generous (±20% cost tweak stays inside) and together they catch a true bug (free buy → win_rate→1.0, median ratio→>2) without flagging mild tuning. A spurious pass where one policy is unaffordable is ruled out by `insufficient_* == 0`. *Justification added to Decision 6.* **Settled.** *ESCALATE only if product wants a different "dominant" definition (e.g. top-2 win-rate vs median) — current 0.80/1.60 is a durable default.*

**Q4 — What confound could make the AC2/AC1 warning-isolated test pass spuriously, and how is it ruled out?**
*Recommended:* Paired seeds + affordability + price-variance guards. *Answer:* Sections 7–8 recurring defect: comparing two policies that differed in more than the one variable (e.g. `buy_grain` also changes cash vs `expand_farm` changes supply). For Section 9, the analogous spurious pass is: dominant-strategy test passes because one policy always hits `insufficient_cash` and never actually executes its intended strategy, so it never wins — looks balanced but isn't. The plan rules this out by (a) paired design (same seeds for every policy), (b) `insufficient_* == 0` for deterministic policies, (c) asserting `price_home_series` variance >0 (perturbation applied). Each new test's docstring states the confound explicitly. **Folded into Decision 6 & Work Plan 4.** **Settled.**

**Q5 — AC4 price bounds: what are "deliberate" bounds and why these numbers?**
*Recommended:* `[2000,9000]` Home / `[2000,10000]` River as in Decision 7. *Answer:* Computed from engine: `base 5000`, `max_movement_bps 2000` (20%/turn), 5 turns → `5000*(1.20)^5≈12441` theoretical max, `5000*(0.80)^5≈1638` min. Tightening to `[2000,9000]` keeps a direct `price*=1.4` drought mutation outside, while surviving a `max_movement_bps` bump to 2500. Bounds are in milliunits, integer, and derived from `MarketState.max_movement_bps`, not arbitrary. **Settled.**

**Q6 — How does the seed sweep produce varied wealth if the world arc is fixed? Isn't wealth identical every seed?**
*Recommended:* Harness-only micro-perturbation + random-policy RNG as in Decision 4. *Answer:* Verified: `turn.py:86-119` price is supply/demand deterministic; `rng_for` jitter is consumed not applied; rivals are isolated. So without harness help, deterministic scripts produce identical wealth per seed → win-rate degenerate (100% for best). Decision 4 adds `±2` supply jitter via `blake2(seed)` micro-perturbation (mean 0, bounded) plus `random_legal`'s `rng_for` variance, making the sweep non-degenerate while keeping the authored drought dominant. Perturbation is harness-owned (not engine) and exactly reproducing. **Settled.** *Alternative of "no perturbation, define AC2 as median comparison on one arc" was rejected because AC1 explicitly says "many seeds" and AC5 requires seed-driven determinism to be testable.*

**Q7 — Where does the harness command live? `cli.py` vs new binary?**
*Recommended:* Extend `backend/app/cli.py` (real path) as in Decision 1/8. *Answer:* User prompt says "exact validation commands using real paths (the CLI is `backend/app/cli.py`)." So `--balance` is added to that file, not a new `balance_cli.py`. Keeps one entry point and matches the existing `--choices`/`--seed` flags. Verified via `ls backend/app/cli.py` and `STATE.md` "CLI `backend/app/cli.py`". **Settled.**

**Q8 — Determinism: how to prove AC5 without a tautological golden file?**
*Recommended:* Double-run equality as in Decision 10. *Answer:* A test that writes a golden file and compares output to itself proves nothing. The plan asserts `run_batch(config) == run_batch(config)` via two independent calls plus `diff` on `--json-out` files, and a second assertion that changing `seed_prefix` *does* change output (sensitivity). No `hash()` usage; `json.dumps(sort_keys=True)` ensures stability. **Settled.**

**Q9 — Does the harness need FastAPI/DB? Does it keep `engine` pure?**
*Recommended:* No — pure sync, no `fastapi`/`sqlalchemy`/`httpx`. *Answer:* `engine/harness.py` imports only `domain/*`, `engine/pressure`, `engine/prototype`, `engine/actor`, `engine/rng`, `engine/turn` (pure). `cli.py` already is I/O, allowed to import harness. `test_engine_purity.py` will continue to assert `backend/app/engine` has no web/DB imports. **Settled.**

**Q10 — Bankrupt definition: what counts?**
*Recommended:* Exact `cash==0 and grain==0` as bankrupt, `<100 cash and <5 grain` as near-bankrupt informational, AC3 gate is negativity not bankruptcy frequency (Decision 11). *Answer:* `Money/Quantity ge=0` already prevents negatives; harness asserts no negatives across all turns. Bankruptcy is reported but not a hard gate — otherwise a deliberately cash-preserving strategy that ends low-cash would be penalized as "broken." **Settled.**

**Q11 — Performance: can hundreds of games run "quickly" without async/parallel?**
*Recommended:* Yes — tight loop, no parallelism in v1 (Decision 9). *Answer:* One `FiveTurnGame.run` is ~5× `resolve_turn` with integer math and ~10 Pydantic validations. 200 games = 1000 turns → <0.5s expected on CI (measured in validation). Adding `asyncio` or `multiprocessing` is premature abstraction. **Settled.**

**Q12 — Output for CI: what is "easy to compare"?**
*Recommended:* Markdown table on stdout + stable JSON file with sorted keys (Decision 8). *Answer:* `diff` on JSON is byte-stable because `sort_keys=True` and policy order is fixed `POLICY_IDS`. Exit code 0/2 integrates with `make test` and CI pipelines. No HTML, no sqlite. **Settled.**

**ESCALATE (none blocking):**
- If product prefers AC2 thresholds of `0.90` instead of `0.80` (more lenient) or wants win-rate computed as pairwise Elo vs argmax, that is a one-line `BatchConfig` tweak — plan is written to allow it without structural change. No escalation needed to proceed.

---

## Open Questions

None — all implementation choices are settled above. The only product-tunable values are the three AC2 thresholds and price bounds, each with justification and a clear line to edit in `harness.py: _GATES`. No `Open Questions` section with unresolved implementation remains.

---

## What the Grill Changed

- **Added Decision 4 micro-perturbation** — grill Q6 exposed the degenerate seed sweep (fixed arc → identical wealth every seed → win-rate unfalsifiable). Fixed by harness-only `±2` supply jitter (mean 0, blake2-derived, deterministic) plus random-policy RNG, with variance assertions.
- **Tightened Decision 6 with confound guards** — grill Q4 forced explicit spurious-pass analysis (the Sections 7–8 recurring defect: policies differing in affordability, not strategy). Added paired-seed design, `insufficient_* == 0`, and price-variance >0 assertions.
- **Justified price bounds (Decision 7) from `max_movement_bps`** — grill Q5 demanded "deliberate" derivation; bounds now computed from `5000*(1.20)^5` and tied to engine, not arbitrary.
- **Made AC5 determinism proof non-tautological (Decision 10)** — grill Q8 replaced golden-file comparison with double-run equality + sensitivity test.
- **Locked CLI path to `backend/app/cli.py --balance`** — grill Q7 ensured validation commands use the real file, and Decision 2 added the `no bare string` grep guard.
- **Clarified bankrupt vs negative-state (Decision 11)** — grill Q10 split AC3 (negativity gate) from informational bankrupt/near-bankrupt.

---

## Fit to Stack & Hosting

- Python 3.12, Pydantic v2, `uv` (`uv sync --project backend`), `ruff`/`pyright` strict — harness adds no new dependencies.
- No Postgres/Render change — remains in-memory until Section 16.
- No frontend change.

---

## Implementation Authority

This plan is the authority for Section 9. Build exactly the files and tests listed in Work Plan 1–4, using `PRESSURE_NORMAL`/`PRESSURE_DROUGHT`/`pressure_for_world`/`PRESSURE_ARC` for every `resolve_turn` caller, honoring the determinism and pure-engine rules in `BUILD_SPEC.md` Part III and `AGENTS.md` §7. Stop at Section 9 gates; do not start Section 10 (FastAPI) or 11 (React).
