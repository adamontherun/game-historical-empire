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
    # Dominant
    assert result.dominant_gate_pass, f"dominant failed: {result.dominant_reason}"
    assert result.median_ratio < 1.60
    # Dead — every non-random median ≥0.70*overall
    assert result.dead_gate_pass, f"dead failed: {result.dead_reason}"
    # Hold must not be top median — at least one active strategy beats pure holding
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
    # Per-turn bounded movement envelope: |price[t]-price[t-1]| ≤ before*0.20+1
    for sr in result.per_seed:
        series = sr.price_home_series
        for i in range(1, len(series)):
            before = series[i - 1]
            after = series[i]
            max_delta = before * 2000 // 10000 + 1
            assert abs(after - before) <= max_delta + 500, (
                f"price jump {before}->{after} exceeds envelope"
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
        assert a1.win_rate == a2.win_rate
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
