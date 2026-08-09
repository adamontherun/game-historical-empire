"""Canonical economic types for Sections 2-4.

Integer-only canonical state per BUILD_SPEC §12. Validation via Pydantic v2
Annotated constraints — invalid negatives rejected at construction.
All models are frozen for determinism.

Covers 10 required concepts:
- cash, grain inventory, farm capacity, storage capacity,
  regional supply/demand, grain price, turn, run_seed, ruleset_version

Six models: GameState, PlayerState, MarketState, OperationState,
InventoryState, TurnContext plus Money/Quantity/BasisPoints/PriceMilliunits.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# Canonical numeric aliases — constrained where invalid negatives are possible.
# BasisPoints allows any int (helpers validate range where needed); others are ge=0.

Money = Annotated[int, Field(ge=0, strict=True)]
Quantity = Annotated[int, Field(ge=0, strict=True)]
PriceMilliunits = Annotated[int, Field(ge=0, strict=True)]
BasisPoints = Annotated[int, Field(strict=True)]


class InventoryState(BaseModel):
    """Player grain inventory — single good grain for Sections 2-4."""

    model_config = ConfigDict(frozen=True)

    grain: Quantity = Field(default=0, description="Grain quantity on hand")


class OperationState(BaseModel):
    """Economic operation — stub for farm/granary, extensible later.

    Represents a farm or granary operation with capacity. Level exists for
    future compounding visibility (§8) without generic registry.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Stable operation id, e.g. 'farm_1'")
    kind: Literal["farm", "granary"] = Field(description="Operation kind")
    capacity: Quantity = Field(description="Capacity owned by this operation")
    level: int = Field(default=1, ge=1, description="Visible scale level")


class PlayerState(BaseModel):
    """Player economic exposure."""

    model_config = ConfigDict(frozen=True)

    cash: Money = Field(description="Player cash")
    inventory: InventoryState = Field(description="Player inventory")
    farm_capacity: Quantity = Field(description="Total farm capacity")
    storage_capacity: Quantity = Field(description="Total storage capacity")
    operations: list[OperationState] = Field(
        default_factory=list, description="Operations owned (stub for Sec 5)"
    )


class MarketState(BaseModel):
    """Regional grain market — minimal for Sections 2-4.

    Responsiveness / max movement deferred to Section 3.
    """

    model_config = ConfigDict(frozen=True)

    supply: Quantity = Field(description="Regional grain supply")
    demand: Quantity = Field(description="Regional grain demand")
    base_price: PriceMilliunits = Field(description="Base price milliunits")
    current_price: PriceMilliunits = Field(description="Current price milliunits")


class TurnContext(BaseModel):
    """Lightweight turn identity for RNG derivation."""

    model_config = ConfigDict(frozen=True)

    turn: int = Field(ge=0, description="Current turn number")
    run_seed: str = Field(description="Opaque run seed")
    ruleset_version: str = Field(description="Ruleset version")


class GameState(BaseModel):
    """Top-level canonical game state for Sections 2-4."""

    model_config = ConfigDict(frozen=True)

    turn: int = Field(ge=0, description="Current turn")
    run_seed: str = Field(description="Opaque run seed")
    ruleset_version: str = Field(description="Ruleset version")
    player: PlayerState = Field(description="Player state")
    market: MarketState = Field(description="Regional market state")

    def to_turn_context(self) -> TurnContext:
        """Derive TurnContext for RNG calls."""
        return TurnContext(
            turn=self.turn, run_seed=self.run_seed, ruleset_version=self.ruleset_version
        )
