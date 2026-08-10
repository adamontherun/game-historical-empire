"""Deterministic regime-shift mechanism proof — Section 13.

Vary exactly one variable (skilled_labour) to prove the labour cap is
the binding constraint. Two players enter the epilogue with identical
grain, cash, and legacies; only labour differs (1 vs 3). After three
epilogue turns the labour-rich player must end with more wealth.

Falsifiability: if the labour cap is removed (max_by_labour = 10_000)
both arms craft the same amount and end equal, so the test fails.
This distinguishes "labour is the bottleneck" from
"holding cash beats holding grain in a declining grain market".

Also covers AC3 legacy linkage: river_contracts is what grants +2 labour.
"""

from app.domain.pressure import PressureState
from app.domain.types import (
    GameState,
    InventoryState,
    MarketState,
    PlayerCommand,
    PlayerState,
    RouteState,
)
from app.engine.actor import FINISHED_GOODS_PRICE, FINISHED_GOODS_PRICE_RIVER_EXTRA
from app.engine.turn import resolve_turn


def _make_state(
    grain: int,
    labour: int,
    cash: int,
    finished: int,
    price: int,
    legacies: tuple[str, ...],
    turn: int = 5,
) -> GameState:
    return GameState(
        turn=turn,
        run_seed="scenario",
        ruleset_version="t",
        player=PlayerState(
            cash=cash,
            inventory=InventoryState(grain=grain, finished_goods=finished),
            farm_capacity=10,
            storage_capacity=200,
            skilled_labour=labour,
        ),
        market=MarketState(
            supply=100, demand=280, base_price=5000, current_price=5000 if price == 5000 else price
        ),
        river_market=MarketState(supply=80, demand=130, base_price=5200, current_price=5200),
        route=RouteState(),
        legacies=legacies,
    )


def _wealth(state: GameState) -> int:
    price = state.market.current_price
    leg_extra = FINISHED_GOODS_PRICE_RIVER_EXTRA if "river_contracts" in state.legacies else 0
    fin_price = FINISHED_GOODS_PRICE + leg_extra
    return (
        state.player.cash
        + state.player.inventory.grain * price // 1000
        + state.player.inventory.finished_goods * fin_price // 1000
    )


def _run_three_turns(state: GameState) -> GameState:
    cur = state
    pressure = PressureState(
        pressure_id="test",
        stage="normal",
        activation_turn=0,
        world="normal",
        signal="ok",
        title="t",
    )
    for _ in range(3):
        grain = cur.player.inventory.grain
        # Request all grain — let actor.py enforce the labour cap (labour*10).
        # This is critical for falsifiability: if max_by_labour is removed,
        # both arms craft the same amount and wealth equalises.
        if grain > 0:
            cmd = PlayerCommand.model_validate({"type": "craft_goods", "quantity": grain})
        else:
            cmd = PlayerCommand.model_validate({"type": "hold"})
        res = resolve_turn(cur, cmd, pressure, cur.to_turn_context())
        cur = res.next_state
    return cur


def test_single_variable_labour_cap_is_binding():
    """Vary exactly one thing: 150 grain, 1500 cash, labour 1 vs 3 -> labour-rich wins."""
    price = 5000
    grain = 150
    cash = 1500
    legacies: tuple[str, ...] = ()

    state_poor = _make_state(grain, 1, cash, 0, price, legacies)
    state_rich = _make_state(grain, 3, cash, 0, price, legacies)

    # Identical except labour — same grain, cash, legacies, market price
    assert state_poor.player.inventory.grain == state_rich.player.inventory.grain == grain
    assert state_poor.player.cash == state_rich.player.cash == cash
    assert state_poor.legacies == state_rich.legacies == legacies
    assert state_poor.player.skilled_labour == 1
    assert state_rich.player.skilled_labour == 3
    assert _wealth(state_poor) == _wealth(state_rich) == cash + grain * price // 1000

    end_poor = _run_three_turns(state_poor)
    end_rich = _run_three_turns(state_rich)

    # Labour-rich crafts 30/turn (90 total -> 27 finished) vs 10/turn (30 total -> 9 finished)
    # Both start 150 grain and harvest replenishes, but cap is binding.
    assert _wealth(end_rich) > _wealth(end_poor), (
        f"labour-rich {_wealth(end_rich)} should beat labour-poor {_wealth(end_poor)} "
        f"after 3 epilogue turns (identical start 150 grain, 1500 cash, legacies {legacies}) "
        f"— labour×10 cap is the bottleneck"
    )


def test_river_contracts_grants_plus_two_labour():
    """AC3 legacy linkage: river_contracts is what grants +2 skilled_labour."""

    # Direct mapping as implemented in EightTurnGame._ensure_epilogue_start:
    # base 1, +2 if river_contracts (trade_heavy only; granary/land do not grant labour)
    def epilogue_labour(legacies: tuple[str, ...]) -> int:
        base = 1
        if "river_contracts" in legacies:
            base += 2
        return base

    assert epilogue_labour(("river_contracts",)) == 3
    assert epilogue_labour(()) == 1
    assert epilogue_labour(("river_contracts",)) - epilogue_labour(()) == 2
    assert epilogue_labour(("granary_expertise",)) == 1
    assert epilogue_labour(("land_network",)) == 1
    assert epilogue_labour(("granary_expertise", "land_network")) == 1

    # Verify via actual EightTurnGame: route -> river_contracts -> 3 labour
    from app.engine.prototype import EightTurnGame

    # Without route: no river_contracts, labour 1
    g_without = EightTurnGame(seed="labour-without", version="t")
    for _ in range(5):
        g_without.submit(PlayerCommand.model_validate({"type": "hold"}))
    assert "river_contracts" not in g_without.legacies
    assert g_without.state.player.skilled_labour == 1

    # With route: secure_route grants river_contracts, labour 3
    g_with = EightTurnGame(seed="labour-with", version="t")
    g_with.submit(PlayerCommand.model_validate({"type": "secure_route"}))
    for _ in range(4):
        g_with.submit(PlayerCommand.model_validate({"type": "hold"}))
    assert "river_contracts" in g_with.legacies
    assert g_with.state.player.skilled_labour == 3
    assert g_with.state.player.skilled_labour - g_without.state.player.skilled_labour == 2
