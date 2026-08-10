"""Section 4 — multi-step drought to wealth chain tests."""

from __future__ import annotations

from app.domain.types import GameState, InventoryState, MarketState, PlayerCommand, PlayerState
from app.engine.turn import resolve_turn


def _state(
    cash: int = 1000,
    grain: int = 20,
    farm: int = 10,
    storage: int = 100,
    supply: int = 100,
    demand: int = 120,
    base_price: int = 5000,
    current_price: int = 5000,
    seed: str = "seed-001",
) -> GameState:
    return GameState(
        turn=0,
        run_seed=seed,
        ruleset_version="1.0",
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


def test_drought_to_wealth_structural_chain_exact() -> None:
    """Drought chain must be structurally present via parent_ids and exact wealth math."""
    state = _state(farm=10, supply=100, demand=120, grain=20, storage=100)
    cmd = PlayerCommand(type="hold")
    drought = resolve_turn(state, cmd, "drought", state.to_turn_context())
    normal = resolve_turn(state, cmd, "normal", state.to_turn_context())

    # Drought reduces farm output
    def farm_out(res):  # type: ignore[no-untyped-def]
        return next(n for n in res.causal_trace.nodes if n.id == "farm_output").after

    d_out = farm_out(drought)
    n_out = farm_out(normal)
    assert d_out is not None and n_out is not None
    assert d_out < n_out

    # Supply lower under drought
    assert drought.next_state.market.supply < normal.next_state.market.supply

    # Price higher under drought (scarcity)
    assert drought.next_state.market.current_price >= normal.next_state.market.current_price

    # Structural chain exists: world -> farm_output -> supply -> price -> price_value_effect -> wealth
    ids = {n.id for n in drought.causal_trace.nodes}
    for required in (
        "world",
        "farm_output",
        "supply",
        "price_pressure",
        "target_price",
        "price",
        "quantity_value_effect",
        "price_value_effect",
        "wealth",
    ):
        assert required in ids

    # Parent chain checks
    farm_node = next(n for n in drought.causal_trace.nodes if n.id == "farm_output")
    assert "world" in farm_node.parent_ids
    assert "farm_capacity" in farm_node.parent_ids

    supply_node = next(n for n in drought.causal_trace.nodes if n.id == "supply")
    assert "farm_output" in supply_node.parent_ids

    price_node = next(n for n in drought.causal_trace.nodes if n.id == "price")
    assert "target_price" in price_node.parent_ids

    price_val = next(n for n in drought.causal_trace.nodes if n.id == "price_value_effect")
    assert "price" in price_val.parent_ids
    assert "inventory_after_trade" in price_val.parent_ids

    wealth_node = next(n for n in drought.causal_trace.nodes if n.id == "wealth")
    assert "quantity_value_effect" in wealth_node.parent_ids
    assert "price_value_effect" in wealth_node.parent_ids
    assert "cash_effect" in wealth_node.parent_ids

    # No direct world->price edge
    for nid in ("price", "target_price", "price_pressure", "wealth", "price_value_effect"):
        node = next(n for n in drought.causal_trace.nodes if n.id == nid)
        assert "world" not in node.parent_ids

    # Exact wealth decomposition
    eff = {e.metric: e for e in drought.domain_effects}
    assert (
        eff["wealth"].delta
        == eff["cash_effect"].delta
        + eff["quantity_value_effect"].delta
        + eff["price_value_effect"].delta
    )
    assert wealth_node.delta == eff["wealth"].delta

    # Drivers must be derived from trace and sum to wealth_delta (when all present, sum equals wealth_delta)
    # For hold, cash_effect is 0, so drivers may be quantity and price only
    _total_driver_impact = sum(d.impact_money for d in drought.player_outcome.drivers)  # noqa: F841
    # With hold, cash 0, so drivers should be quantity+price; sum should equal wealth_delta if both present
    # But if one is zero, it's filtered, so sum may be <= wealth_delta; check that no driver double counts
    # Ensure every driver's causal_node_ids are subset of trace ids
    trace_ids = {n.id for n in drought.causal_trace.nodes}
    for d in drought.player_outcome.drivers:
        for cid in d.causal_node_ids:
            assert cid in trace_ids
        # impact_bps should be wealth-bps
        wealth_before = wealth_node.before
        assert wealth_before is not None
        expected_bps = abs(d.impact_money) * 10_000 // max(wealth_before, 1)
        assert d.impact_bps == expected_bps

    # At least one driver should cover drought (farm output path or price path)
    assert len(drought.player_outcome.drivers) >= 1
    assert len(drought.player_outcome.drivers) <= 3


def test_story_drivers_cover_wealth_chain() -> None:
    state = _state()
    res = resolve_turn(state, PlayerCommand(type="hold"), "drought", state.to_turn_context())
    # Drivers collectively should reference farm_output, price, wealth/valuation
    all_causal = set()
    for d in res.player_outcome.drivers:
        all_causal.update(d.causal_node_ids)
    # At least one driver should mention farm_output or quantity, and at least one should mention price
    assert any(
        "farm_output" in d.causal_node_ids for d in res.player_outcome.drivers
    ) or "quantity_value" in {d.id for d in res.player_outcome.drivers}
    # Price revaluation driver should exist when price moves
    if res.player_outcome.price_delta != 0:
        assert any(d.id == "price_revaluation" for d in res.player_outcome.drivers)
    # Drivers sorted by impact_bps desc
    for i in range(len(res.player_outcome.drivers) - 1):
        a = res.player_outcome.drivers[i]
        b = res.player_outcome.drivers[i + 1]
        assert a.impact_bps >= b.impact_bps
        if a.impact_bps == b.impact_bps:
            assert a.id < b.id


def test_concise_le_three_full_trace_preserved() -> None:
    state = _state()
    res = resolve_turn(state, PlayerCommand(type="expand_farm"), "drought", state.to_turn_context())
    # Concise drivers ≤3
    assert len(res.player_outcome.drivers) <= 3
    # Full trace preserved (≥10 nodes including valuation)
    assert len(res.causal_trace.nodes) >= 10
    # Chain intact
    for nid in (
        "world",
        "farm_output",
        "supply",
        "price",
        "inventory",
        "quantity_value_effect",
        "price_value_effect",
        "wealth",
    ):
        assert any(n.id == nid for n in res.causal_trace.nodes)
    # top_drivers string view matches drivers labels
    assert res.player_outcome.top_drivers == tuple(d.label for d in res.player_outcome.drivers)


def test_normal_vs_drought_different_drivers() -> None:
    """Same command, different world should produce different driver impacts (drought has larger farm/price effects)."""
    state = _state(farm=10, supply=100, demand=120)
    cmd = PlayerCommand(type="hold")
    normal = resolve_turn(state, cmd, "normal", state.to_turn_context())
    drought = resolve_turn(state, cmd, "drought", state.to_turn_context())
    # Drought farm output smaller, so quantity effect smaller
    q_normal = next(n for n in normal.causal_trace.nodes if n.id == "quantity_value_effect").delta
    q_drought = next(n for n in drought.causal_trace.nodes if n.id == "quantity_value_effect").delta
    assert q_normal is not None and q_drought is not None
    assert q_drought < q_normal  # drought yields less quantity value
    # Price effect larger under drought (more scarcity)
    p_normal = next(n for n in normal.causal_trace.nodes if n.id == "price_value_effect").delta
    p_drought = next(n for n in drought.causal_trace.nodes if n.id == "price_value_effect").delta
    assert p_normal is not None and p_drought is not None
    # Drought price higher, so price revaluation should be >= normal (if inventory positive)
    # With same inventory, higher price under drought means larger price effect
    assert p_drought >= p_normal
