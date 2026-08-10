"""Section 9 — Balance harness acceptance tests.

Covers AC1-6 with confound-controlled dominance/dead checks (median-ratio only,
deterministic policies are seed-invariant — seed variation from random_legal only).
Thresholds are reported via harness exit 2, but these unit tests assert blocking
gates now that the economy has been tuned to pass (see plan Rev 2).
"""

from __future__ import annotations

import json
import pathlib

from app.domain.types import PlayerCommand
from app.engine.harness import BatchConfig, run_batch
from app.engine.pressure import PRESSURE_DROUGHT, PRESSURE_NORMAL
from app.engine.prototype import FiveTurnGame, default_start_state
from app.engine.turn import TURN_ORDER, resolve_turn


def test_harness_runs_hundreds_quickly() -> None:
    import time

    config = BatchConfig(seed_prefix="perf", n_seeds=40, version="1.0")
    start = time.time()
    result = run_batch(config)
    elapsed = time.time() - start
    assert len(result.per_seed) == 200  # 40*5
    assert elapsed < 5.0, f"200 games took {elapsed:.2f}s, expected <5s"


def test_no_dominant_or_dead_strategy_by_median_ratio() -> None:
    """AC2: no universally dominant (median_ratio <1.60) and no dead (median ≥0.70*overall).

    Plus hold-not-top: cash_preserving must not have highest median (game rewards action).
    Confound control: same seeds for every policy (paired), deterministic policies
    are seed-invariant so win_rate is 0/1 — median ratio is the honest test.
    Also asserts deterministic policies have no insufficient_* (legal by construction).
    """
    config = BatchConfig(seed_prefix="harness", n_seeds=40, version="1.0")
    result = run_batch(config)
    # Dominant — integer bps
    assert result.dominant_gate_pass, f"dominant failed: {result.dominant_reason}"
    assert result.median_ratio_bps < 16_000
    # Dead — every non-random median ≥0.70*overall
    assert result.dead_gate_pass, f"dead failed: {result.dead_reason}"
    # Hold must not be top median — at least two active archetypes beat hold by ≥5% material
    assert result.hold_not_top_gate_pass, f"hold_not_top failed: {result.hold_not_top_reason}"
    # Paired and affordable: no insufficient_* in deterministic histories
    # Check a single seed's deterministic policies for insufficient
    for pid in ("production_heavy", "storage_heavy", "trade_heavy", "cash_preserving"):
        # run one game and check trace
        from app.engine.harness import POLICY_FUNCS

        func = POLICY_FUNCS[pid]
        g = FiveTurnGame(seed="harness-0000", version="1.0")
        for idx in range(5):
            cmd = func(g.state, idx, "harness-0000", "1.0")
            res = g.submit(cmd)
            cmd_node = next(n for n in res.causal_trace.nodes if n.id == "command")
            assert "insufficient" not in cmd_node.reason_code, f"{pid} has {cmd_node.reason_code}"


def test_no_impossible_negative_state() -> None:
    config = BatchConfig(seed_prefix="negcheck", n_seeds=20, version="1.0")
    result = run_batch(config)
    assert not result.any_negative_state
    assert result.negativity_gate_pass
    # Exhaustive per-turn check on a few seeds
    for sr in result.per_seed[:10]:
        assert sr.final_cash >= 0
        assert sr.final_grain >= 0
        for p in sr.price_home_series + sr.price_river_series:
            assert p > 0


def test_price_ranges_within_deliberate_bounds() -> None:
    config = BatchConfig(seed_prefix="pricecheck", n_seeds=20, version="1.0")
    result = run_batch(config)
    assert result.price_gate_pass
    assert 2000 <= result.overall_price_min <= 9000
    assert 2000 <= result.overall_price_max <= 9000
    # Per-turn bounded movement envelope: exact engine rule from _bounded_price
    # Read max_movement_bps from state, not hard-coded 2000, and no +500 loosening
    state = default_start_state(seed="price-envelope", version="1.0")
    max_movement_bps = state.market.max_movement_bps
    for sr in result.per_seed:
        series = sr.price_home_series
        for i in range(1, len(series)):
            before = series[i - 1]
            after = series[i]
            max_delta = before * max_movement_bps // 10_000
            assert abs(after - before) <= max_delta, (
                f"price jump {before}->{after} exceeds envelope max_delta {max_delta} (before {before} * {max_movement_bps}//10000)"
            )


def test_largest_swing_bounded() -> None:
    config = BatchConfig(seed_prefix="swing", n_seeds=20, version="1.0")
    result = run_batch(config)
    assert result.global_max_swing <= 2500
    for sr in result.per_seed:
        # largest_swing should equal max abs wealth_delta across 5 turns
        # we trust harness, but check it is not huge
        assert sr.largest_swing <= 2500


def test_determinism_same_batch_identical() -> None:
    config = BatchConfig(seed_prefix="det", n_seeds=10, version="1.0")
    r1 = run_batch(config)
    r2 = run_batch(config)
    # JSON stable
    j1 = json.dumps(json.loads(r1.model_dump_json()), sort_keys=True)
    j2 = json.dumps(json.loads(r2.model_dump_json()), sort_keys=True)
    assert j1 == j2
    # Aggregates equal
    for a1, a2 in zip(r1.aggregates, r2.aggregates, strict=True):
        assert a1.median_wealth == a2.median_wealth
        assert a1.win_rate_bps == a2.win_rate_bps
    # Changing prefix changes at least one aggregate (sensitivity, via random_legal)
    config2 = BatchConfig(seed_prefix="det2", n_seeds=10, version="1.0")
    r3 = run_batch(config2)
    # At least random_legal should differ
    r1_rand = next(a for a in r1.aggregates if a.policy_id == "random_legal")
    r3_rand = next(a for a in r3.aggregates if a.policy_id == "random_legal")
    assert (
        r1_rand.median_wealth != r3_rand.median_wealth or r1_rand.mean_wealth != r3_rand.mean_wealth
    )


def test_harness_uses_pressure_not_bare_string() -> None:
    text = pathlib.Path("backend/app/engine/harness.py").read_text()
    # Must delegate via FiveTurnGame or use PRESSURE_* — but must not have bare string world
    assert "FiveTurnGame" in text or "PRESSURE" in text or "pressure_for" in text
    for line in text.splitlines():
        if "resolve_turn" in line and '"normal"' in line:
            raise AssertionError(f"bare string in harness: {line}")
        if "resolve_turn" in line and "'normal'" in line:
            raise AssertionError(f"bare string in harness: {line}")
        if "resolve_turn" in line and '"drought"' in line:
            raise AssertionError(f"bare string in harness: {line}")
        if "resolve_turn" in line and "'drought'" in line:
            raise AssertionError(f"bare string in harness: {line}")
    # Trace should contain pressure_stage with pressure: prefix
    g = FiveTurnGame(seed="pressure-check")
    g.run([PlayerCommand(type="hold") for _ in range(5)])
    for res in g.history:
        p_node = next(n for n in res.causal_trace.nodes if n.id == "pressure_stage")
        assert p_node.reason_code.startswith("pressure:")


def test_regional_output_chain_truthful() -> None:
    """New invariant: drought raises price even with farm_capacity=0 via regional."""
    state = default_start_state(seed="regional-truth", version="1.0")
    # Zero farm
    zero_farm = state.model_copy(
        update={"player": state.player.model_copy(update={"farm_capacity": 0})}
    )
    # Need to ensure regional_output is present
    assert zero_farm.market.regional_output > 0
    ctx = zero_farm.to_turn_context()
    rN = resolve_turn(zero_farm, PlayerCommand(type="hold"), PRESSURE_NORMAL, ctx)
    rD = resolve_turn(zero_farm, PlayerCommand(type="hold"), PRESSURE_DROUGHT, ctx)
    # Drought must not lower price; with bounded movement it may be equal when both hit cap,
    # but drought's underlying pressure/supply must be worse.
    assert rD.next_state.market.current_price >= rN.next_state.market.current_price, (
        f"drought price {rD.next_state.market.current_price} not >= normal {rN.next_state.market.current_price} with farm 0"
    )
    # Stronger: drought supply strictly lower, and regional output lower
    assert rD.next_state.market.supply < rN.next_state.market.supply
    rN_reg = next(n for n in rN.causal_trace.nodes if n.id == "regional_output")
    rD_reg = next(n for n in rD.causal_trace.nodes if n.id == "regional_output")
    assert rD_reg.after < rN_reg.after  # type: ignore[operator]
    # Trace: regional_output parented by world, home_supply parented by regional+farm
    for res in (rN, rD):
        assert "regional_output" in {n.id for n in res.causal_trace.nodes}
        ro = next(n for n in res.causal_trace.nodes if n.id == "regional_output")
        assert "world" in ro.parent_ids
        hs = next(n for n in res.causal_trace.nodes if n.id == "home_supply")
        assert "regional_output" in hs.parent_ids
        assert "farm_output" in hs.parent_ids
    # TURN_ORDER includes regional_output
    assert "regional_output" in TURN_ORDER


def test_build_granary_not_worthless() -> None:
    """Regression: starting storage must be scarce enough that granary matters.

    Idle player accumulates start_grain + farm*YIELD*5 over the game. If starting
    storage already exceeds that, build_granary (+50 cap for 300 cash) is a pure
    cash burn with zero marginal value — storage_heavy's defining move is
    worthless and hold will dominate. This invariant silently broke at 400.
    Cheap necessary condition; sufficiency is checked by matched control below.
    """
    from app.engine.actor import YIELD_PER_CAPACITY

    state = default_start_state(seed="granary-test", version="1.0")
    start_grain = state.player.inventory.grain
    farm_cap = state.player.farm_capacity
    storage = state.player.storage_capacity
    max_idle = start_grain + farm_cap * YIELD_PER_CAPACITY * 5
    assert storage < max_idle, (
        f"storage {storage} >= idle accumulation {max_idle} "
        f"(start {start_grain} + farm {farm_cap}*{YIELD_PER_CAPACITY}*5) — "
        "granary worthless, storage strategy dead by construction"
    )


def test_granary_incremental_matched_control() -> None:
    """Matched control: policy_storage_heavy must beat itself with build_granary suppressed.

    Runs the identical policy with that single command suppressed and compares median
    wealth. This is the sufficient check that the headroom assertion above cannot see:
    at shipped constants the granary was -21 on 300 cost (-7%) with the strawman policy,
    flipped to +56 with the fixed policy and no constant tuning.
    """
    from app.engine.actor import YIELD_PER_CAPACITY
    from app.engine.harness import POLICY_FUNCS

    def policy_no_granary(state, turn_idx, seed, version):  # type: ignore[no-untyped-def]
        # Identical to storage_heavy but never builds: if it would build, hold instead
        harvest = state.player.farm_capacity * YIELD_PER_CAPACITY
        # Check if original would build
        would_build = (
            turn_idx < 4
            and state.player.inventory.grain + harvest > state.player.storage_capacity
            and state.player.cash >= 300
        )
        if would_build:
            # suppressed: hold instead of build
            # Still allow buy logic as in original (headroom)
            headroom = state.player.storage_capacity - (state.player.inventory.grain + harvest)
            if headroom > 0 and turn_idx in (1, 2):
                price = state.market.current_price
                max_affordable = ((state.player.cash + 1) * 1000 - 1) // price if price > 0 else 0
                target = min(headroom, max_affordable)
                actual = min(target, 80) if target > 10 else target
                if actual > 0:
                    return PlayerCommand(type="buy_grain", quantity=actual)
            if turn_idx == 4 and state.player.inventory.grain > 0:
                return PlayerCommand(
                    type="sell_grain", quantity=min(state.player.inventory.grain, 150)
                )
            return PlayerCommand(type="hold")
        # otherwise delegate to real policy
        return POLICY_FUNCS["storage_heavy"](state, turn_idx, seed, version)

    # Quick headroom check already done above; now matched control
    # Run both across a batch and compare medians
    from app.engine.prototype import FiveTurnGame

    diffs: list[int] = []
    for i in range(40):
        seed = f"harness-{i:04d}"
        g_with = FiveTurnGame(seed=seed, version="1.0")
        g_without = FiveTurnGame(seed=seed, version="1.0")
        for idx in range(5):
            g_with.submit(POLICY_FUNCS["storage_heavy"](g_with.state, idx, seed, "1.0"))
            g_without.submit(policy_no_granary(g_without.state, idx, seed, "1.0"))
        diffs.append(g_with.summary().final_wealth - g_without.summary().final_wealth)
    median_diff = sorted(diffs)[len(diffs) // 2]
    assert median_diff > 0, (
        f"granary does not repay: median incremental {median_diff} <=0 "
        f"(storage_heavy vs itself with build suppressed, n=40)"
    )
    # Also check harness's aggregated report finds same (if available)
    # Run via harness to ensure consistent
    config = BatchConfig(seed_prefix="harness", n_seeds=20, version="1.0")
    result = run_batch(config)
    # storage should be top or near top and beat hold by >=5% material
    hold = next(a.median_wealth for a in result.aggregates if a.policy_id == "cash_preserving")
    stor = next(a.median_wealth for a in result.aggregates if a.policy_id == "storage_heavy")
    assert stor * 10_000 >= hold * 10_500, f"storage {stor} not >= hold {hold} *1.05"


def test_route_can_repay_establishment_cost() -> None:
    """Matched control: policy_trade_heavy must beat itself with secure_route suppressed.

    Also checks harness's route incremental reporting: trade vs trade_without_route
    must be positive, otherwise secure_route is a trap (strictly negative under
    every line of play). This invariant violated at cap 20 / cost 800 before fix.
    Route at 20/300 repays +174 on 400 cost (43.5%); 60 gives +280 but strains
    price-taking approximation, so 20 is kept.
    """

    from app.engine.harness import POLICY_FUNCS

    def policy_no_route(state, turn_idx, seed, version):  # type: ignore[no-untyped-def]
        # Identical to trade_heavy but never secures route
        if state.route.established and state.player.inventory.grain > 0:
            margin = (
                state.river_market.current_price
                - state.route.transport_cost_per_unit
                - state.market.current_price
            )
            if margin > 0:
                cost_per = state.route.transport_cost_per_unit
                affordable = (
                    ((state.player.cash + 1) * 1000 - 1) // cost_per
                    if cost_per > 0
                    else state.player.inventory.grain
                )
                ship_qty = min(state.player.inventory.grain, state.route.capacity, affordable)
                if ship_qty > 0:
                    return PlayerCommand(type="ship_grain", quantity=ship_qty)
        if turn_idx in (1, 2):
            price = state.market.current_price
            space = state.player.storage_capacity - state.player.inventory.grain
            if space > 0 and price > 0:
                max_affordable = ((state.player.cash + 1) * 1000 - 1) // price if price > 0 else 0
                target = min(space, max_affordable)
                actual = min(target, 80) if target > 10 else target
                if actual > 0:
                    return PlayerCommand(type="buy_grain", quantity=actual)
            return PlayerCommand(type="hold")
        if turn_idx == 4 and state.player.inventory.grain > 0:
            return PlayerCommand(type="sell_grain", quantity=min(state.player.inventory.grain, 80))
        return PlayerCommand(type="hold")

    from app.engine.prototype import FiveTurnGame

    diffs: list[int] = []
    for i in range(40):
        seed = f"harness-{i:04d}"
        g_with = FiveTurnGame(seed=seed, version="1.0")
        g_without = FiveTurnGame(seed=seed, version="1.0")
        for idx in range(5):
            g_with.submit(POLICY_FUNCS["trade_heavy"](g_with.state, idx, seed, "1.0"))
            g_without.submit(policy_no_route(g_without.state, idx, seed, "1.0"))
        diffs.append(g_with.summary().final_wealth - g_without.summary().final_wealth)
    median_diff = sorted(diffs)[len(diffs) // 2]
    assert median_diff > 0, (
        f"route does not repay: median incremental {median_diff} <=0 "
        f"(trade_heavy vs itself with secure_route suppressed, n=40)"
    )
    # Also verify harness reports same via its incremental fields
    config = BatchConfig(seed_prefix="harness", n_seeds=20, version="1.0")
    result = run_batch(config)
    assert result.route_incremental_value > 0, (
        f"harness route_incremental {result.route_incremental_value} <=0 "
        f"(trade {result.trade_wealth} vs without {result.trade_without_route_wealth})"
    )
    assert result.route_incremental_value_bps_of_cost > 0
    # Trade should be weakest of the three active but still > hold by 5%
    hold = next(a.median_wealth for a in result.aggregates if a.policy_id == "cash_preserving")
    trade = next(a.median_wealth for a in result.aggregates if a.policy_id == "trade_heavy")
    assert trade * 10_000 >= hold * 10_500, f"trade {trade} not >= hold {hold}*1.05"
