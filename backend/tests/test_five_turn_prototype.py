"""Section 6 — Five-Turn Headless Prototype acceptance tests.

AC1: exactly 5 decisions
AC2: completable from terminal (non-interactive via run)
AC3: deterministic same choices -> same, different choices diverge
AC4: three strategies diverge
AC5: drought rewards preparation
AC6: top causes understandable
AC7: concise strategic summary
Plus supply semantics stock-drained gate.
"""

from __future__ import annotations

from app.domain.types import PlayerCommand
from app.engine.prototype import (
    TURN_LIMIT,
    TURN_SPECS,
    FiveTurnGame,
    default_start_state,
)
from app.engine.turn import resolve_turn


def _hold() -> PlayerCommand:
    return PlayerCommand(type="hold")


def _choices(*types: str) -> list[PlayerCommand]:
    """Helper to build choice list from type strings like 'buy_grain:20'."""
    out: list[PlayerCommand] = []
    for t in types:
        if ":" in t:
            typ, qty_s = t.split(":", 1)
            out.append(PlayerCommand(type=typ, quantity=int(qty_s)))  # type: ignore[arg-type]
        else:
            out.append(PlayerCommand(type=t))  # type: ignore[arg-type]
    return out


def test_five_turn_game_requires_exactly_five_decisions() -> None:
    game = FiveTurnGame(seed="seed-five-001")
    assert not game.is_complete
    assert game.current_turn == 0
    # 4 submits not complete
    for _ in range(4):
        game.submit(_hold())
        assert not game.is_complete
    assert len(game.history) == 4
    assert game.current_turn == 4
    # 5th completes
    game.submit(_hold())
    assert game.is_complete
    assert len(game.history) == 5
    assert game.state.turn == 5
    # 6th raises
    try:
        game.submit(_hold())
        raise AssertionError("6th submit should raise")
    except ValueError as e:
        assert "complete" in str(e).lower()


def test_can_be_completed_from_terminal_noninteractive() -> None:
    game = FiveTurnGame(seed="seed-noninteractive")
    summary = game.run([_hold()] * 5)
    assert len(summary.history) == 5
    assert summary.is_complete
    assert summary.final_state.turn == 5
    assert summary.final_wealth >= 0
    # history length is 5
    assert len(game.history) == 5


def test_determinism_same_seed_same_choices_same_final_state() -> None:
    choices = _choices("hold", "hold", "hold", "hold", "hold")
    g1 = FiveTurnGame(seed="det-seed")
    g2 = FiveTurnGame(seed="det-seed")
    s1 = g1.run(list(choices))
    s2 = g2.run(list(choices))
    assert s1.history == s2.history
    assert s1.final_state == s2.final_state
    assert s1.final_wealth == s2.final_wealth
    # Different choices must potentially diverge
    g3 = FiveTurnGame(seed="det-seed")
    diff_choices = _choices("expand_farm", "hold", "hold", "hold", "hold")
    s3 = g3.run(diff_choices)
    assert s3.final_state != s1.final_state or s3.final_wealth != s1.final_wealth


def test_supply_semantics_is_stock_drained_by_demand() -> None:
    """Gate for KDR #5: supply is stock drained by demand each turn."""
    # Use a controlled state: supply 100, demand 90, farm 10 => 100 harvest normal
    state = default_start_state(seed="supply-semantics", version="1.0")
    # Override to known values via manual GameState
    # Use the default start state's market: supply 100 demand 90
    # For normal: stock_next = 100 + 100 -90 =110
    # For drought: 100+60-90=70
    normal = resolve_turn(state, _hold(), "normal", state.to_turn_context())
    drought = resolve_turn(state, _hold(), "drought", state.to_turn_context())
    assert normal.next_state.market.supply == 110, (
        f"expected 110 got {normal.next_state.market.supply}"
    )
    assert drought.next_state.market.supply == 70, (
        f"expected 70 got {drought.next_state.market.supply}"
    )
    # Supply lower under drought
    assert drought.next_state.market.supply < normal.next_state.market.supply
    # Price higher under drought scarcity
    assert drought.next_state.market.current_price >= normal.next_state.market.current_price
    # Verify trace supply node exists and has correct reason
    supply_node = next(n for n in normal.causal_trace.nodes if n.id == "supply")
    assert supply_node.after == 110
    assert "farm_output" in supply_node.parent_ids


def test_three_strategies_diverge() -> None:
    seed = "diverge-seed-001"
    farm_heavy = _choices("expand_farm", "expand_farm", "hold", "hold", "hold")
    storage_heavy = _choices("build_granary", "buy_grain:20", "hold", "hold", "hold")
    trade_heavy = _choices(
        "secure_route", "build_granary", "hold", "ship_grain:10", "ship_grain:10"
    )

    g_farm = FiveTurnGame(seed=seed)
    g_storage = FiveTurnGame(seed=seed)
    g_trade = FiveTurnGame(seed=seed)

    s_farm = g_farm.run(farm_heavy)
    s_storage = g_storage.run(storage_heavy)
    s_trade = g_trade.run(trade_heavy)

    # At least one pair differs by >10% on final wealth or peak inventory or cash_low
    # Check final wealth spread
    vals = [s_farm.final_wealth, s_storage.final_wealth, s_trade.final_wealth]
    max_v = max(vals)
    min_v = min(vals)
    # At least 10% spread relative to max
    assert max_v != min_v, "strategies must not be identical"
    spread_bps = abs(max_v - min_v) * 10000 // max(max_v, 1)
    assert spread_bps >= 1000, f"expected >=10% spread, got {spread_bps / 100:.1f}%  vals={vals}"

    # Also check that each completed 5 turns
    for s in (s_farm, s_storage, s_trade):
        assert len(s.history) == 5
        assert s.is_complete

    # Also verify each history has 5 turn specs
    assert len(TURN_SPECS) == 5
    assert TURN_SPECS[3].world == "drought"
    assert TURN_SPECS[2].world == "normal"


def test_drought_rewards_preparation() -> None:
    seed = "prepare-seed"
    # Unprepared: farm-heavy before drought — overexpands farm, wastes storage, low cash
    unprepared_choices = _choices("expand_farm", "expand_farm", "expand_farm", "hold", "hold")
    # Prepared: storage before drought (build + buy)
    prepared_choices = _choices("build_granary", "buy_grain:20", "hold", "hold", "hold")

    g_unprep = FiveTurnGame(seed=seed)
    g_prep = FiveTurnGame(seed=seed)

    s_unprep = g_unprep.run(unprepared_choices)
    s_prep = g_prep.run(prepared_choices)

    # Find T4 (index 3) wealth delta — drought turn
    unprep_t4 = s_unprep.history[3].player_outcome.wealth_delta
    prep_t4 = s_prep.history[3].player_outcome.wealth_delta
    # Prepared should have higher (less negative or more positive) T4 wealth than unprepared
    # Farm-heavy wastes cash and creates surplus that depresses its own price, while
    # storage-heavy has inventory to benefit from scarcity price rise
    assert prep_t4 > unprep_t4, f"prepared T4 {prep_t4} should exceed unprepared {unprep_t4}"
    # Prepared should also have higher inventory to show preparation
    assert (
        s_prep.history[3].next_state.player.inventory.grain
        > s_unprep.history[2].next_state.player.inventory.grain
        or s_prep.peak_inventory >= s_unprep.peak_inventory
    )


def test_each_turn_has_understandable_causes() -> None:
    game = FiveTurnGame(seed="causes-seed")
    game.run([_hold()] * 5)
    for i, res in enumerate(game.history):
        # Each turn's drivers ≤3
        assert len(res.player_outcome.drivers) <= 3
        # Each trace has required chain
        ids = {n.id for n in res.causal_trace.nodes}
        for required in (
            "world",
            "farm_output",
            "supply",
            "price",
            "inventory",
            "quantity_value_effect",
            "price_value_effect",
            "wealth",
        ):
            assert required in ids, f"turn {i + 1} missing {required}"
        # Drivers derived from trace
        trace_ids = ids
        for d in res.player_outcome.drivers:
            for cid in d.causal_node_ids:
                assert cid in trace_ids
        # At least world -> farm_output edge exists
        farm_node = next(n for n in res.causal_trace.nodes if n.id == "farm_output")
        assert "world" in farm_node.parent_ids
        supply_node = next(n for n in res.causal_trace.nodes if n.id == "supply")
        assert "farm_output" in supply_node.parent_ids

    # Signals are truthful prose (check first and drought)
    assert "demand high" in TURN_SPECS[0].signal.lower() or "demand" in TURN_SPECS[0].signal.lower()
    assert "abundant" in TURN_SPECS[1].signal.lower() or "weak" in TURN_SPECS[1].signal.lower()
    assert "drought" in TURN_SPECS[3].signal.lower()


def test_run_ends_with_concise_strategic_summary() -> None:
    game = FiveTurnGame(seed="summary-seed")
    game.run([_hold()] * 5)
    summary = game.summary()
    assert summary.is_complete
    assert summary.final_state.turn == 5
    assert len(summary.history) == 5
    assert summary.final_wealth >= 0
    assert summary.initial_wealth >= 0
    assert summary.wealth_delta_total == summary.final_wealth - summary.initial_wealth
    assert summary.cash_low >= 0
    assert summary.peak_inventory >= 0
    formatted = summary.format()
    assert "STRATEGIC SUMMARY" in formatted
    assert "5 turns" in formatted
    assert "final wealth" in formatted.lower()


def test_run_requires_exactly_five_choices() -> None:
    game = FiveTurnGame(seed="exact-five")
    try:
        game.run([_hold()] * 4)
        raise AssertionError("should require exactly 5")
    except ValueError as e:
        assert "exactly 5" in str(e)
    try:
        game.run([_hold()] * 6)
        raise AssertionError("should require exactly 5")
    except ValueError as e:
        assert "exactly 5" in str(e)


def test_cli_parse_choices() -> None:
    from app.cli import parse_choice, parse_choices_arg

    assert parse_choice("hold").type == "hold"
    assert parse_choice("1").type == "hold"
    assert parse_choice("buy 20").type == "buy_grain" and parse_choice("buy 20").quantity == 20
    assert (
        parse_choice("buy_grain:10").type == "buy_grain"
        and parse_choice("buy_grain:10").quantity == 10
    )
    assert parse_choice("ship 10").type == "ship_grain" and parse_choice("ship 10").quantity == 10
    assert parse_choice("secure_route").type == "secure_route"
    assert parse_choice("expand_farm").type == "expand_farm"
    choices = parse_choices_arg("hold,buy 20,hold,ship 10,hold")
    assert len(choices) == 5
    assert choices[1].quantity == 20
    assert choices[3].quantity == 10


def test_signals_truthful_about_mechanics() -> None:
    """Every authored signal must not assert a mechanic not in the model."""
    # The five signals must not claim demand rises or harvest differs except where world differs
    # Check that only T4 is drought, others normal — so signals claiming "strong harvest" for T2
    # would be false. Our revised signals claim "Repeated harvests have left grain abundant"
    # which is true via stock accumulation, not per-turn harvest difference.
    assert TURN_SPECS[0].world == "normal"
    assert TURN_SPECS[1].world == "normal"
    assert TURN_SPECS[2].world == "normal"
    assert TURN_SPECS[3].world == "drought"
    assert TURN_SPECS[4].world == "normal"
    # No signal should mention a demand number or harvest amount not present
    for spec in TURN_SPECS:
        assert "price +=" not in spec.signal
        assert (
            "demand rising" not in spec.signal.lower() or spec == TURN_SPECS[0]
        )  # only T1 mentions demand high, not rising per turn
    # T2 surplus must be emergent, not claimed as different world
    assert "abundant" in TURN_SPECS[1].signal.lower()


def test_turn_specs_length_and_titles() -> None:
    assert len(TURN_SPECS) == TURN_LIMIT == 5
    titles = [s.title for s in TURN_SPECS]
    assert titles[0] == "A Growing Settlement"
    assert titles[1] == "Surplus"
    assert titles[2] == "Warning Signs"
    assert titles[3] == "Drought"
    assert titles[4] == "Aftermath"


def test_available_commands_include_all_verbs() -> None:
    game = FiveTurnGame()
    cmds = game.available_commands()
    for verb in ("hold", "expand_farm", "build_granary", "buy_grain", "secure_route", "ship_grain"):
        assert verb in cmds
