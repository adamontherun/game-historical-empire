"""Canonical economic types for Sections 2-5.

Integer-only canonical state per BUILD_SPEC §12. Validation via Pydantic v2
Annotated constraints — invalid negatives rejected at construction.
All models are frozen for determinism.

Covers Section 5 two-market + route extension:
- cash, grain inventory, farm capacity, storage capacity,
  home + river market supply/demand, grain price, turn, run_seed, ruleset_version,
  River Route with transport cost / capacity / reliability / delay / event exposure

Models: GameState (now two markets + route), PlayerState, MarketState,
RouteState, OperationState, InventoryState, TurnContext plus Money/Quantity/BasisPoints/PriceMilliunits.
WorldCondition and PlayerCommand (now with secure_route/ship_grain) for Section 5.
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
    """Player inventory — grain for Sections 2-4, finished_goods added Section 13."""

    model_config = ConfigDict(frozen=True)

    grain: Quantity = Field(default=0, description="Grain quantity on hand")
    finished_goods: Quantity = Field(
        default=0, description="Finished goods (city craft) — Section 13"
    )


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
    """Player economic exposure — single source of truth for capacities.

    For Sections 2-4 farm/storage capacities are explicit aggregates.
    OperationState exists as a standalone type for future Section 5 use
    but is not embedded here to avoid coherent-state duplication
    (frozen + mutable list + duplicate capacity sources).
    Section 13 adds skilled_labour (workshop bottleneck).
    """

    model_config = ConfigDict(frozen=True)

    cash: Money = Field(description="Player cash")
    inventory: InventoryState = Field(description="Player inventory")
    farm_capacity: Quantity = Field(description="Total farm capacity")
    storage_capacity: Quantity = Field(description="Total storage capacity")
    skilled_labour: Quantity = Field(
        default=0, description="Skilled labour (city craft) — Section 13"
    )


class MarketState(BaseModel):
    """Regional grain market — one market, one good (grain) for Section 3."""

    model_config = ConfigDict(frozen=True)

    supply: Quantity = Field(description="Regional grain supply")
    demand: Quantity = Field(description="Regional grain demand")
    regional_output: Quantity = Field(
        default=0,
        description="Non-player regional grain output per turn (Home only; River stays exogenous)",
    )
    base_price: PriceMilliunits = Field(  # type: ignore[call-overload]
        description="Base price milliunits (>0)",
        strict=True,
        gt=0,
    )
    current_price: PriceMilliunits = Field(  # type: ignore[call-overload]
        description="Current price milliunits (>0)",
        strict=True,
        gt=0,
    )
    responsiveness: BasisPoints = Field(
        default=5000,
        description="Price responsiveness bps (10_000=100% pass-through, >=0)",
        strict=True,
        ge=0,
    )
    max_movement_bps: BasisPoints = Field(
        default=2000,
        description="Max per-turn price movement bps (0..10_000)",
        strict=True,
        ge=0,
        le=10_000,
    )


class TurnContext(BaseModel):
    """Lightweight turn identity for RNG derivation."""

    model_config = ConfigDict(frozen=True)

    turn: int = Field(ge=0, description="Current turn number")
    run_seed: str = Field(description="Opaque run seed")
    ruleset_version: str = Field(description="Ruleset version")


WorldCondition = Literal["normal", "drought"]


class RouteState(BaseModel):
    """River Route — single route between Home Valley and River Town (Section 5).

    Carries the four required route properties plus optional delay/event exposure.
    All fields are canonical integer/bool (frozen). Transport cost is per grain
    unit in PriceMilliunits (milli-Money) so profit arithmetic uses
    qty*price_milli//1000 and stays comparable to grain price (~5000 milli).
    """

    model_config = ConfigDict(frozen=True)

    transport_cost_per_unit: PriceMilliunits = Field(
        default=800, description="Transport cost per grain unit in milliunits (≥0)"
    )
    capacity: Quantity = Field(
        default=20, description="Carrying capacity per turn in grain units (≥0)"
    )
    reliability_bps: BasisPoints = Field(
        default=10000,
        description="Reliability 0..10_000 (10_000=100% delivers all)",
        strict=True,
        ge=0,
        le=10_000,
    )
    established: bool = Field(default=False, description="Whether trade access has been secured")
    delay_turns: int = Field(
        default=0,
        ge=0,
        le=0,
        description="Optional settlement delay in turns (must be 0 until delayed settlement exists)",
    )
    event_exposure: str = Field(
        default="river_risk", description="Event exposure tag for future pressure arc"
    )


class PlayerCommand(BaseModel):
    """Player turn command — one major action per turn (Sections 3–5, sell_grain Section 9, craft/hire Section 13)."""

    model_config = ConfigDict(frozen=True)

    type: Literal[
        "expand_farm",
        "build_granary",
        "buy_grain",
        "sell_grain",
        "hold",
        "secure_route",
        "ship_grain",
        "craft_goods",
        "sell_finished_goods",
        "hire_labour",
    ] = Field(description="Command type")
    quantity: Quantity | None = Field(
        default=None,
        description="Grain quantity for buy_grain / sell_grain / ship_grain / craft_goods / sell_finished_goods (ignored otherwise)",
    )


class GameState(BaseModel):
    """Top-level canonical game state for Sections 2-5.

    For backward compatibility, `market` remains the Home Valley market alias
    (existing tests construct `GameState(market=...)`). `river_market` is the
    River Town market and `route` is the River Route. Together they satisfy
    Section 5's two-market + route requirement without renaming churn.
    """

    model_config = ConfigDict(frozen=True)

    turn: int = Field(ge=0, description="Current turn")
    run_seed: str = Field(description="Opaque run seed")
    ruleset_version: str = Field(description="Ruleset version")
    player: PlayerState = Field(description="Player state")
    market: MarketState = Field(description="Home Valley market state (alias)")
    river_market: MarketState = Field(
        default_factory=lambda: MarketState(
            supply=80, demand=130, base_price=5200, current_price=5200
        ),
        description="River Town market state",
    )
    route: RouteState = Field(default_factory=RouteState, description="River Route state")
    legacies: tuple[str, ...] = Field(
        default=(), description="Earned legacies carried into epilogue (Section 13)"
    )

    def to_turn_context(self) -> TurnContext:
        """Derive TurnContext for RNG calls."""
        return TurnContext(
            turn=self.turn, run_seed=self.run_seed, ruleset_version=self.ruleset_version
        )
