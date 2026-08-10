"""Pressure arc — Section 8 authored 5-turn arc.

Hard-coded, deterministic, no RNG, no I/O, no JSON loader.
Pressure is turn-derived (R1/F2), not canonical GameState.
"""

from __future__ import annotations

from app.domain.pressure import PressureStage, PressureState
from app.domain.types import WorldCondition

PRESSURE_ARC: tuple[PressureState, ...] = (
    PressureState(
        pressure_id="northern_drought",
        stage="normal",
        activation_turn=0,
        world="normal",
        signal="The growing settlement keeps food demand high.",
        title="A Growing Settlement",
    ),
    PressureState(
        pressure_id="northern_drought",
        stage="early_dry",
        activation_turn=1,
        world="normal",
        signal="Grain remains abundant, but the rains have begun to fail.",
        title="Surplus",
    ),
    PressureState(
        pressure_id="northern_drought",
        stage="worsening_dry",
        activation_turn=2,
        world="normal",
        signal="The dry spell persists. Farmers warn the next harvest is at risk.",
        title="Warning Signs",
    ),
    PressureState(
        pressure_id="northern_drought",
        stage="drought",
        activation_turn=3,
        world="drought",
        signal="Drought cuts farm output — regional supply tightens.",
        title="Drought",
    ),
    PressureState(
        pressure_id="northern_drought",
        stage="aftermath",
        activation_turn=4,
        world="normal",
        signal="Markets adjust to the drought's aftermath.",
        title="Aftermath",
    ),
)

# Validate activation_turn == index at import (single source)
for _idx, _p in enumerate(PRESSURE_ARC):
    if _p.activation_turn != _idx:
        raise ValueError(
            f"PRESSURE_ARC[{_idx}].activation_turn={_p.activation_turn} != index {_idx}"
        )


def pressure_for_turn(idx: int) -> PressureState:
    """Return PressureState for turn idx (0..4), else raise."""
    if not 0 <= idx < len(PRESSURE_ARC):
        raise IndexError(f"pressure_for_turn idx {idx} out of range 0..{len(PRESSURE_ARC) - 1}")
    return PRESSURE_ARC[idx]


def world_for_turn(idx: int) -> WorldCondition:
    """Derive world for turn idx from pressure arc."""
    return pressure_for_turn(idx).world


def next_world_known_for_turn(idx: int) -> WorldCondition | None:
    """Structured threat known at turn idx (pre-turn).

    Only T3 (idx=2, worsening_dry) telegraphs T4 drought. Derived from
    pressure stage, never from prose parsing. Early_dry does not threaten.
    """
    stage: PressureStage = pressure_for_turn(idx).stage  # type: ignore[assignment]
    if stage == "worsening_dry":
        return "drought"
    return None
