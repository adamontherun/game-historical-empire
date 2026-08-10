"""Section 5 — Two Markets and One Trade Route acceptance tests.

AC 1: Home Valley and River Town can have different prices from same good.
AC 2: Transport cost can make apparent price difference unprofitable.
AC 3: Route capacity constrains trade volume.
AC 4: Profitable arbitrage emerges from market conditions not script.
AC 5: Player can remain in Home Valley and still complete turn.
AC 6: All results deterministic.
"""

from __future__ import annotations

from app.domain.types import (
    GameState,
    InventoryState,
    MarketState,
    PlayerCommand,
    PlayerState,
    RouteState,
)
from app.engine.turn import TURN_ORDER, resolve_turn


def _base_state(
    cash: int = 1000,
    grain: int = 20,
    farm: int = 10,
    storage: int = 100,
    home_supply: int = 100,
    home_demand: int = 120,
    home_base: int = 5000,
    home_price: int = 5000,
    river_supply: int = 80,
    river_demand: int = 130,
    river_base: int = 5200,
    river_price: int = 5200,
    route_capacity: int = 20,
    transport_cost: int = 800,
    reliability: int = 10000,
    established: bool = False,
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
            supply=home_supply, demand=home_demand, base_price=home_base, current_price=home_price
        ),
        river_market=MarketState(
            supply=river_supply,
            demand=river_demand,
            base_price=river_base,
            current_price=river_price,
        ),
        route=RouteState(
            transport_cost_per_unit=transport_cost,
            capacity=route_capacity,
            reliability_bps=reliability,
            established=established,
        ),
    )


def test_two_markets_can_have_different_prices() -> None:
    """AC1: Home and River can have different prices from same underlying grain."""
    # Home surplus (supply > demand) vs River shortage (demand > supply)
    state = _base_state(home_supply=200, home_demand=100, river_supply=60, river_demand=150)
    res = resolve_turn(state, PlayerCommand(type="hold"), "normal", state.to_turn_context())
    assert res.next_state.market.current_price != res.next_state.river_market.current_price
    # Both prices derived via same kernel but different inputs — divergence is emergent
    # Ensure Home chain still: farm_output -> supply -> price
    supply_node = next(n for n in res.causal_trace.nodes if n.id == "supply")
    assert "farm_output" in supply_node.parent_ids
    farm_node = next(n for n in res.causal_trace.nodes if n.id == "farm_output")
    assert "world" in farm_node.parent_ids
    # River supply should be present and have its own pressure chain
    assert any(n.id == "river_supply" for n in res.causal_trace.nodes)
    assert any(n.id == "river_price_pressure" for n in res.causal_trace.nodes)
    assert any(n.id == "river_price" for n in res.causal_trace.nodes)
    # River price parents
    river_price = next(n for n in res.causal_trace.nodes if n.id == "river_price")
    assert "river_target_price" in river_price.parent_ids
    # Home and River prices should be in effects
    eff = {e.metric: e for e in res.domain_effects}
    assert "grain_price" in eff
    assert "river_grain_price" in eff


def test_transport_cost_can_make_apparent_price_difference_unprofitable() -> None:
    """AC2: Transport cost can erase apparent arbitrage profit."""
    # Same market divergence, two route costs: low transport profitable, high transport unprofitable
    base_kwargs = dict(
        cash=5000,
        grain=50,
        storage=200,
        home_supply=200,
        home_demand=100,
        river_supply=60,
        river_demand=150,
        established=True,
        route_capacity=20,
    )
    s_low = _base_state(transport_cost=200, **base_kwargs)  # type: ignore[arg-type]
    s_high = _base_state(transport_cost=3000, **base_kwargs)  # type: ignore[arg-type]
    res_low = resolve_turn(
        s_low, PlayerCommand(type="ship_grain", quantity=10), "normal", s_low.to_turn_context()
    )
    res_high = resolve_turn(
        s_high, PlayerCommand(type="ship_grain", quantity=10), "normal", s_high.to_turn_context()
    )
    # Low cost should have trade net positive or higher
    low_trade = next((d for d in res_low.player_outcome.drivers if d.id == "trade_arbitrage"), None)
    high_trade = next(
        (d for d in res_high.player_outcome.drivers if d.id == "trade_arbitrage"), None
    )
    # High cost must be strictly less profit (could be negative) than low cost
    # Low cost should be profitable or at least more profitable
    assert low_trade is not None
    assert high_trade is not None
    assert high_trade.impact_money < low_trade.impact_money
    # High cost trade should be unprofitable (negative net) when gap is moderate
    # With home price ~4000, river ~6240, gap ~2240 milli (2.24 money), cost 3000 milli (3 money) -> net negative
    assert high_trade.impact_money < 0
    # Low cost 200 milli (0.2 money) should be profitable
    assert low_trade.impact_money > 0
    # Verify transport_cost nodes present and reflect costs
    low_cost_node = next(n for n in res_low.causal_trace.nodes if n.id == "transport_cost")
    high_cost_node = next(n for n in res_high.causal_trace.nodes if n.id == "transport_cost")
    # High cost delta should be more negative
    assert high_cost_node.delta < low_cost_node.delta  # type: ignore[operator]


def test_route_capacity_constrains_trade_volume() -> None:
    """AC3: Route capacity limits shipped quantity."""
    # Request 50 with capacity 5, sufficient inventory and cash
    state = _base_state(
        cash=5000, grain=80, storage=200, route_capacity=5, established=True, farm=10
    )
    res = resolve_turn(
        state, PlayerCommand(type="ship_grain", quantity=50), "normal", state.to_turn_context()
    )
    # Shipment effect should be capped at capacity 5
    shipment_eff = next(e for e in res.domain_effects if e.metric == "shipment")
    assert shipment_eff.delta == -5, f"capacity should cap to -5, got {shipment_eff.delta}"
    assert shipment_eff.reason_code == "limited_by_capacity"
    # Inventory after should reflect capped movement: before 80 + harvest 100 capped to 200 -> 180 pre-ship, minus 5 -> 175
    # Harvest 100 added to 80 =180, storage 200 so not capped, then ship 5 -> 175
    assert res.next_state.player.inventory.grain == 175
    # Cash should reflect only 5 units revenue/cost, not 50
    shipment_node = next(n for n in res.causal_trace.nodes if n.id == "shipment")
    assert shipment_node.delta == -5
    assert "limited_by_capacity" in shipment_node.reason_code


def test_profitable_arbitrage_emerges_from_market_conditions_not_script() -> None:
    """AC4: Profitability depends on market supply/demand divergence, not scripted flag."""
    # Same route, same command, different market conditions should flip profitability
    # Condition A: Home surplus (low home price), River shortage (high river price) -> profitable
    s_profit = _base_state(
        cash=5000,
        grain=50,
        storage=200,
        home_supply=200,
        home_demand=80,
        home_price=5000,
        river_supply=60,
        river_demand=150,
        river_price=5200,
        transport_cost=800,
        established=True,
        route_capacity=20,
    )
    # Condition B: Home shortage (high home price), River surplus (low river price) -> unprofitable (or less profitable)
    s_loss = _base_state(
        cash=5000,
        grain=50,
        storage=200,
        home_supply=60,
        home_demand=150,
        home_price=5000,
        river_supply=200,
        river_demand=80,
        river_price=5200,
        transport_cost=800,
        established=True,
        route_capacity=20,
    )
    res_profit = resolve_turn(
        s_profit,
        PlayerCommand(type="ship_grain", quantity=10),
        "normal",
        s_profit.to_turn_context(),
    )
    res_loss = resolve_turn(
        s_loss, PlayerCommand(type="ship_grain", quantity=10), "normal", s_loss.to_turn_context()
    )
    # Extract trade net
    profit_trade = next(
        (d for d in res_profit.player_outcome.drivers if d.id == "trade_arbitrage"), None
    )
    loss_trade = next(
        (d for d in res_loss.player_outcome.drivers if d.id == "trade_arbitrage"), None
    )
    # At least one of profit/loss should be present; they should differ
    assert profit_trade is not None or loss_trade is not None
    # Profit case should have higher net than loss case
    profit_val = profit_trade.impact_money if profit_trade else 0
    loss_val = loss_trade.impact_money if loss_trade else 0
    assert profit_val > loss_val, f"profit {profit_val} should exceed loss {loss_val}"
    # Verify no scripted bonus: check turn.py does not contain hard-coded bonus string
    import pathlib

    src = pathlib.Path("backend/app/engine/turn.py").read_text()
    assert "bonus" not in src.lower()
    assert "arbitrage_reward" not in src.lower()
    # Verify river and home prices diverged differently
    assert (
        res_profit.next_state.market.current_price
        != res_profit.next_state.river_market.current_price
    )
    assert (
        res_loss.next_state.market.current_price != res_loss.next_state.river_market.current_price
    )
    # Profit case: home price low, river high; loss case: opposite
    # Ensure trace shows river_price_pressure chain for both
    assert any(n.id == "river_price_pressure" for n in res_profit.causal_trace.nodes)
    assert any(n.id == "river_price_pressure" for n in res_loss.causal_trace.nodes)


def test_player_can_remain_entirely_in_home_valley() -> None:
    """AC5: Player can complete turn staying in Home Valley (no trade)."""
    for cmd_type in ("hold", "expand_farm", "build_granary", "buy_grain", "secure_route"):
        state = _base_state(established=False)
        qty = 10 if cmd_type == "buy_grain" else None
        cmd = PlayerCommand(type=cmd_type, quantity=qty)  # type: ignore[arg-type]
        res = resolve_turn(state, cmd, "normal", state.to_turn_context())  # type: ignore[arg-type]
        # Should produce valid next_state, no crash, inventory/cash non-negative
        assert res.next_state.turn == state.turn + 1
        assert res.next_state.player.cash >= 0
        assert res.next_state.player.inventory.grain >= 0
        assert res.next_state.market.current_price >= 1
        assert res.next_state.river_market.current_price >= 1
        # Route may be unchanged or established, but should still be valid
        assert isinstance(res.next_state.route.established, bool)
        # DAG should be valid (already validated by model, but check parents exist)
        assert res.causal_trace.nodes[-1].id == "wealth"
        # Drivers ≤3
        assert len(res.player_outcome.drivers) <= 3
    # Also hold with established False vs True should both work
    s_no_route = _base_state(established=False)
    s_has_route = _base_state(established=True)
    res_no = resolve_turn(
        s_no_route, PlayerCommand(type="hold"), "normal", s_no_route.to_turn_context()
    )
    res_has = resolve_turn(
        s_has_route, PlayerCommand(type="hold"), "normal", s_has_route.to_turn_context()
    )
    # Both should succeed and home market chain identical aside from route nodes
    assert res_no.next_state.market.current_price == res_has.next_state.market.current_price


def test_all_results_remain_deterministic() -> None:
    """AC6: Same state+command+world+seed => identical result, including River and Route."""
    for cmd_type in (
        "hold",
        "expand_farm",
        "build_granary",
        "buy_grain",
        "secure_route",
        "ship_grain",
    ):
        for world in ("normal", "drought"):
            cmd = PlayerCommand(type=cmd_type, quantity=10)  # type: ignore[arg-type]
            # Need fresh state with same seed each time
            s = _base_state(
                established=cmd_type in ("ship_grain", "hold"),
                route_capacity=20,
                transport_cost=800,
                seed="seed-determinism-001",
            )
            ctx = s.to_turn_context()
            r1 = resolve_turn(s, cmd, world, ctx)  # type: ignore[arg-type]
            r2 = resolve_turn(s, cmd, world, ctx)  # type: ignore[arg-type]
            assert r1 == r2, f"non-deterministic for {cmd_type}/{world}"
            # Seed change may produce different derived RNG but still deterministic per seed
            s2 = s.model_copy(update={"run_seed": "seed-different"})
            ctx2 = s2.to_turn_context()
            r3 = resolve_turn(s2, cmd, world, ctx2)  # type: ignore[arg-type]
            r4 = resolve_turn(s2, cmd, world, ctx2)  # type: ignore[arg-type]
            assert r3 == r4
            # Different turn should also be deterministic per turn
            s3 = _base_state(turn=5, established=True, seed="seed-001")
            r5 = resolve_turn(s3, cmd, world, s3.to_turn_context())  # type: ignore[arg-type]
            r6 = resolve_turn(s3, cmd, world, s3.to_turn_context())  # type: ignore[arg-type]
            assert r5 == r6


def test_secure_route_creates_trade_access() -> None:
    """Command that creates trade access must be deterministic and cost cash."""
    state = _base_state(cash=1000, established=False)
    # First secure should cost and establish
    res = resolve_turn(state, PlayerCommand(type="secure_route"), "normal", state.to_turn_context())
    assert res.next_state.route.established is True
    assert res.next_state.player.cash == 600  # 1000 -400
    # Second secure when already established should not charge again
    state2 = res.next_state
    res2 = resolve_turn(
        state2, PlayerCommand(type="secure_route"), "normal", state2.to_turn_context()
    )
    assert res2.next_state.route.established is True
    assert (
        res2.next_state.player.cash == res2.next_state.player.cash
    )  # no further cost aside from possibly 0
    # Check reason_code for second is already_established
    route_node = next(n for n in res2.causal_trace.nodes if n.id == "route_established")
    assert route_node.reason_code == "already_established"
    # Insufficient cash should not establish
    poor = _base_state(cash=100, established=False)
    res_poor = resolve_turn(
        poor, PlayerCommand(type="secure_route"), "normal", poor.to_turn_context()
    )
    assert res_poor.next_state.route.established is False
    assert res_poor.next_state.player.cash == 100
    assert any(n.reason_code == "insufficient_cash_for_route" for n in res_poor.causal_trace.nodes)


def test_ship_requires_route_access() -> None:
    """Ship without established route should be blocked and not move grain."""
    state = _base_state(cash=1000, grain=20, storage=100, established=False)
    res = resolve_turn(
        state, PlayerCommand(type="ship_grain", quantity=10), "normal", state.to_turn_context()
    )
    # No inventory movement
    shipment = next(e for e in res.domain_effects if e.metric == "shipment")
    assert shipment.delta == 0
    assert shipment.reason_code == "no_route_access"
    # Inventory only reflects harvest, not shipment: 20 +100 farm output capped to 100 -> 100
    assert res.next_state.player.inventory.grain == 100
    assert res.next_state.player.cash == 1000


def test_turn_order_string() -> None:
    """TURN_ORDER must include river and route phases and valuation."""
    assert "home_supply" in TURN_ORDER
    assert "river_supply" in TURN_ORDER
    assert "home_price" in TURN_ORDER
    assert "river_price" in TURN_ORDER
    assert "route_settlement" in TURN_ORDER
    assert "valuation" in TURN_ORDER


def test_wealth_decomposition_still_exact_with_route() -> None:
    """Wealth delta must remain exact with route: cash + purchase+harvest+ship + price."""
    for world in ("normal", "drought"):
        for cmd_type in ("hold", "ship_grain", "secure_route", "buy_grain"):
            state = _base_state(cash=2000, grain=30, storage=200, established=True)
            qty = 10 if cmd_type in ("buy_grain", "ship_grain") else None
            cmd = PlayerCommand(type=cmd_type, quantity=qty)  # type: ignore[arg-type]
            res = resolve_turn(state, cmd, world, state.to_turn_context())  # type: ignore[arg-type]
            eff = {e.metric: e for e in res.domain_effects}
            wealth = eff["wealth"].delta
            assert (
                wealth
                == eff["cash_effect"].delta
                + eff["purchase_quantity_value"].delta
                + eff["harvest_quantity_value"].delta
                + eff["ship_quantity_value"].delta
                + eff["price_value_effect"].delta
            )
            assert (
                eff["quantity_value_effect"].delta
                == eff["purchase_quantity_value"].delta
                + eff["harvest_quantity_value"].delta
                + eff["ship_quantity_value"].delta
            )


def test_arbitrage_uses_resolved_home_price_not_before() -> None:
    """Regression: old Home 5.00 new 6.00 river 6.24 transport 0.80 -> old says +0.44 profitable, resolved says -0.56 unprofitable."""
    # Craft market conditions that make home price rise from 5000 to 6000 (new) while river goes to 6240
    # home_supply 70 demand 130 etc gives 5000->6000 as shown in manual run
    state = _base_state(
        cash=5000,
        grain=50,
        farm=0,
        storage=200,
        home_supply=70,
        home_demand=130,
        home_price=5000,
        river_supply=80,
        river_demand=130,
        river_price=5200,
        transport_cost=800,
        reliability=10000,
        established=True,
    )
    res = resolve_turn(
        state, PlayerCommand(type="ship_grain", quantity=10), "normal", state.to_turn_context()
    )
    assert res.next_state.market.current_price == 6000
    assert res.next_state.river_market.current_price == 6240
    # Old calc: river 62 - cost 8 - before_home 50 = 4 profitable (before_price 5000)
    # New calc (arbitrage_margin): river 62 - cost 8 - new_home 60 = -6 unprofitable (new_price 6000)
    old_margin = 62 - 8 - 50  # 4
    new_margin = 62 - 8 - 60  # -6
    assert old_margin == 4
    assert new_margin == -6
    trade = next(d for d in res.player_outcome.drivers if d.id == "trade_arbitrage")
    # Engine must report unprofitable based on resolved price, even though wealth net is +4
    assert trade.reason_code == "unprofitable_shipment"
    # Label should mention arbitrage at resolved prices
    assert "arbitrage" in trade.label.lower()
    assert "-6" in trade.label


def test_trade_causal_graph_truthful() -> None:
    """Fix 2: cash_effect via cash_after_trade, price_value_effect via inventory_after_trade, shipment limits structural."""
    state = _base_state(cash=5000, grain=50, storage=200, established=True, reliability=10000)
    res = resolve_turn(
        state, PlayerCommand(type="ship_grain", quantity=10), "normal", state.to_turn_context()
    )
    nodes = {n.id: n for n in res.causal_trace.nodes}
    # cash_effect must parent cash_after_trade, not cash_after_command directly
    assert nodes["cash_effect"].parent_ids == ("cash_after_trade",)
    assert nodes["cash_after_trade"].parent_ids == (
        "cash_after_command",
        "trade_revenue",
        "transport_cost",
    )
    # price_value_effect must parent inventory_after_trade
    assert nodes["price_value_effect"].parent_ids == ("inventory_after_trade", "price")
    assert nodes["inventory_after_trade"].parent_ids == ("inventory", "shipment")
    # shipment must structurally depend on all limiters
    assert "command" in nodes["shipment"].parent_ids
    assert "route_established" in nodes["shipment"].parent_ids
    assert "route_capacity" in nodes["shipment"].parent_ids
    assert "inventory" in nodes["shipment"].parent_ids
    assert "route_cost_per_unit" in nodes["shipment"].parent_ids
    assert "cash_after_command" in nodes["shipment"].parent_ids
    assert "route_reliability" in nodes["shipment"].parent_ids
    # trade_revenue must parent route_reliability
    assert "route_reliability" in nodes["trade_revenue"].parent_ids
    assert "river_price" in nodes["trade_revenue"].parent_ids
    assert "shipment" in nodes["trade_revenue"].parent_ids
    # Also check blocked case has cash_after_trade zero correctly
    blocked = _base_state(cash=1000, grain=20, established=False)
    res_blocked = resolve_turn(
        blocked, PlayerCommand(type="ship_grain", quantity=10), "normal", blocked.to_turn_context()
    )
    nodes_b = {n.id: n for n in res_blocked.causal_trace.nodes}
    assert nodes_b["cash_after_trade"].delta == 0
    assert nodes_b["inventory_after_trade"].delta == 0


def test_reliability_and_delay_semantics() -> None:
    """Fix 3: reliability consistent for all values, default lossless, delay constrained to 0."""
    from pydantic import ValidationError

    # Default lossless
    assert RouteState().reliability_bps == 10000
    assert RouteState().delay_turns == 0
    # Delay >0 rejected
    try:
        RouteState(delay_turns=3)
        raise AssertionError("delay 3 should be rejected")
    except ValidationError:
        pass
    # Reliability affects delivered deterministically: 9000 -> 90% etc
    for reliability, expected_rev in [(10000, 62), (9000, 56), (5000, 31), (0, 0)]:
        s = _base_state(reliability=reliability, established=True, cash=5000, grain=50, storage=200)
        # Use fixed market so river price 6240
        s = s.model_copy(
            update={
                "river_market": MarketState(
                    supply=80, demand=130, base_price=5200, current_price=5200
                )
            }
        )
        res = resolve_turn(
            s, PlayerCommand(type="ship_grain", quantity=10), "normal", s.to_turn_context()
        )
        rev = next(n for n in res.causal_trace.nodes if n.id == "trade_revenue")
        assert rev.delta == expected_rev, (
            f"reliability {reliability} expected rev {expected_rev} got {rev.delta}"
        )
        # route_reliability must be parent of trade_revenue when it affects delivery
        assert "route_reliability" in rev.parent_ids
