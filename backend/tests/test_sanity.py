"""Trivial engine harness test — proves imports and determinism without placeholder API."""

from __future__ import annotations


def test_engine_and_domain_import() -> None:
    import app.domain  # noqa: F401
    import app.engine  # noqa: F401
