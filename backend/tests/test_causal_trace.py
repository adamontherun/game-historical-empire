"""Section 4 — causal trace hardening, exact wealth decomposition, and story drivers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.trace import CausalNode, CausalTrace
from app.domain.types import (
    GameState,
    InventoryState,
    MarketState,
    PlayerCommand,
    PlayerState,
    TurnContext,
)
from app.engine.turn import TURN_ORDER, resolve_turn


def _base_state(
    cash: int = 1000,
    grain: int = 20,
    farm: int = 10,
    storage: int = 100,
    supply: int = 100,
    demand: int = 120,
    base_price: int = 5000,
    current_price: int = 5000,
    turn: int = 0,
    seed: str = "seed-001",
    version: str = "1.0",
) -> GameState:
    return GameState(
        turn=turn,
        run_seed=seed,
        ruleset_version=version,
        player=PlayerState(
            cash=cash,
            inventory=InventoryState(grain=grain),
            farm_capacity=farm,
            storage_capacity=storage,
        ),
        market=MarketState(
            supply=supply, demand=demand, base_price=base_price, current_price=current_price
        ),
    )


def test_every_important_node_has_parent_including_valuation() -> None:
    """AC #1: every important mutated node has parents, including valuation subgraph."""
    for cmd_type in ("hold", "expand_farm", "build_granary", "buy_grain"):
        for world in ("normal", "drought"):
            state = _base_state()
            qty = 5 if cmd_type == "buy_grain" else None
            cmd = PlayerCommand(type=cmd_type, quantity=qty)  # type: ignore[arg-type]
            res = resolve_turn(state, cmd, world, state.to_turn_context())  # type: ignore[arg-type]
            ids = {n.id for n in res.causal_trace.nodes}
            # Core chain must exist
            for required in (
                "world",
                "farm_output",
                "supply",
                "price_pressure",
                "target_price",
                "price",
                "inventory",
                "quantity_value_effect",
                "price_value_effect",
                "wealth",
                "cash_after_command",
            ):
                assert required in ids, f"missing {required} for {cmd_type}/{world}"
            # Parents exist and are before child, and are tuples
            assert isinstance(res.causal_trace.nodes, tuple)
            for node in res.causal_trace.nodes:
                assert isinstance(node.parent_ids, tuple)
                # Allowed roots
                if node.id in ("world", "command"):
                    assert node.parent_ids == (), f"{node.id} should be root"
                    continue
                if node.id == "farm_capacity" and node.delta == 0:
                    assert node.parent_ids == ()
                    continue
                # All valuation nodes must have parents
                if node.id in ("quantity_value_effect", "price_value_effect", "wealth"):
                    assert len(node.parent_ids) > 0
                if node.id == "quantity_value_effect":
                    assert "inventory" in node.parent_ids
                    assert "price" in node.parent_ids
                if node.id == "price_value_effect":
                    assert "inventory" in node.parent_ids
                    assert "price" in node.parent_ids
                if node.id == "wealth":
                    assert "quantity_value_effect" in node.parent_ids
                    assert "price_value_effect" in node.parent_ids
                    assert "cash_effect" in node.parent_ids
            # Parents before children
            pos = {n.id: i for i, n in enumerate(res.causal_trace.nodes)}
            for node in res.causal_trace.nodes:
                for pid in node.parent_ids:
                    assert pid in pos, f"parent {pid} missing for {node.id}"
                    assert pos[pid] < pos[node.id]


def test_trace_immutable_tuples() -> None:
    state = _base_state()
    res = resolve_turn(state, PlayerCommand(type="hold"), "normal", state.to_turn_context())
    assert isinstance(res.causal_trace.nodes, tuple)
    assert isinstance(res.domain_effects, tuple)
    assert isinstance(res.player_outcome.drivers, tuple)
    for node in res.causal_trace.nodes:
        assert isinstance(node.parent_ids, tuple)
    # Attempt to mutate should fail (frozen + tuple)
    with pytest.raises((AttributeError, TypeError, ValidationError)):
        res.causal_trace.nodes.append(  # type: ignore[attr-defined]
            CausalNode(
                id="bogus",
                label="bogus",
                kind="price",
                before=1,
                after=2,
                delta=1,
                reason_code="bogus",
                parent_ids=(),
            )
        )
    # Tuple has no append; node parent_ids is tuple
    node = res.causal_trace.nodes[0]
    with pytest.raises(AttributeError):
        node.parent_ids.append("bogus")  # type: ignore[attr-defined]


def test_wealth_decomposition_exact() -> None:
    """Wealth delta must equal cash + quantity + price effects exactly."""
    for world in ("normal", "drought"):
        for cmd_type in ("hold", "expand_farm", "build_granary", "buy_grain"):
            state = _base_state(cash=1000, grain=20, farm=10, storage=100)
            qty = 10 if cmd_type == "buy_grain" else None
            cmd = PlayerCommand(type=cmd_type, quantity=qty)  # type: ignore[arg-type]
            res = resolve_turn(state, cmd, world, state.to_turn_context())  # type: ignore[arg-type]
            # Extract valuation effects
            eff = {e.metric: e for e in res.domain_effects}
            assert "quantity_value_effect" in eff
            assert "price_value_effect" in eff
            assert "cash_effect" in eff
            assert "wealth" in eff
            # Check exact sum
            wealth_delta = eff["wealth"].delta
            assert (
                wealth_delta
                == eff["cash_effect"].delta
                + eff["quantity_value_effect"].delta
                + eff["price_value_effect"].delta
            ), f"wealth decomposition failed for {cmd_type}/{world}"
            # Also check wealth node matches
            wealth_node = next(n for n in res.causal_trace.nodes if n.id == "wealth")
            assert wealth_node.delta == wealth_delta
            assert wealth_node.before is not None and wealth_node.after is not None
            # Drivers sum should be ≤ wealth_delta magnitude but with exact partition, sum of all drivers (≤3) may be subset
            # Instead check that drivers' impact sum plus discarded zeros still allows exact check via effects
            # Verify that every driver's impact corresponds to one of the three effects
            for d in res.player_outcome.drivers:
                assert (
                    d.impact_money
                    in (
                        eff["cash_effect"].delta,
                        eff["quantity_value_effect"].delta,
                        eff["price_value_effect"].delta,
                    )
                    or d.impact_money == eff["wealth"].delta
                )  # allow wealth direct if needed


def test_wealth_graph_parents() -> None:
    state = _base_state()
    res = resolve_turn(state, PlayerCommand(type="hold"), "normal", state.to_turn_context())
    q = next(n for n in res.causal_trace.nodes if n.id == "quantity_value_effect")
    p = next(n for n in res.causal_trace.nodes if n.id == "price_value_effect")
    w = next(n for n in res.causal_trace.nodes if n.id == "wealth")
    assert set(q.parent_ids) == {"inventory", "price"}
    assert set(p.parent_ids) == {"inventory", "price"}
    assert set(w.parent_ids) == {"cash_effect", "quantity_value_effect", "price_value_effect"}
    # Edges derived
    assert ("inventory", "quantity_value_effect") in res.causal_trace.edges
    assert ("price", "price_value_effect") in res.causal_trace.edges
    assert ("quantity_value_effect", "wealth") in res.causal_trace.edges


def test_drivers_derived_from_trace_not_snapshot() -> None:
    """Drivers must reference trace nodes, not snapshot diff."""
    state = _base_state(cash=500, grain=25, storage=30, farm=0, current_price=5000)
    # Storage 30, grain 25 => space 5, request 20 => clamped to 5
    cmd = PlayerCommand(type="buy_grain", quantity=20)
    res = resolve_turn(state, cmd, "normal", state.to_turn_context())
    # Buy was storage-limited
    buy_node = next(n for n in res.causal_trace.nodes if n.id == "inventory_after_buy")
    assert buy_node.reason_code == "insufficient_storage"
    # At least one driver should reference the buy path if cash_effect is non-zero
    # Drivers are exact partitions; buy cost is cash_effect driver
    if res.player_outcome.drivers:
        for d in res.player_outcome.drivers:
            # Each driver must have causal_node_ids subset of trace ids
            trace_ids = {n.id for n in res.causal_trace.nodes}
            for cid in d.causal_node_ids:
                assert cid in trace_ids
            # Reason code should match trace or be derived
            assert isinstance(d.reason_code, str) and len(d.reason_code) > 0
    # Snapshot diff would just see inventory +5 and cash -25, but trace knows why (storage)
    # Ensure quantity_value_effect reflects capped inventory
    q = next(n for n in res.causal_trace.nodes if n.id == "quantity_value_effect")
    # With farm 0, inventory change is only buy 5, so quantity effect should be 5 * price_before //1000
    # price_before 5000 => 5*5000//1000=25
    assert q.delta == 25


def test_driver_ranking_deterministic_exact_wealth_bps() -> None:
    state = _base_state(cash=1000, grain=20, farm=10, storage=100)
    cmd = PlayerCommand(type="expand_farm")
    ctx = state.to_turn_context()
    r1 = resolve_turn(state, cmd, "drought", ctx)
    r2 = resolve_turn(state, cmd, "drought", ctx)
    assert r1.player_outcome.drivers == r2.player_outcome.drivers
    # Also ensure ranking is by wealth-bps desc, id asc
    for drivers in [r1.player_outcome.drivers]:
        for i in range(len(drivers) - 1):
            a = drivers[i]
            b = drivers[i + 1]
            # Either higher bps, or equal bps and id order
            if a.impact_bps == b.impact_bps:
                assert a.id < b.id
            else:
                assert a.impact_bps > b.impact_bps
    # Check that impact_bps is computed as abs(impact)*10000//wealth_before
    # wealth_before for base state: cash 1000 + grain 20*5000//1000=100 => 1100
    # So a driver with impact 500 should have bps ~4545
    # We don't hardcode, just check formula holds for one driver
    if r1.player_outcome.drivers:
        d = r1.player_outcome.drivers[0]
        # Recompute expected bps via same formula
        # wealth_before is world cash_before + value_before
        # We can extract from wealth node
        wealth_node = next(n for n in r1.causal_trace.nodes if n.id == "wealth")
        wealth_before = wealth_node.before
        assert wealth_before is not None
        expected_bps = abs(d.impact_money) * 10_000 // max(wealth_before, 1)
        assert d.impact_bps == expected_bps


def test_story_drivers_are_paths_and_filtered() -> None:
    """Drivers must be causal paths, not single nodes, and zero-impact stories discarded."""
    # Hold with no price change? Use high supply to keep price stable
    state = _base_state(
        cash=1000,
        grain=20,
        farm=5,
        storage=100,
        supply=100,
        demand=100,
        current_price=5000,
        base_price=5000,
    )
    # With supply==demand, price pressure 0, target==base, bounded may be 0 delta
    res = resolve_turn(state, PlayerCommand(type="hold"), "normal", state.to_turn_context())
    # Drivers should be ≤3 and each should have path length >=2 or at least 2 nodes for price story
    assert len(res.player_outcome.drivers) <= 3
    for d in res.player_outcome.drivers:
        assert len(d.causal_node_ids) >= 2, f"driver {d.id} should be a path"
        assert d.impact_money != 0, "zero-impact stories should be discarded"
        assert d.impact_bps > 0
    # At least one driver should be a multi-node price chain if price moved
    # For this state, price may not move, so quantity driver may be present
    # Test a more volatile case where price does move
    state2 = _base_state(
        cash=1000, grain=20, farm=10, storage=100, supply=10, demand=120, current_price=5000
    )
    res2 = resolve_turn(state2, PlayerCommand(type="hold"), "normal", state2.to_turn_context())
    assert len(res2.player_outcome.drivers) <= 3
    # Price revaluation should have long path
    price_drivers = [d for d in res2.player_outcome.drivers if d.id == "price_revaluation"]
    if price_drivers:
        assert len(price_drivers[0].causal_node_ids) >= 3


def test_trace_validates_dag_and_allowed_roots() -> None:
    # Forward parent reference should raise
    with pytest.raises(ValidationError):
        CausalTrace(
            nodes=(
                CausalNode(
                    id="a",
                    label="a",
                    kind="price",
                    before=1,
                    after=2,
                    delta=1,
                    reason_code="x",
                    parent_ids=("b",),
                ),
                CausalNode(
                    id="b",
                    label="b",
                    kind="price",
                    before=1,
                    after=2,
                    delta=1,
                    reason_code="x",
                    parent_ids=(),
                ),
            )
        )
    # Duplicate id should raise
    with pytest.raises(ValidationError):
        CausalTrace(
            nodes=(
                CausalNode(
                    id="a",
                    label="a",
                    kind="world",
                    before=None,
                    after=None,
                    delta=None,
                    reason_code="x",
                    parent_ids=(),
                ),
                CausalNode(
                    id="a",
                    label="a2",
                    kind="world",
                    before=None,
                    after=None,
                    delta=None,
                    reason_code="x",
                    parent_ids=(),
                ),
            )
        )
    # command with non-zero delta and empty parents is allowed (authored root)
    ct = CausalTrace(
        nodes=(
            CausalNode(
                id="world",
                label="w",
                kind="world",
                before=None,
                after=None,
                delta=None,
                reason_code="x",
                parent_ids=(),
            ),
            CausalNode(
                id="command",
                label="c",
                kind="command",
                before=0,
                after=10,
                delta=10,
                reason_code="x",
                parent_ids=(),
            ),
            CausalNode(
                id="cash_after_command",
                label="c",
                kind="cash",
                before=0,
                after=-5,
                delta=-5,
                reason_code="x",
                parent_ids=("command",),
            ),
        )
    )
    assert len(ct.nodes) == 3
    # farm_capacity with non-zero delta and empty parents should fail (must be child of command)
    with pytest.raises(ValidationError):
        CausalTrace(
            nodes=(
                CausalNode(
                    id="world",
                    label="w",
                    kind="world",
                    before=None,
                    after=None,
                    delta=None,
                    reason_code="x",
                    parent_ids=(),
                ),
                CausalNode(
                    id="command",
                    label="c",
                    kind="command",
                    before=0,
                    after=10,
                    delta=10,
                    reason_code="x",
                    parent_ids=(),
                ),
                CausalNode(
                    id="farm_capacity",
                    label="f",
                    kind="capacity",
                    before=10,
                    after=20,
                    delta=10,
                    reason_code="expand_farm",
                    parent_ids=(),
                ),
            )
        )
    # farm_capacity with zero delta and empty is allowed
    ct2 = CausalTrace(
        nodes=(
            CausalNode(
                id="world",
                label="w",
                kind="world",
                before=None,
                after=None,
                delta=None,
                reason_code="x",
                parent_ids=(),
            ),
            CausalNode(
                id="command",
                label="c",
                kind="command",
                before=0,
                after=0,
                delta=0,
                reason_code="hold",
                parent_ids=(),
            ),
            CausalNode(
                id="farm_capacity",
                label="f",
                kind="capacity",
                before=10,
                after=10,
                delta=0,
                reason_code="farm_capacity_unchanged",
                parent_ids=(),
            ),
        )
    )
    assert len(ct2.nodes) == 3


def test_rng_context_mismatch_raises() -> None:
    state = _base_state(turn=0, seed="seed-001", version="1.0")
    bad_ctx = TurnContext(turn=999, run_seed="seed-001", ruleset_version="1.0")
    with pytest.raises(ValueError, match="rng_context"):
        resolve_turn(state, PlayerCommand(type="hold"), "normal", bad_ctx)
    # Also wrong seed
    bad_ctx2 = TurnContext(turn=0, run_seed="other", ruleset_version="1.0")
    with pytest.raises(ValueError):
        resolve_turn(state, PlayerCommand(type="hold"), "normal", bad_ctx2)


def test_storage_capped_zero_quantity_effect() -> None:
    """If storage is full, quantity value effect should be zero and driver discarded."""
    # Storage exactly full before harvest: grain 100, storage 100, farm 10 => 100 output would exceed
    state = _base_state(cash=1000, grain=100, farm=10, storage=100, supply=100, demand=120)
    res = resolve_turn(state, PlayerCommand(type="hold"), "normal", state.to_turn_context())
    # Inventory should be capped at 100, so delta 0, quantity effect 0
    inv_node = next(n for n in res.causal_trace.nodes if n.id == "inventory")
    assert inv_node.after == 100
    assert inv_node.delta == 0
    q = next(n for n in res.causal_trace.nodes if n.id == "quantity_value_effect")
    assert q.delta == 0
    # Quantity driver should be absent (filtered)
    assert not any(d.id == "quantity_value" for d in res.player_outcome.drivers)
    # Price effect may still be present if price moved
    # wealth decomposition still exact
    eff = {e.metric: e for e in res.domain_effects}
    assert (
        eff["wealth"].delta
        == eff["cash_effect"].delta
        + eff["quantity_value_effect"].delta
        + eff["price_value_effect"].delta
    )


def test_turn_order_includes_valuation() -> None:
    assert TURN_ORDER == "command -> production -> supply -> price -> settlement -> valuation"
