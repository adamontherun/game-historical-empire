"""Domain package — re-exports canonical types."""

from app.domain.trace import (
    CausalNode,
    CausalTrace,
    DomainEffect,
    PlayerOutcome,
    TurnResolution,
)
from app.domain.types import (
    BasisPoints,
    GameState,
    InventoryState,
    MarketState,
    Money,
    OperationState,
    PlayerCommand,
    PlayerState,
    PriceMilliunits,
    Quantity,
    TurnContext,
    WorldCondition,
)

__all__ = [
    "BasisPoints",
    "CausalNode",
    "CausalTrace",
    "DomainEffect",
    "GameState",
    "InventoryState",
    "MarketState",
    "Money",
    "OperationState",
    "PlayerCommand",
    "PlayerState",
    "PlayerOutcome",
    "PriceMilliunits",
    "Quantity",
    "TurnContext",
    "TurnResolution",
    "WorldCondition",
]
