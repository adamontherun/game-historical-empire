"""Pydantic schemas for the minimal API — outside engine/domain."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.trace import CausalTrace, DomainEffect, OutcomeDriver


class CreateGameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_seed: str | None = Field(default=None, min_length=1, max_length=64)
    ruleset_version: str | None = Field(default=None, min_length=1, max_length=32)


class CreateChoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: Annotated[int, Field(ge=0)]


class ChoiceView(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    kind: str
    quantity: int | None = None
    cost: int | None = None  # cash cost for buy/expand/build/secure; None for others


class PlayerSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    cash: int
    inventory_grain: int
    farm_capacity: int
    storage_capacity: int
    wealth: int


class EmpireSummary(BaseModel):
    """Exactly the three concrete empire fields — no invented operations list.

    OperationState exists at domain/types.py:40 but is dormant per types.py:59
    (not embedded in PlayerState to avoid duplicate source of truth).
    Synthesizing farm_1/granary_1 with invented levels would create fictional
    canonical-looking state — so mapper keeps single source of truth.
    """

    model_config = ConfigDict(frozen=True)

    farm_capacity: int
    storage_capacity: int
    route_established: bool


class MarketView(BaseModel):
    model_config = ConfigDict(frozen=True)

    supply: int
    demand: int
    base_price: int
    current_price: int
    responsiveness: int


class RouteStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    established: bool
    capacity: int
    transport_cost_per_unit: int
    reliability_bps: int
    next_margin: int  # via actor.ship_margin(river, transport, home)


class RivalHeadlines(BaseModel):
    model_config = ConfigDict(frozen=True)

    mira: str
    daran: str


class OutcomeView(BaseModel):
    """Latest turn's outcome with its OWN resolved context — not the next turn.

    After drought, OutcomeView.world == "drought" while GameView.world == "aftermath".
    This disambiguation is required for Section 11's reveal screen (C4).
    """

    model_config = ConfigDict(frozen=True)

    resolved_turn: int
    title: str
    pressure_stage: str
    world: Literal["normal", "drought"]
    command_type: str
    command_quantity: int | None = None
    wealth_delta: int
    inventory_delta: int
    price_delta: int
    drivers: tuple[OutcomeDriver, ...]
    domain_effects: tuple[DomainEffect, ...]
    causal_trace: CausalTrace


class CompletionSummaryView(BaseModel):
    """API-owned end-screen summary — no history smuggling (C3).

    Must NOT contain initial_state, final_state, history, or raw rival states.
    StrategicSummary at prototype.py:137 has those — returning it would be a
    history endpoint by another name, contradicting Section 10's explicit exclusion
    and B2's "latest turn only" decision.
    """

    model_config = ConfigDict(frozen=True)

    initial_wealth: int
    final_wealth: int
    wealth_delta_total: int
    final_cash: int
    final_grain: int
    final_farm_capacity: int
    final_storage_capacity: int
    cash_low: int
    peak_inventory: int
    is_complete: bool
    final_rival_headlines: RivalHeadlines | None = None


class GameView(BaseModel):
    model_config = ConfigDict(frozen=True)

    game_id: str
    run_seed: str  # B5: echoed so omitted-seed games are reproducible; distinct from game_id
    ruleset_version: str  # S0c: echo version for determinism reproduction
    revision: int
    turn: int
    turn_limit: int  # derived from prototype.TURN_LIMIT, not literal 5 (B7/C7)
    signal: str  # next-decision context (C4)
    pressure_stage: str  # next-decision context
    world: Literal["normal", "drought"]  # next-decision context
    player_summary: PlayerSummary
    empire_summary: EmpireSummary
    home_valley_market: MarketView
    river_town_market: MarketView
    route_status: RouteStatus
    rival_headlines: RivalHeadlines | None = None
    available_choices: tuple[ChoiceView, ...]
    latest_outcome: OutcomeView | None = (
        None  # C4: carries its own resolved context + unconditional causal_trace (B2/C2)
    )
    completion_summary: CompletionSummaryView | None = None  # C3: API-owned, not StrategicSummary
