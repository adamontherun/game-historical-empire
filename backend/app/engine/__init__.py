"""Engine package — deterministic RNG and rounding."""

from app.engine.harness import BatchConfig, BatchResult, format_markdown, run_batch, to_json
from app.engine.pressure import (
    PRESSURE_ARC,
    PRESSURE_BY_WORLD,
    PRESSURE_DROUGHT,
    PRESSURE_NORMAL,
    next_world_known_for_turn,
    pressure_for_turn,
    pressure_for_world,
    world_for_turn,
)
from app.engine.rng import derive_seed, make_rng, rng_for
from app.engine.rounding import (
    apply_basis_points,
    clamp_non_negative,
    div_round_half_up,
    mul_basis_points,
)
from app.engine.turn import TURN_ORDER, resolve_turn

__all__ = [
    "PRESSURE_ARC",
    "PRESSURE_BY_WORLD",
    "PRESSURE_DROUGHT",
    "PRESSURE_NORMAL",
    "TURN_ORDER",
    "apply_basis_points",
    "BatchConfig",
    "BatchResult",
    "clamp_non_negative",
    "derive_seed",
    "div_round_half_up",
    "format_markdown",
    "make_rng",
    "mul_basis_points",
    "next_world_known_for_turn",
    "pressure_for_turn",
    "pressure_for_world",
    "resolve_turn",
    "rng_for",
    "run_batch",
    "to_json",
    "world_for_turn",
]
