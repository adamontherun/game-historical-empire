# Section 9 — Headless Strategy and Balance Harness — Plan (Rev 2 — regional_output fix, per review round 1)

**Date:** 2026-08-10 (Rev 2)
**Branch:** `section/9-balance-harness` (from `origin/main` at Section 8 merge)
**Spec Authority:** `BUILD_SPEC.md` Section 9 (Status: NOT STARTED) + global §§10–16 + `DECISIONS.md` 001–012 + `STATE.md` §8 + `docs/plans/2026-08-10-section-9-review-round-1.md` (empirical, not opinion)
**Related:** `backend/app/domain/types.py` (MarketState), `backend/app/domain/pressure.py`, `backend/app/domain/trace.py`, `backend/app/engine/pressure.py` (PRESSURE_ARC/constants), `backend/app/engine/turn.py` (supply+price, now regional), `backend/app/engine/actor.py` (shared drought primitive), `backend/app/engine/prototype.py` (default_start_state), `backend/app/engine/rivals.py`, `backend/app/engine/rng.py`, `backend/app/cli.py` (`backend/app/cli.py`)

> **Rev 2 change summary vs Rev 1:** Review round 1 proved Decision 4's ±2 perturbation is useless (0.3% wealth movement, winner never flips) and that the game has a universally dominant "do nothing" strategy (hold 1909 vs production 548). Root cause: `signal_next = max(0, signal + farm_output - demand)` makes the player the entire supply side — expanding floods your own market, drought is invisible without a farm. Rev 2 adopts the settled design decision: add non-player `regional_output` to Home `MarketState`, apply the *same* `DROUGHT_YIELD_REDUCTION_BPS` via the existing actor primitive, retune `default_start_state` so player's farm is 15–25% of total and demand stabilises the signal in normal, emit `regional_output` causal nodes. Decision 4 deleted. Decision 6's `win_rate ≥0.05` dead-strategy floor deleted (unsatisfiable under determinism). Thresholds land as *reported* (exit 2) first, converted to blocking only once the economy passes. Honest that deterministic policies on a fixed authored arc are seed-invariant — seed variation comes from `random_legal` only.

---

## Goal

1. **Fix the economy's dominant-strategy pathology at lowest MVP complexity** so `BUILD_SPEC §2`'s signature chain is literally true: `drought -> regional farm output falls -> regional supply falls -> price pressure rises -> stored grain becomes more valuable` even for a producer with no farm, and production is not a self-harm trap.
2. Prove the fix with a **headless balance harness** that runs hundreds of deterministic five-turn games across scripted policies and many seeds, aggregates wealth/cash/inventory/price/swing metrics, and emits CI-comparable output. Headless callers use `PRESSURE_NORMAL` / `PRESSURE_DROUGHT` / `pressure_for_world` / `PRESSURE_ARC` — never a bare `"normal"/"drought"` string overload on `resolve_turn`.

## Success Criteria (maps to Section 9 AC + global rules + review)

1. **Economy truthfulness (new, blocks AC2).** `MarketState` Home has `regional_output: Quantity`. Supply is `signal_next = max(0, signal + regional_output_after_world + farm_output - demand)` where `regional_output_after_world` reuses the same `DROUGHT_YIELD_REDUCTION_BPS=4000` via `actor.compute_farm_output`/`_regional` (no second formula). Trace shows `pressure_stage -> world -> regional_output -> home_supply -> home_price` alongside `farm_output -> home_supply`. Invariants hold: drought raises Home price vs normal, no negative states, wealth decomposition exact, no `pressure->price` direct edge, Section 8 warning-isolation equality still holds (retuned numbers).
2. **AC1 — Hundreds of games quickly.** One command runs ≥200 five-turn games (5 policies × 40 seeds) in <5s (no DB/network). CLI is `backend/app/cli.py`: `uv run --project backend python backend/app/cli.py --balance ...`.
3. **AC2 — No universally dominant strategy (reported first).** Harness evaluates and **reports** (exit 2 on breach, not a hard-failing unit test on first land). Pass iff `max_median / second_max_median < 1.60` (top median not 60% ahead, generous vs ±20% cost tweaks). `win_rate` is computed but **not** gated by a `≥0.05` floor — deterministic policies on a fixed arc have win-rate ∈ {0,1} by construction, so that floor is unsatisfiable; median ratio is the honest dead-strategy test. Rationale: a free-buy bug pushes ratio →>2; mild tuning stays inside. *Convert to blocking test only once the real economy passes.*
4. **AC2b — No obviously dead strategy (reported).** Every non-random policy has `median_final_wealth ≥ 0.70 × overall_median`. Under current broken economy `production` at 548 vs median ~1690 correctly flags as dead; after tuning this must pass.
5. **AC3 — No routine impossible negative state.** Zero `cash<0`/`grain<0`/`supply<0`/`price≤0` across full batch, and `insufficient_* == 0` for deterministic policies (affordability guard) — proves policies are legal, not that the test was loosened.
6. **AC4 — Price ranges within deliberate bounds.** Every Home price ∈ `[2000, 9000]`, River ∈ `[2000, 10000]` (milliunits), per-turn move ≤ `max_movement_bps` envelope. Bounds = `base ± 20%/turn` over 5 turns (`5000*(1.20)^5≈12441`, tightened) — a `price*=1.4` drought bug violates.
7. **AC5 — Determinism.** Same `(seed_prefix, n_seeds, version)` batch → byte-identical JSON + aggregates (double-run equality, not golden file). No global `random`, no `hash()`, integers only via `rng_for`.
8. **AC6 — CI-comparable output.** Markdown table to stdout + stable JSON (`sort_keys`, fixed `POLICY_IDS` order) via `--json-out`. Exit 0 on all gates passing, 2 on threshold breach with one-line `FAIL: ...`.
9. **Housekeeping.** `engine`/`domain` pure, `resolve_turn(state, command, pressure: PressureState, rng_context)` unchanged, no bare-string shim, no Section 10/11/15 material (no FastAPI, no React, no content DSL/`world_modifiers`/`market-share`/`rival production→supply`).

---

## Context And Current Facts (verified against code)

- **Spec §9:** Five scripted policies (production-heavy, storage-heavy, trade-heavy, cash-preserving, random legal), many deterministic seeds, metrics (final wealth, cash lows, inventory, drought exposure, win rate, median, bankrupt/near-bankrupt, price ranges, largest swing), targets (no dominant, no dead, preparation mitigates luck, legible ranges). AC1–6 as above.
- **Review round 1 empirical:** `turn.py:146-164` discards both `rng_for` draws — nothing depends on seed; Decision 4's ±2 supply sweep moves wealth ~0.3% and never flips winner (cash wins all 5 deltas); wider band `cash∈{700,1000,1400}×supply∈{85,100,115}×demand∈{85,95}` (18 configs) — `hold` wins all 18, `distinct winners = {cash}`. With every command executing cleanly (`reason_code` verified, no `insufficient_*`): `hold×5=1909`, `granary+buy20=1746`, `granary×3=1690`, `secure+buy+ship=1448`, `expand×2=548`. Doing nothing dominates; production is ruinous because own `farm_output` floods `home_supply`.
- **Pressure (Section 8):** `domain/pressure.py` `PressureState{pressure_id, stage, activation_turn, world, signal, title, causal_source_id}` (7 fields, biconditional, single source) + `engine/pressure.py` `PRESSURE_ARC` 5 stages + `PRESSURE_NORMAL`/`PRESSURE_DROUGHT`/`pressure_for_world` + `pressure_for_turn`/`next_world_known_for_turn`. `prototype.py:64-66` derives `TURN_SPECS` from `PRESSURE_ARC`. `turn.py:122` `resolve_turn(..., pressure: PressureState, ...)` with `pressure_stage` parent of `world`, chain `pressure->world->farm_output->supply->price->...->wealth`.
- **Prototype:** `FiveTurnGame` owns `state+history:5+rival_history:5×(Mira,Daran)` isolated from shared `market.supply`; `turn_limit=5`, `turn==0` enforced; two-phase submit (rivals choose pre→player resolve→rivals settle `buy@pre_home`, `ship@resolved_river`). `default_start_state` currently cash 1000 grain 20 farm 10 storage 200 Home 100/90/5000 River 80/130/5200 route 800/20/10000 — **will be retuned** (player ~15–25% of total, demand ≈ signal+regional+farm in normal).
- **Actor:** `actor.py` single source `YIELD_PER_CAPACITY=10`, `DROUGHT_YIELD_REDUCTION_BPS=4000`, `EXPAND_FARM_COST=500`, `BUILD_GRANARY_COST=300`, `ROUTE_ESTABLISH_COST=400`, `compute_farm_output(cap, world) -> (output, base, reason)` — the *only* drought formula.
- **Numerics/RNG:** `Money/Quantity/PriceMilliunits ge=0`, `rounding.py` helpers, `rng.py` `rng_for` via blake2b, no global random. `test_pressure_arc.py` covers arc order, 7-field, biconditional, causal single source, mechanism-isolated warning, `current_pressure` None when complete.
- **CLI:** `backend/app/cli.py` (not `engine/cli.py`) — existing flags `--choices/--seed/--version`; harness extends with `--balance` group. No new binary.

---

## Constraints And Non-goals

- **Hard constraints:** Determinism (§11), canonical integers (§12), pure `engine`/`domain` (§13), causal trace parent chain preserved, no global `random`/`hash()`, `resolve_turn` keeps `PressureState` arg (no bare-string overload), harness reports before gating per review § "Thresholds must not land as hard-failing tests first", legitimate numeric updates only — no deleted/loosened assertions per `BUILD_SPEC §0.4`, invariants stay asserted.
- **Do not build:** Section 10 FastAPI, Section 11 React, Section 15 content loader/JSON DSL/`world_modifiers`/weighted sampler, `market_share` params, rival production→regional supply, new player commands, second drought formula, route congestion/contested supply, generic rival framework. Exactly: one field `regional_output`, one reuse of `compute_farm_output` primitive, retuned constants.
- **Do not regress:** 122 existing tests remain asserted as invariants (updated numbers where economy changed, not weakened); `trace.py` validator not loosened; `TURN_ORDER` only appended with `regional_output` (see Decision 5); graphify updated.

---

## Key Decisions (all settled — no open choices)

| # | Decision | Choice | Why | Alternative Rejected |
|---|----------|--------|-----|----------------------|
| 1 | **Harness location & shape** | New `backend/app/engine/harness.py` (pure, sync) + CLI extension in `backend/app/cli.py` (`--balance` flags). `harness.py` owns: `POLICY_IDS = ("production_heavy","storage_heavy","trade_heavy","cash_preserving","random_legal")`, `Policy` protocol `(state, pressure, ctx) -> PlayerCommand`, five policy fns, `BatchConfig{seed_prefix, n_seeds, version, policy_ids}`, `SeedResult`/`PolicyAggregate`/`BatchResult` (frozen), `run_batch(config)->BatchResult`, `format_markdown`/`to_json`. No `backend/app/balance/` dir. | Keeps engine pure; `FiveTurnGame` stays orchestrator; harness is thin batch runner. | New package/binary/FastAPI endpoint — extra surface. |
| 2 | **No bare-string shim** | `harness.py` and all tests call `resolve_turn` only via `FiveTurnGame.submit` or directly with `PRESSURE_NORMAL`/`PRESSURE_DROUGHT`/`pressure_for_world`/`pressure_for_turn`. No `world: str` overload, no `isinstance(pressure,str)`. Grep CI asserts no `resolve_turn(..., "normal"` literal in harness. | Section 8 guardrail; single source of truth. | `PressureState|str` union — rejected. |
| 3 | **Policy definitions — affordability-aware, seed-aware only via random** | Five policies as pure fns of `(state, pressure, ctx)`:<br>• **production_heavy:** `expand_farm` while `cash >= EXPAND_FARM_COST+200` for first 2 turns else `hold` (never `buy`/`secure`).<br>• **storage_heavy:** `build_granary` T1 if affordable, then `buy_grain:min(20, affordable, space)` T2–T3, then `hold`/`ship` T5.<br>• **trade_heavy:** `secure_route` T1 if affordable, `buy_grain:10` T2, `ship_grain: min(10, inv, capacity)` T4–T5 when established.<br>• **cash_preserving:** `hold` ×5.<br>• **random_legal:** uniform among `available_commands()` filtered by affordability (`cash>=cost`, `affordable>0`, `inv>0&&established` for ship) using `rng_for(seed, version, turn, "harness", policy_id, 0)`. Each deterministic policy asserts `reason_code != insufficient_*` (legal by construction). | Legible, intentionally different postures, legal by construction so AC3 is meaningful. Seed variation comes **only** from `random_legal`'s `rng_for`; deterministic policies are honestly seed-invariant on a fixed arc (review E5). | Fixed 5-literal lists ignoring state (emit unaffordable), prose-parsing policies — rejected. |
| 4 | **Deleted — ±2 perturbation** | **Delete Decision 4 entirely.** No harness-owned supply perturbation. Batch enumerates `seeds = [f"{prefix}-{i:04d}" for i in range(n_seeds)]` (default `prefix="harness"`, `n_seeds=200`, `version` from config). Reviews E2/E3 prove ±2 and even a wide band leave winner unchanged (0.3% movement, `hold` wins 18/18). Honest statement: deterministic policies are seed-invariant by construction; that is a property, not a defect to paper over. | Removes divergence from shipped start state while achieving nothing. | Any perturbation, wider band, per-seed demand jitter — rejected. Genuine world diversity (varying pressure arc) is Section 15 — not now. |
| 5 | **Economy fix — one field, one primitive reuse, one supply formula change + causal nodes** | (a) Add `regional_output: Quantity = Field(ge=0, ...)` to `MarketState` in `domain/types.py` (Home only; River Town unchanged, stays exogenous). Default e.g. `300–400` (tuned in Phase 3 so player farm ≈15–25% of total).<br>(b) In `turn.py` add helper `_regional_output_after_world(base, world)` that reuses `actor`'s `DROUGHT_YIELD_REDUCTION_BPS` (i.e. `base*6000//10000` if drought else `base`; or reuse `compute_farm_output` shape — single formula). New supply: `next_supply = max(0, signal + regional_output_after_world + farm_output - demand)`.<br>(c) Emit `CausalNode(id="regional_output", kind="production", parent_ids=("world",), before=base, after=after, delta=after-base, reason_code="drought_reduced_yield"|"normal_yield")` and make `home_supply` parented by `("regional_output","farm_output","home_demand")` (or `("regional_output","farm_output","demand")` plus alias). Chain: `pressure_stage->world->regional_output->home_supply->home_price` alongside `farm_output->home_supply`. Extend `TURN_ORDER` to `... -> regional_output -> home_supply ...` (append only). No rival production→supply, no new commands, no second drought formula. | Lowest-complexity that fixes both consequences: player no longer floods own market alone, and drought is felt even with `farm_capacity=0`. Reusing the actor primitive guarantees one drought number (review "Do not write a second drought formula"). One field + retuned constants is the settled design. | Market-share param, rival feeding supply, second formula, new good/route — all rejected. |
| 6 | **Retuned start state (empirical, Phase 3)** | Set `prototype.py:default_start_state` so normal turns are roughly signal-stable and player's share is 15–25%. Example search band (not hard-coded as law, but as starting point for Phase 3 tuning): `regional_output ∈ {320,360,400}`, `farm_capacity ∈ {10,12}`, `supply (signal) ∈ {240,280}`, `demand ≈ signal+regional+farm - ε` (so `next_supply ≈ supply` in normal, drought drops it ~40% of regional). Cash/storage/route unchanged initially unless tuning shows payback issue. Exact numbers chosen empirically by running the harness until review's balance table no longer has `hold` dominant and `production` dead — reported in final plan closeout. | Review's follow-up says "Pick the exact numbers empirically — run the harness and tune until the balance table shows no universally dominant strategy." Honest that deterministic policies' win-rate is still {0,1}, so median ratio is the honest dead-strategy test (Decision 7). | Hand-tuning one constant without harness evidence — rejected. |
| 7 | **Operationalizing "no dominant / no dead" — thresholds are reported first, not blocking** | Harness **reports** (exit 2 on breach) — not a hard `assert` in `pytest` on first land. Gates:<br>• Dominant: `max_median / second_max_median < 1.60` (generous).<br>• Dead: every non-random policy `median ≥ 0.70 × overall_median` (median-ratio only; deletes prior `win_rate ≥0.05` floor which is unsatisfiable under determinism — review E6).<br>`win_rate` is still computed and shown (per-seed `argmax final_wealth` among 5, tie by `POLICY_IDS` order) but **honestly noted as seed-invariant** for deterministic policies — narrative in markdown: "deterministic policies are seed-invariant on this fixed arc; seed variation comes from random_legal only."<br>**Convert to blocking unit test only once the real economy passes** (Phase 3 TUNED → add `test_balance_thresholds_pass` that calls `run_batch` and asserts the two gates). This avoids loosening thresholds to go green (BUILD_SPEC §0.4). | Makes AC2 falsifiable without magic, survives ±20% tweaks, respects determinism. | `win_rate ≥0.05` floor, equality-of-outcomes target, golden-file-only determinism — rejected. |
| 8 | **Metrics collected** | Per-game: `seed, policy_id, choices[5], final_wealth, wealth_delta, cash_low, peak_inventory, final_cash/grain, price_home_series[5], price_river_series[5], largest_single_turn_wealth_delta, bankrupt flag`. Per-policy aggregate: `n, mean/median/min/max final_wealth, median cash_low, median peak_inventory, win_rate, price min/max, max_swing_max, bankrupt_count`. Per-batch: `overall price min/max, global max_swing, any_negative_state, total_games`. All ints; `final_wealth = cash + grain*home_price//1000`. | Covers every `Measure:` bullet (§9) without new economy. | P&L attribution/Sharpe — out of scope. |
| 9 | **Output & exit semantics for CI** | `python backend/app/cli.py --balance --seeds 200 --json-out /tmp/balance.json` prints markdown table (policy | n | win_rate | median_wealth | mean_wealth | median_cash_low | price_range | bankrupt) + writes JSON `config/aggregates/overall/per_seed` with `sort_keys`, fixed `POLICY_IDS` order. Exit 0 if AC3/AC4 and reported dominance/dead gates pass; exit 2 with `FAIL: dominant ...` / `FAIL: dead ...` / `FAIL: negative state` if any breach. | AC6 "easy to compare" — `diff` on JSON stable; exit integrates with CI. | HTML/sqlite/LLM summary — rejected. |
| 10 | **Performance & determinism** | `run_batch` is a tight loop `FiveTurnGame(seed, version, start_state).run(policy_choices)` — no async/DB. Target <5s for 200 games (1000 turns). Determinism proven by double-run equality (`json.dumps(sort_keys)`) + sensitivity (changing `seed_prefix` changes only `random_legal` aggregates). Uses `rng_for` only, no `random`/`hash()`. | AC1/AC5. | Parallel workers — premature. |
| 11 | **Existing tests — numeric updates vs assertion weakening** | Changing supply formula and start constants **will** change expected numbers (e.g. `test_five_turn_prototype.py:101-114` supply 110/70, `test_pressure_arc.py` T4 supply 100==100/price 4750 etc., `test_two_markets_route.py` price expectations). Legitimate: update expected numbers to reflect intentional economy change and document `Updated: regional_output economy — ...` in commit message/test comment. Forbidden: deleting asserts, loosening `==` to `>=`, removing tests, weakening bounds. Every invariant stays asserted: `drought price > normal` (relative), non-negativity, determinism, wealth decomposition, `TURN_ORDER`, `pressure_stage->world->regional_output/farm_output->home_supply->home_price`, no `pressure->price` edge, Section 8 warning-isolation equality (retuned numbers but equality itself must hold, fully affordable, threshold-free). If an invariant genuinely cannot hold, **stop and report** rather than adjust. | Review § "About existing tests — read carefully" and BUILD_SPEC §0.4. | Deleting coverage to go green — forbidden. |
| 12 | **No Section 10/11/15 leakage** | Harness in `engine/` (pure), CLI additive (no `fastapi`), no JSON loader, no `world_modifiers`, no `render.yaml`, no React. `STATE.md`/`DECISIONS.md`/`BUILD_SPEC` only at closeout. | Keeps Section 9 scope tight. | Content-driven arcs, API wrapper — rejected. |

---

## Recommended Approach (dependency order)

1. **Domain — `backend/app/domain/types.py`:** Add `regional_output: Quantity = Field(default=..., ge=0)` to `MarketState` (Home). Keep `demand`/`supply`/`base_price`/`current_price`/etc. River `regional_output` may default 0 or not used; harness only reads Home. Validate frozen, `ge=0`. No other new domain type.
2. **Engine — `backend/app/engine/turn.py`:** New helper `_regional_output_after_world(base: int, world) -> (after, reason)` reusing `DROUGHT_YIELD_REDUCTION_BPS` from `actor.py` (single formula). Replace `next_supply = max(0, signal + farm_output - demand)` with `max(0, signal + regional_after + farm_output - demand)`. Emit `regional_output` node (parents `world`), re-parent `home_supply` to `("regional_output","farm_output","home_demand")` (and keep `supply` alias `("regional_output","farm_output","demand")` for backward compat), update `TURN_ORDER` to include `regional_output`. Keep `_target_price/_bounded_price` and wealth decomposition untouched.
3. **Engine — `backend/app/engine/prototype.py`:** Retune `default_start_state` empirically (Decision 6): set `regional_output` and `supply/demand` so player's farm ≈15–25% of `regional+farm` and normal `next_supply ≈ supply`. Example starting point: `regional_output=360`, `supply=280`, `demand = supply+regional_output+farm_output - slack` where `slack ≈ 5–10` for mild surplus. Keep cash 1000 grain 20 farm 10 storage 200 unless Phase 3 tuning demands cost/yield tweak (do not change `YIELD_PER_CAPACITY` or costs unless harness shows payback failure — report if changed).
4. **Engine — new `backend/app/engine/harness.py` (~180 lines):** Per Decisions 1,3,7,8,10 — five policies, `BatchConfig/SeedResult/PolicyAggregate/BatchResult` frozen, `run_batch`, `format_markdown`/`to_json`, dominance/dead evaluation (reported). No global random, no `hash()`, uses `rival` `rng_for` only for `random_legal`.
5. **CLI — `backend/app/cli.py` (~60 lines additive):** New flags `--balance`, `--seeds` (default 200), `--seed-prefix` (default "harness"), `--json-out`, `--balance-version` (default "1.0"). When `--balance`: build `BatchConfig`, call `run_batch`, print markdown, optionally write JSON, evaluate gates and exit 2 on breach. Keep `--choices`/interactive paths untouched. No `fastapi` import.
6. **Re-export (optional):** Expose `run_batch/BatchConfig` via `engine/__init__.py` for tests.
7. **Tests — Phase 1 land (non-blocking harness):** `backend/tests/test_balance_harness.py` with 7–8 tests that **report** but do not hard-fail on dominance on first land (see Validation Plan). Determinism, price bounds, negativity, and determinism-sensitive tests are blocking; dominance/dead is informational until Phase 3 tuning passes, then converted to blocking.

---

## Work Plan (ordered, no unrelated cleanup)

1. **Create `engine/harness.py`** per Decisions 1,3,7,8,10 — five policies, `BatchConfig`/`BatchResult`, `run_batch`, markdown/json, dominance/dead evaluation (reported). Strict types, `pyright` clean, no `random`/`hash()`, uses `PRESSURE_*` only.
2. **Patch `domain/types.py` — add `regional_output` to `MarketState`.**
3. **Patch `engine/turn.py` — reuse drought primitive, new supply formula, `regional_output` causal nodes, re-parent `home_supply`, extend `TURN_ORDER`.**
4. **Patch `engine/prototype.py` — retune `default_start_state` (regional, supply, demand) for 15–25% player share and stable normal signal.**
5. **Extend `app/cli.py` — add `--balance` flags, batch run, markdown/json, exit semantics.**
6. **Update `engine/__init__.py` re-exports (if tests import via package).**
7. **Tests — `tests/test_balance_harness.py` (new, 7 tests on first land, 8th converted after tuning):**
   - `test_harness_runs_hundreds_quickly` — `run_batch(n_seeds=200)` <5s, `total_games==1000`.
   - `test_balance_thresholds_reported_not_blocking` (first land — informational) — runs batch and asserts report contains `median_ratio` and `price_range`, does **not** assert dominance passes; documents that thresholds are evaluated with exit 2, not hard `assert`.
   - `test_no_impossible_negative_state` — exhaustive `cash/inv/supply/price >=0`, `price>0`, `insufficient_*==0` for deterministic policies.
   - `test_price_ranges_within_deliberate_bounds` — Home `[2000,9000]`, River `[2000,10000]`, per-turn move ≤ `max_movement_bps` envelope.
   - `test_largest_swing_bounded` — `global max_swing ≤ 2500` (generous vs current ~130–2000 after regional).
   - `test_determinism_same_batch_identical` — double-run identical JSON/aggregates; changing `seed_prefix` changes only `random_legal`.
   - `test_harness_uses_pressure_not_bare_string` — `grep` harness for `PRESSURE`/ `pressure_for_` and no `resolve_turn(..., "normal"` literal; checks trace `pressure_stage` nodes with `pressure:` prefix.
   - `test_regional_output_chain_truthful` (new) — one normal vs drought `resolve_turn` with `regional_output>0` proves `drought price > normal price` even when `farm_capacity==0` (player with no farm feels drought via regional), and trace has `regional_output` parented by `world` and `home_supply` parented by `regional_output`+`farm_output`. Be honest about determinism: deterministic policies are seed-invariant, so `win_rate` is shown but not gated by `≥0.05`.
8. **Update existing tests' expected numbers (legitimate):** `test_five_turn_prototype.py:101-114`, `test_pressure_arc.py` T4 supply/price equality pre-condition, `test_two_markets_route.py` price expectations, any `default_start_state` supply/demand/wealth assertions — update numbers, keep equalities/invariants, comment `Updated: regional_output economy — supply now includes regional_output`.
9. **Phase 3 tuning loop:** Run `python backend/app/cli.py --balance --seeds 200` repeatedly, adjust `default_start_state` regional/supply/demand (and if absolutely needed, `YIELD_PER_CAPACITY`/`EXPAND_FARM_COST` — report any cost change) until `max_median/second_max <1.60` and every `median ≥0.70×overall` and `hold` no longer dominates. Report final balance table and tuning deltas. Then convert `test_balance_thresholds_reported_not_blocking` into blocking `test_no_dominant_or_dead_strategy_by_median_ratio` that asserts the two gates.
10. **Closeout:** `make test`/`make lint`/`make type`/`make format-check` green, `graphify update .`, `STATE.md` synced to observed behavior (new wealth/price/bounds), `DECISIONS.md` entry for regional_output rationale, `BUILD_SPEC.md` Section 9 `COMPLETE` only if gates pass. Commit and push `section/9-balance-harness`. Stop at Section 9 — do not start Section 10.

---

## Validation Plan (exact commands, real paths)

```bash
# 1. Install & gates
uv sync --project backend
uv run --project backend ruff check backend
uv run --project backend ruff format --check backend
uv run --project backend pyright

# 2. Unit — must stay green; new harness tests included (12x existing + 7-8 new)
uv run --project backend pytest -v
# expect 122 + 7-8 = 129-130 passing on first land (dominance informational), 130 passing after Phase 3 tuning when dominance blocking added

# 3. Harness — the command that proves AC1/AC2/AC4/AC6
uv run --project backend python backend/app/cli.py --balance --seeds 200 --seed-prefix harness --version 1.0
uv run --project backend python backend/app/cli.py --balance --seeds 200 --seed-prefix harness --version 1.0 --json-out /tmp/balance.json
cat /tmp/balance.json | python3 -m json.tool | head -100
# expected: markdown table with 5 policies, JSON config/aggregates/overall/per_seed, exit 0 if retuned economy passes, exit 2 if still dominant

# 4. Show the economy fix — drought felt even with no farm (new invariant)
uv run --project backend python -c "
from app.domain.types import GameState, PlayerState, InventoryState, MarketState, RouteState
from app.engine.pressure import PRESSURE_NORMAL, PRESSURE_DROUGHT
from app.engine.prototype import default_start_state
s=default_start_state(seed='demo',version='1.0')
# zero farm — player has no production
s2=s.model_copy(update={'player': s.player.model_copy(update={'farm_capacity': 0})})
from app.engine.turn import resolve_turn
rN=resolve_turn(s2, __import__('app.domain.types', fromlist=['PlayerCommand']).PlayerCommand(type='hold'), PRESSURE_NORMAL, s2.to_turn_context())
rD=resolve_turn(s2, __import__('app.domain.types', fromlist=['PlayerCommand']).PlayerCommand(type='hold'), PRESSURE_DROUGHT, s2.to_turn_context())
print('regional', rN.next_state.market.regional_output, 'supply N', rN.next_state.market.supply, 'price N', rN.next_state.market.current_price)
print('drought price D', rD.next_state.market.current_price, 'drought>normal?', rD.next_state.market.current_price > rN.next_state.market.current_price)
print('trace parents home_supply', [n for n in rD.causal_trace.nodes if n.id=='home_supply'][0].parent_ids)
print('regional_output node', [n for n in rD.causal_trace.nodes if n.id=='regional_output'][0].after)
"

# 5. Determinism double-run (AC5) — byte-identical
uv run --project backend python backend/app/cli.py --balance --seeds 100 --seed-prefix harness --json-out /tmp/a.json
uv run --project backend python backend/app/cli.py --balance --seeds 100 --seed-prefix harness --json-out /tmp/b.json
diff /tmp/a.json /tmp/b.json && echo "deterministic: identical"

# 6. Performance (AC1)
time uv run --project backend python backend/app/cli.py --balance --seeds 200 --seed-prefix perf  # <5s

# 7. Purity — engine/domain no web/DB/LLM
uv run --project backend pytest backend/tests/test_engine_purity.py -v

# 8. No bare-string shim (Section 8 guard)
grep -rn "resolve_turn" backend/app/engine/harness.py | grep -v "PRESSURE\|pressure_for" && echo "FAIL bare string" || echo "no bare string"
grep -rn '\"normal\"' backend/app/engine/harness.py | grep resolve_turn && echo FAIL || echo ok

# 9. Phase 3 tuning loop — run, read median ratio, adjust default_start_state regional_output/supply/demand, repeat until
#    max_median/second_max <1.60 and every median ≥0.70×overall and hold not dominant; report final table
uv run --project backend python backend/app/cli.py --balance --seeds 200 2>&1 | tee /tmp/final_balance.txt
cat /tmp/final_balance.txt

# 10. Freshness — pre-push
git status --short
graphify update .  # code-only
```

**Highest-risk validation:** Phase 3 tuning — the retuned constants must make `hold` not dominant while keeping all invariants (especially `drought price > normal` with `farm==0` via regional, and Section 8 warning-isolation equality with retuned numbers but still equality). Mitigated by running the new `test_regional_output_chain_truthful` invariant first.

---

## Risks / Rollback

- **Risk: Retuned constants still leave `hold` dominant.** Mitigation: Phase 3 is explicitly iterative; harness reports median ratio each run, so tuning is data-driven. If still dominant after reasonable search, report and escalate — do not loosen thresholds.
- **Risk: Updating expected numbers weakens a real invariant.** Mitigation: Every changed expectation must preserve the invariant shape (e.g. `==` stays `==`, `>` stays `>`); CI enforces same. Violations stop and report rather than adjust.
- **Risk: New field breaks frozen-model construction in old tests.** Mitigation: `regional_output` has a default, so existing `MarketState(supply=...)` constructions still work; new tests assert the field explicitly.
- **Rollback:** Revert `types.py` `regional_output` default, `turn.py` supply line + causal node, `prototype.py` constants, delete `harness.py` and `--balance` CLI block, `BUILD_SPEC.md` stays `NOT STARTED`.

---

## Grill — Headless Stress Test (Rev 2, answered from code/evidence, folded into plan)

**Q1 — Why one field `regional_output` rather than a market-share param or rival→supply feeding?**
*Recommended:* One field. *Answer:* Review settled it: lowest MVP complexity that makes drought truthful and fixes dominance. Market-share adds a second param to tune; rival→supply couples session-owned rivals into canonical `GameState.supply` (violates isolation invariants from Section 7) and adds cross-actor feedback before any contested-supply design exists. One field + one reused primitive is the minimal honest fix. **Settled.**

**Q2 — How to avoid a second drought formula?**
*Recommended:* Reuse `actor.DROUGHT_YIELD_REDUCTION_BPS` / `compute_farm_output` shape. *Answer:* `_regional_output_after_world = base*6000//10000` if drought else `base` — same 40% number, no duplicate constant. Grep guard: `turn.py` imports `DROUGHT_YIELD_REDUCTION_BPS` from `actor`, no literal `4000` second site. **Settled.**

**Q3 — What happens to existing equality assertions when supply numbers change?**
*Recommended:* Legitimate numeric updates, invariants preserved (Decision 11). *Answer:* `test_five_turn_prototype.py:101` expects `supply 110/70`; after regional (e.g. regional 360) the normal `next_supply = 100+360+100-90=470` vs drought `100+216+60-90=286` — update numbers, keep `drought < normal` and `price_drought > price_normal`. Section 8 warning-isolation test's `supply 100==100` / `price 4750==4750` pre-condition must be retuned to new equalities but the *equality itself* stays `==`, fully affordable, threshold-free. **Settled.**

**Q4 — Why delete the win-rate floor?**
*Recommended:* Delete per E6. *Answer:* Deterministic policies have win-rate ∈ {0,1} exactly on a fixed arc — a `≥0.05` floor is unsatisfiable by construction for 4 of 5 policies regardless of balance quality. Median ratio `≥0.70×overall` is well-defined under determinism (review already noted `production 548 vs median 1690` correctly flags dead). `win_rate` still computed and displayed, just not gated. **Settled.**

**Q5 — Why not land thresholds as blocking tests immediately?**
*Recommended:* Report first (exit 2), block only once economy passes (Decision 7). *Answer:* Review E4's pipeline: detection is working — harness correctly reports failure on first run. Landing a hard-failing `assert max_median/second <1.60` would force threshold-loosening to go green, violating `BUILD_SPEC §0.4`. The plan's own exit-2 report design is reused, then converted. **Settled.**

**ESCALATE (none blocking):** If Phase 3 tuning shows that fixing dominance requires changing `YIELD_PER_CAPACITY` or `EXPAND_FARM_COST`/`BUILD_GRANARY_COST` beyond start-state constants, that is a one-line `actor.py` tweak — report it, do not block on it.

---

## Open Questions

None — all implementation choices are settled. The only empirical work is Phase 3 tuning of `regional_output`/`supply`/`demand` (and if needed, costs) until the harness median-ratio gates pass. No unresolved implementation remains.

---

## What the Grill Changed (Rev 1 → Rev 2)

- **Added economy fix (Decision 5 + 6 + 11):** Replaced "detect only" with one-field `regional_output`, reused drought primitive, new supply formula `signal+regional_after+farm-demand`, `regional_output` causal nodes, retuned `default_start_state` for 15–25% player share and stable normal signal, with explicit legitimate-vs-forbidden test-update rule.
- **Deleted Decision 4 (±2 perturbation):** Proved useless (0.3% movement, 18-config sweep `hold` wins 18/18) — removed, replaced with honest seed-invariant narrative (seed variation from `random_legal` only).
- **Replaced Decision 6 win-rate floor with median-ratio only:** `win_rate≥0.05` unsound under determinism (exactly 0 or 1) — deleted, kept `median≥0.70×overall` + `max_median/second<1.60` (now reported first).
- **Made thresholds report-first (Decision 7):** Prevent BUILD_SPEC §0.4 violation — harness exits 2 on breach first, converts to blocking only once economy actually passes.
- **Made existing-test handling explicit (Decision 11):** Legitimate numeric updates vs forbidden deletions/loosenings, with every invariant (drought>normal, non-negativity, determinism, wealth exact, `pressure_stage->world->regional_output/farm_output->home_supply->home_price`, no direct edge, warning-isolation equality) staying asserted.

---

## Fit to Stack & Hosting

- Python 3.12, Pydantic v2, `uv`, `ruff`/`pyright` strict — no new deps.
- No Postgres/Render — in-memory until Section 16.
- No frontend — mobile UI in Section 11.

---

## Implementation Authority

This plan (Rev 2) is the authority for Section 9. Build exactly the files and tests in Work Plan 1–9, using `PRESSURE_NORMAL`/`PRESSURE_DROUGHT`/`pressure_for_world`/`PRESSURE_ARC` for every `resolve_turn` caller, honoring determinism/pure-engine rules and the review's settled regional_output design. Stop at Section 9 — do not start Section 10.
