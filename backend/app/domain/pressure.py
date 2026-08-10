"""Pressure domain — Section 8 world-pressure arc types.

Small, frozen, validated types for the pressure-driven event arc.
Pressure is turn-derived/session-authored, not canonical GameState.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.types import WorldCondition

PressureStage = Literal["normal", "early_dry", "worsening_dry", "drought", "aftermath"]


class PressureState(BaseModel):
    """One step of the authored pressure arc — frozen, validated.

    Exactly 7 fields per spec (R2/F4). World is tied to stage by
    biconditional (F2): stage == "drought" iff world == "drought".
    causal_source_id is the single source for the trace pressure node
    (F3) — default is f"pressure:{pressure_id}:{stage}" and explicit
    overrides are forced to match that formula.
    """

    model_config = ConfigDict(frozen=True)

    pressure_id: str = Field(description="Stable arc id, e.g. 'northern_drought'")
    stage: PressureStage = Field(description="Pressure stage")
    activation_turn: int = Field(ge=0, le=4, description="Turn index this stage activates (0..4)")
    world: WorldCondition = Field(description="World condition for this stage")
    signal: str = Field(description="Player-facing signal text for this stage")
    title: str = Field(description="Stage title, e.g. 'Surplus'")
    causal_source_id: str = Field(
        default="",
        description="Trace causal_source_id — defaults to f'pressure:{pressure_id}:{stage}'",
    )

    @model_validator(mode="before")  # pyright: ignore[reportUnknownVariableType]
    @classmethod
    def _populate_causal_source_id(cls, data: object) -> object:
        # Populate default causal_source_id before validation (G6: avoid frozen mutation)
        if isinstance(data, dict):
            d = data  # type: ignore[assignment]
            cid = d.get("causal_source_id")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            if not cid:
                pid = d.get("pressure_id")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                stage = d.get("stage")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                if pid and stage:
                    d["causal_source_id"] = f"pressure:{pid}:{stage}"  # pyright: ignore[reportUnknownMemberType]
        return data  # pyright: ignore[reportUnknownVariableType]

    @model_validator(mode="after")
    def _validate(self) -> PressureState:
        # Biconditional: stage == "drought" <=> world == "drought" (F2)
        is_drought_stage = self.stage == "drought"
        is_drought_world = self.world == "drought"
        if is_drought_stage != is_drought_world:
            raise ValueError(
                f"stage {self.stage!r} and world {self.world!r} mismatch: "
                f"stage == 'drought' must iff world == 'drought'"
            )
        # causal_source_id single source (F3) — must match formula if explicitly set
        expected = f"pressure:{self.pressure_id}:{self.stage}"
        if self.causal_source_id != expected:
            raise ValueError(
                f"causal_source_id {self.causal_source_id!r} != expected {expected!r} "
                f"(must equal f'pressure:{{pressure_id}}:{{stage}}')"
            )
        return self
