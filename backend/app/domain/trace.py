"""Causal trace, domain effects, and player outcome for Section 3.

Minimal chain structure compatible with Section 4's richer formalization.
Trace is emitted during resolution, not reconstructed by diffing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.types import GameState


class CausalNode(BaseModel):
    """One step in the causal chain with explicit parent links."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Stable node id, e.g. 'drought', 'farm_output'")
    label: str = Field(description="Human-readable label for this node")
    kind: str = Field(description="Node kind, e.g. 'world', 'production', 'supply', 'price'")
    before: int | None = Field(default=None, description="Value before change")
    after: int | None = Field(default=None, description="Value after change")
    delta: int | None = Field(default=None, description="Delta if applicable")
    reason_code: str = Field(description="Machine reason code, e.g. 'drought_reduced_yield'")
    parent_ids: list[str] = Field(default_factory=list, description="Parent node ids")


class CausalTrace(BaseModel):
    """Ordered causal chain — parents appear before children."""

    model_config = ConfigDict(frozen=True)

    nodes: list[CausalNode] = Field(description="Causal nodes in emission order")
    # Edges are implicit via parent_ids; flat deltas alone would be insufficient.


class DomainEffect(BaseModel):
    """Player-visible economic effect derived from trace."""

    model_config = ConfigDict(frozen=True)

    metric: str = Field(description="Metric name, e.g. 'cash', 'farm_output', 'grain_price'")
    before: int = Field(description="Value before")
    after: int = Field(description="Value after")
    delta: int = Field(description="Delta (after - before)")
    reason_code: str = Field(description="Reason code")


class PlayerOutcome(BaseModel):
    """Concise player outcome for the turn reveal."""

    model_config = ConfigDict(frozen=True)

    wealth_delta: int = Field(description="Cash delta for the turn")
    inventory_delta: int = Field(description="Grain inventory delta")
    price_delta: int = Field(description="Market price delta")
    top_drivers: list[str] = Field(description="Up to 3 driver labels derived from trace")


class TurnResolution(BaseModel):
    """Full result of resolving one turn."""

    model_config = ConfigDict(frozen=True)

    next_state: GameState = Field(description="Canonical next state (turn incremented)")
    domain_effects: list[DomainEffect] = Field(description="Domain effects for display")
    causal_trace: CausalTrace = Field(description="Structured causal chain")
    player_outcome: PlayerOutcome = Field(description="Concise player-facing outcome")
