"""Invariant and property tests for Section 3 — AC #2, #4."""

from __future__ import annotations

from app.domain.types import GameState, InventoryState, MarketState, PlayerCommand, PlayerState
from app.engine.turn import _bounded_price, _target_price, resolve_turn


def _state(
    supply: int, demand: int = 120, base_price: int = 5000, current_price: int = 5000
) -> GameState:
    return GameState(
        turn=0,
        run_seed="inv-seed",
        ruleset_version="1.0",
        player=PlayerState(
            cash=1000, inventory=InventoryState(grain=10), farm_capacity=5, storage_capacity=100
        ),
        market=MarketState(
            supply=supply, demand=demand, base_price=base_price, current_price=current_price
        ),
    )


def test_target_price_monotonic_in_supply() -> None:
    # Lower supply with fixed demand should not reduce target price.
    demand = 120
    base = 5000
    resp = 5000
    prices = []
    for supply in [200, 150, 100, 50, 20, 10, 5]:
        p = _target_price(base, supply, demand, resp)
        prices.append((supply, p))
    # As supply decreases, price should be non-decreasing
    for i in range(len(prices) - 1):
        s_high, p_high = prices[i]
        s_low, p_low = prices[i + 1]
        assert s_high > s_low
        assert p_low >= p_high, (
            f"supply {s_high}->{s_low} should not reduce target price {p_high}->{p_low}"
        )


def test_bounded_price_monotonic_with_supply() -> None:
    # Even with bounding, lower supply should not give lower bounded price
    demand = 120
    base = 5000
    current = 5000
    max_bps = 2000
    resp = 5000
    supplies = [200, 150, 100, 80, 60, 40, 20]
    # We need to go from high supply to low supply: price should be non-decreasing
    for _supply in reversed(supplies):  # start low supply?
        # Actually test decreasing supply -> price non-decreasing
        pass
    # Forward: as supply goes down, bounded price should not go down
    bounded_prices = []
    for s in supplies:
        target = _target_price(base, s, demand, resp)
        bp = _bounded_price(current, target, max_bps)
        bounded_prices.append((s, bp))
    for i in range(len(bounded_prices) - 1):
        s_high, p_high = bounded_prices[i]
        s_low, p_low = bounded_prices[i + 1]
        # s_high > s_low, so p_low should be >= p_high
        assert p_low >= p_high, (
            f"bounded price should be monotonic: supply {s_high}->{s_low} price {p_high}->{p_low}"
        )


def test_demand_unchanged_cannot_reduce_target_when_supply_falls() -> None:
    # Property: for any demand, reducing supply cannot reduce target
    for demand in [50, 100, 120, 200]:
        for supply_high in [100, 150]:
            supply_low = supply_high - 20
            t_high = _target_price(5000, supply_high, demand, 5000)
            t_low = _target_price(5000, supply_low, demand, 5000)
            assert t_low >= t_high, (
                f"demand {demand} supply {supply_high}->{supply_low} target {t_high}->{t_low}"
            )


def test_resolve_turn_monotonic_via_engine() -> None:
    # Use full resolve_turn: lower initial supply should lead to >= price
    cmd = PlayerCommand(type="hold")
    # Use farm 0 to isolate price effect; but farm_output still adds, need same farm  # noqa: E501
    s_high = _state(supply=150, demand=120, current_price=5000)
    s_low = _state(supply=100, demand=120, current_price=5000)
    # Both have same farm 5 => same output, but starting supply differs
    r_high = resolve_turn(s_high, cmd, "normal", s_high.to_turn_context())
    r_low = resolve_turn(s_low, cmd, "normal", s_low.to_turn_context())
    assert r_low.next_state.market.current_price >= r_high.next_state.market.current_price


def test_no_negatives_across_random_spread() -> None:
    # Fuzz a few states
    cases = [
        (0, 0, 0, 0),
        (10, 1000, 5000, 5000),
        (100, 10, 100, 1000),
        (50, 50, 1, 1),
    ]
    for supply, demand, base_price, current_price in cases:
        for cash, farm, storage, grain in [(0, 0, 0, 0), (10, 5, 10, 5), (1000, 100, 200, 50)]:
            state = GameState(
                turn=0,
                run_seed="fuzz",
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
            for world in ("normal", "drought"):
                for cmd_type in ("hold", "expand_farm", "build_granary", "buy_grain"):
                    qty = 5 if cmd_type == "buy_grain" else None
                    cmd = PlayerCommand(type=cmd_type, quantity=qty)  # type: ignore[arg-type]
                    res = resolve_turn(state, cmd, world, state.to_turn_context())  # type: ignore[arg-type]
                    assert res.next_state.player.cash >= 0
                    assert res.next_state.player.inventory.grain >= 0
                    assert res.next_state.market.supply >= 0
                    assert res.next_state.market.current_price >= 1


def test_price_stays_positive_extreme() -> None:
    for supply in [0, 1, 2, 10000]:
        for demand in [0, 1, 10000]:
            t = _target_price(100, supply, demand, 10000)
            assert t >= 1
            bp = _bounded_price(100, t, 2000)
            assert bp >= 1


def test_responsiveness_zero_gives_base_price() -> None:
    # With responsiveness 0, target should be base_price regardless of imbalance
    for supply in [10, 100, 200]:
        t = _target_price(5000, supply, 120, 0)
        assert t == 5000
