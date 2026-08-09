"""Trivial engine harness test — proves engine/domain imports work."""

from __future__ import annotations


def test_engine_and_domain_import() -> None:
    import app.domain  # noqa: F401
    import app.engine  # noqa: F401
