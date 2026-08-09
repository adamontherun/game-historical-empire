"""Tests for canonical economic types — AC #1, #2."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.types import (
    GameState,
    InventoryState,
    MarketState,
    OperationState,
    PlayerState,
)


def test_money_quantity_price_must_be_int_and_non_negative() -> None:
    with pytest.raises(ValidationError):
        PlayerState(
            cash=-1,  # type: ignore[arg-type]
            inventory=InventoryState(grain=0),
            farm_capacity=10,
            storage_capacity=10,
        )
    with pytest.raises(ValidationError):
        InventoryState(grain=-5)
    with pytest.raises(ValidationError):
        MarketState(supply=10, demand=10, base_price=-1, current_price=1000)
    with pytest.raises(ValidationError):
        MarketState(supply=-1, demand=10, base_price=1000, current_price=1000)


def test_operation_capacity_non_negative() -> None:
    with pytest.raises(ValidationError):
        OperationState(id="farm_1", kind="farm", capacity=-1)


def test_game_state_valid_construction() -> None:
    state = GameState(
        turn=0,
        run_seed="seed-001",
        ruleset_version="1.0",
        player=PlayerState(
            cash=1000,
            inventory=InventoryState(grain=50),
            farm_capacity=10,
            storage_capacity=100,
        ),
        market=MarketState(supply=100, demand=120, base_price=5000, current_price=5200),
    )
    assert state.turn == 0
    assert state.player.cash == 1000
    assert state.market.supply == 100


def test_turn_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        GameState(
            turn=-1,
            run_seed="s",
            ruleset_version="1.0",
            player=PlayerState(
                cash=0, inventory=InventoryState(grain=0), farm_capacity=0, storage_capacity=0
            ),
            market=MarketState(supply=0, demand=0, base_price=0, current_price=0),
        )


def test_frozen_models_reject_mutation() -> None:
    inv = InventoryState(grain=10)
    with pytest.raises(ValidationError):
        inv.grain = -1  # type: ignore[assignment]


def test_canonical_values_are_int() -> None:
    state = GameState(
        turn=1,
        run_seed="seed-001",
        ruleset_version="1.0",
        player=PlayerState(
            cash=100, inventory=InventoryState(grain=1), farm_capacity=1, storage_capacity=1
        ),
        market=MarketState(supply=1, demand=1, base_price=1, current_price=1),
    )
    assert isinstance(state.player.cash, int)
    assert isinstance(state.player.inventory.grain, int)
    assert isinstance(state.market.current_price, int)
    assert isinstance(state.market.supply, int)


def test_to_turn_context() -> None:
    state = GameState(
        turn=3,
        run_seed="seed-xyz",
        ruleset_version="2.0",
        player=PlayerState(
            cash=0, inventory=InventoryState(grain=0), farm_capacity=0, storage_capacity=0
        ),
        market=MarketState(supply=0, demand=0, base_price=0, current_price=0),
    )
    ctx = state.to_turn_context()
    assert ctx.turn == 3
    assert ctx.run_seed == "seed-xyz"
    assert ctx.ruleset_version == "2.0"
