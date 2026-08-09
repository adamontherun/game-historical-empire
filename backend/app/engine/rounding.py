"""Deterministic integer rounding helpers for canonical economic math.

All canonical economic state is integer (Money/Quantity/BasisPoints/PriceMilliunits).
Transient Decimal must be quantized explicitly via these helpers.
Rounding is deterministic and tested; no floats in canonical path.
"""

from __future__ import annotations


def mul_basis_points(value: int, bps: int) -> int:
    """Multiply value by basis points (10_000 = 100%) with floor division.

    Deterministic floor behavior; no float. Negative inputs are allowed
    at this layer — caller validation (e.g. Pydantic ge=0) prevents invalid
    canonical state from being constructed.

    Args:
        value: Base integer value (e.g. Money or Quantity).
        bps: Basis points, where 10_000 == 100%.

    Returns:
        Floored integer result of value * bps / 10_000.
    """
    return (value * bps) // 10_000


def apply_basis_points(value: int, bps: int) -> int:
    """Alias for mul_basis_points — semantic for price adjustments."""
    return mul_basis_points(value, bps)


def div_round_half_up(numerator: int, denominator: int) -> int:
    """Integer division rounding half away from zero for positive denominators.

    For negative numerators, follows symmetric half-up (e.g. -3/2 -> -2).
    Denominator must be non-zero; zero raises ZeroDivisionError deterministically.

    Args:
        numerator: Dividend.
        denominator: Divisor, must not be 0.

    Returns:
        Rounded quotient.
    """
    if denominator == 0:
        raise ZeroDivisionError("denominator must not be zero")
    # Use integer math without float to stay deterministic.
    # For denominator > 0: (n + d//2) // d for n>=0; (n - d//2) // d for n<0
    # For denominator < 0: normalize sign.
    if denominator < 0:
        numerator = -numerator
        denominator = -denominator
    if numerator >= 0:
        return (numerator + denominator // 2) // denominator
    return -((-numerator + denominator // 2) // denominator)


def clamp_non_negative(value: int) -> int:
    """Clamp value to >= 0 — useful for post-math canonical guards."""
    return value if value >= 0 else 0
