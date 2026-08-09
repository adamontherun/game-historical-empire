"""Tests for deterministic rounding helpers — AC #6."""

from __future__ import annotations

import pytest

from app.engine.rounding import (
    apply_basis_points,
    clamp_non_negative,
    div_round_half_up,
    mul_basis_points,
)


def test_mul_basis_points_floor() -> None:
    assert mul_basis_points(1000, 10_000) == 1000  # 100%
    assert mul_basis_points(1000, 5000) == 500  # 50%
    assert mul_basis_points(1000, 0) == 0
    assert mul_basis_points(1, 3333) == 0  # floor
    assert mul_basis_points(3, 3333) == 0  # 0.9999 floor to 0
    assert mul_basis_points(3, 3334) == 1  # 1.0002 floor to 1


def test_apply_basis_points_alias() -> None:
    assert apply_basis_points(2000, 2500) == 500  # 25% of 2000


def test_div_round_half_up_positive() -> None:
    assert div_round_half_up(5, 2) == 3  # 2.5 -> 3
    assert div_round_half_up(4, 2) == 2
    assert div_round_half_up(1, 2) == 1  # 0.5 -> 1
    assert div_round_half_up(3, 2) == 2  # 1.5 -> 2
    assert div_round_half_up(0, 5) == 0


def test_div_round_half_up_negative() -> None:
    assert div_round_half_up(-5, 2) == -3  # -2.5 -> -3
    assert div_round_half_up(-3, 2) == -2  # -1.5 -> -2
    assert div_round_half_up(-1, 2) == -1  # -0.5 -> -1


def test_div_round_half_up_negative_denominator() -> None:
    assert div_round_half_up(5, -2) == -3
    assert div_round_half_up(-5, -2) == 3


def test_div_round_half_up_zero_denominator() -> None:
    with pytest.raises(ZeroDivisionError):
        div_round_half_up(1, 0)


def test_clamp_non_negative() -> None:
    assert clamp_non_negative(5) == 5
    assert clamp_non_negative(0) == 0
    assert clamp_non_negative(-10) == 0
