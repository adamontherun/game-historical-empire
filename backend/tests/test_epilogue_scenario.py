"""Deterministic regime-shift mechanism proof — Section 13.

Two players enter the epilogue with equal wealth.
One is grain-rich / labour-poor (agricultural winner shape),
the other grain-poorer / labour-rich (river_contracts).
After three epilogue turns the labour-rich player must end with more wealth.

This tests the *mechanism* (labour is the bottleneck), not a statistical
harness ranking. The four-arm harness (epilogue_harness.run_four_arm) remains
as an instrument for post-playtest tuning but is not a gate.
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
            storage_capacity=10,
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
        labour = cur.player.skilled_labour
        grain = cur.player.inventory.grain
        finished = cur.player.inventory.finished_goods
        if labour > 0 and grain > 0:
            qty = min(grain, labour * 10)
            cmd = PlayerCommand.model_validate({"type": "craft_goods", "quantity": qty})
        elif finished > 0:
            cmd = PlayerCommand.model_validate(
                {"type": "sell_finished_goods", "quantity": min(finished, 30)}
            )
        else:
            cmd = PlayerCommand.model_validate({"type": "hold"})
        res = resolve_turn(cur, cmd, pressure, cur.to_turn_context())
        cur = res.next_state
    return cur


def test_equal_wealth_labour_rich_wins():
    """Grain-rich/labour-poor vs grain-poorer/labour-rich, equal start wealth -> labour wins."""
    price = 5000
    grain_poor_labour = 150  # agricultural winner shape
    grain_rich_labour = 70  # river shape — less grain
    cash_poor = 1500
    wealth_eq = cash_poor + grain_poor_labour * price // 1000
    cash_rich = wealth_eq - grain_rich_labour * price // 1000

    state_poor = _make_state(grain_poor_labour, 1, cash_poor, 0, price, ("land_network",))
    state_rich = _make_state(grain_rich_labour, 3, cash_rich, 0, price, ("river_contracts",))

    assert _wealth(state_poor) == _wealth(state_rich) == wealth_eq

    end_poor = _run_three_turns(state_poor)
    end_rich = _run_three_turns(state_rich)

    assert _wealth(end_rich) > _wealth(end_poor), (
        f"labour-rich {_wealth(end_rich)} should beat grain-rich {_wealth(end_poor)} "
        f"after 3 epilogue turns (equal start {wealth_eq})"
    )
