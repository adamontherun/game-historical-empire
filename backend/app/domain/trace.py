"""Causal trace, domain effects, and player outcome for Sections 4–5.

Structural causal graph with exact wealth decomposition and immutable tuples.
Trace is emitted during resolution, not reconstructed by diffing.
Section 5 adds river price divergence and route/ship subgraph.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.domain.types import GameState

CausalEdge = tuple[str, str]

Kind = Literal[
    "world",
    "command",
    "capacity",
    "cash",
    "production",
    "supply",
    "demand",
    "price",
    "inventory",
    "quantity_value_effect",
    "purchase_quantity_value",
    "harvest_quantity_value",
    "price_value_effect",
    "wealth",
    "route",
    "trade",
    "river_supply",
    "river_price",
]


class CausalNode(BaseModel):
    """One step in the causal chain with explicit parent links."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Stable node id, e.g. 'farm_output'")
    label: str = Field(description="Human-readable label for this node")
    kind: str = Field(description="Node kind")
    before: int | None = Field(default=None, description="Value before change")
    after: int | None = Field(default=None, description="Value after change")
    delta: int | None = Field(default=None, description="Delta if applicable")
    reason_code: str = Field(description="Machine reason code, e.g. 'drought_reduced_yield'")
    parent_ids: tuple[str, ...] = Field(
        default_factory=tuple, description="Parent node ids in topological order"
    )

    @model_validator(mode="after")
    def _validate_delta(self) -> CausalNode:
        if self.before is not None and self.after is not None and self.delta is not None:
            if self.delta != self.after - self.before:
                # Allow None delta to skip check; otherwise enforce consistency
                # For nodes where before/after are present, delta must match
                pass  # keep permissive for now; DomainEffect enforces strictly
        if self.delta is not None and self.before is not None and self.after is not None:
            # Strict check only when all three present and not
            # deliberately capped
            # Inventory capped nodes have correct delta; keep check
            if self.delta != self.after - self.before:
                raise ValueError(
                    f"CausalNode {self.id} delta {self.delta} "
                    f"!= after {self.after} - before {self.before}"
                )
        return self


class CausalTrace(BaseModel):
    """Ordered causal chain — parents appear before children, immutable tuples."""

    model_config = ConfigDict(frozen=True)

    nodes: tuple[CausalNode, ...] = Field(
        default_factory=tuple, description="Causal nodes in emission order"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def edges(self) -> tuple[CausalEdge, ...]:
        """Derived edges as (parent, child) tuples from parent_ids."""
        out: list[CausalEdge] = []
        for node in self.nodes:
            for pid in node.parent_ids:
                out.append((pid, node.id))
        return tuple(out)

    @model_validator(mode="after")
    def _validate_dag(self) -> CausalTrace:
        seen: dict[str, int] = {}
        for idx, node in enumerate(self.nodes):
            if node.id in seen:
                raise ValueError(f"duplicate node id {node.id!r}")
            seen[node.id] = idx
        # Check parents exist and appear before child, and allowed roots
        allowed_empty_roots = {"world", "command"}
        for idx, node in enumerate(self.nodes):
            if not node.parent_ids:
                # Empty parents allowed for world/command always;
                # for others only if delta is 0 or None (unchanged)
                if node.id in allowed_empty_roots or node.kind in allowed_empty_roots:
                    continue
                # farm_capacity / storage_capacity unchanged nodes are allowed as roots
                if node.id in ("farm_capacity", "storage_capacity") and node.delta == 0:
                    continue
                # Generic unchanged capacity nodes allowed
                if node.kind == "capacity" and node.delta == 0:
                    continue
                # Demand signal nodes are stable inputs (like capacity) — allow delta 0 as root
                if node.kind == "demand" and node.delta == 0:
                    continue
                # Route nodes with zero delta may be roots (not yet established / no trade)
                if (
                    node.kind in ("route", "trade", "river_supply", "river_price")
                    and node.delta == 0
                ):
                    continue
                if (
                    node.id
                    in (
                        "route_capacity",
                        "route_reliability",
                        "route_cost_per_unit",
                        "river_supply",
                        "river_price_pressure",
                        "river_target_price",
                        "river_price",
                        "shipment",
                        "trade_revenue",
                        "transport_cost",
                        "trade_profit",
                    )
                    and node.delta == 0
                ):
                    continue
                # If delta is None (diagnostic like world) already
                # handled; otherwise require parents
                # But diagnostic nodes like world have been allowed;
                # other nodes with no delta and no parents are allowed
                # only if world/command
                # For production/supply/price/inventory/wealth etc
                # with no parents, it's invalid
                if node.kind in (
                    "production",
                    "supply",
                    "demand",
                    "price",
                    "inventory",
                    "quantity_value_effect",
                    "purchase_quantity_value",
                    "harvest_quantity_value",
                    "price_value_effect",
                    "wealth",
                    "route",
                    "trade",
                    "river_supply",
                    "river_price",
                ):
                    raise ValueError(f"node {node.id!r} kind {node.kind!r} must have parent_ids")
                # cash_after_command etc should have parents; but
                # cash_after_command is child of command, so not empty
                # If node has delta==0 and is capacity, allow;
                # otherwise require parents
                if node.delta is not None and node.delta != 0:
                    raise ValueError(f"node {node.id!r} must have parent_ids")
                # Allow zero-delta diagnostic nodes to be roots
                continue
            for pid in node.parent_ids:
                if pid not in seen:
                    raise ValueError(f"node {node.id!r} parent {pid!r} not found")
                if seen[pid] >= idx:
                    raise ValueError(f"node {node.id!r} parent {pid!r} must appear before child")
                if pid == node.id:
                    raise ValueError(f"node {node.id!r} cannot be parent of itself")
        return self


class DomainEffect(BaseModel):
    """Player-visible economic effect derived from trace."""

    model_config = ConfigDict(frozen=True)

    metric: str = Field(description="Metric name, e.g. 'cash', 'farm_output', 'grain_price'")
    before: int = Field(description="Value before")
    after: int = Field(description="Value after")
    delta: int = Field(description="Delta (after - before)")
    reason_code: str = Field(description="Reason code")

    @model_validator(mode="after")
    def _validate_delta(self) -> DomainEffect:
        if self.delta != self.after - self.before:
            raise ValueError(
                f"DomainEffect {self.metric!r} delta {self.delta} "
                f"!= after {self.after} - before {self.before}"
            )
        return self


class OutcomeDriver(BaseModel):
    """Player-facing causal story grouping multiple trace nodes.

    Represents a distinct economic narrative (e.g. farm output, price move,
    cash cost) whose wealth impact is exact and sums to wealth_delta across
    drivers plus discarded zero effects.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        description="Stable driver id, e.g. 'farm_output', 'supply_price', 'command_cost'"
    )
    label: str = Field(description="Human-readable sentence for the reveal")
    kind: str = Field(
        description="Driver kind, e.g. 'production', 'supply', 'price', 'cash', 'valuation'"
    )
    impact_money: int = Field(description="Exact contribution to wealth_delta in Money")
    impact_bps: int = Field(
        description="Basis points of wealth_before: abs(impact_money)*10000//max(wealth_before,1)"
    )
    reason_code: str = Field(description="Machine reason code")
    causal_node_ids: tuple[str, ...] = Field(
        description="Ordered trace node ids that justify this driver (path)"
    )


class PlayerOutcome(BaseModel):
    """Concise player outcome for the turn reveal."""

    model_config = ConfigDict(frozen=True)

    wealth_delta: int = Field(
        description="Wealth delta = cash_effect + quantity_value_effect + price_value_effect"
    )
    inventory_delta: int = Field(description="Grain inventory delta")
    price_delta: int = Field(description="Market price delta")
    drivers: tuple[OutcomeDriver, ...] = Field(
        default_factory=tuple,
        max_length=3,
        description="Up to 3 story drivers ranked by exact wealth-bps",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def top_drivers(self) -> tuple[str, ...]:
        """Deprecated string view — derived from drivers for backward compat."""
        return tuple(d.label for d in self.drivers)


class TurnResolution(BaseModel):
    """Full result of resolving one turn."""

    model_config = ConfigDict(frozen=True)

    next_state: GameState = Field(description="Canonical next state (turn incremented)")
    domain_effects: tuple[DomainEffect, ...] = Field(description="Domain effects for display")
    causal_trace: CausalTrace = Field(description="Structured causal chain")
    player_outcome: PlayerOutcome = Field(description="Concise player-facing outcome")
