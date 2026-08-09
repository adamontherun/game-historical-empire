"""Gate 4: engine and domain must not import web/DB/LLM packages (AST check)."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_TOP_LEVEL = {"fastapi", "sqlalchemy", "httpx", "asyncpg", "openai", "clerk"}

ENGINE_DIR = Path(__file__).parent.parent / "app" / "engine"
DOMAIN_DIR = Path(__file__).parent.parent / "app" / "domain"


def _assert_no_forbidden_imports(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    if not source.strip():
        return
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                assert top not in FORBIDDEN_TOP_LEVEL, (
                    f"{path.name} imports forbidden top-level package '{top}'"
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            top = node.module.split(".")[0]
            assert top not in FORBIDDEN_TOP_LEVEL, (
                f"{path.name} imports from forbidden package '{top}'"
            )


def test_engine_source_contains_no_forbidden_imports() -> None:
    for root in (ENGINE_DIR, DOMAIN_DIR):
        for filepath in root.rglob("*.py"):
            _assert_no_forbidden_imports(filepath)


def test_engine_and_domain_import_without_forbidden_runtime_deps() -> None:
    # Importing the pure packages must not pull forbidden runtime deps transitively.
    # ruff/pyright ensure no direct imports; this guards transitive pulls.
    import importlib

    for name in ("app.engine", "app.domain"):
        importlib.import_module(name)

    import sys

    for mod in FORBIDDEN_TOP_LEVEL:
        assert mod not in sys.modules, f"importing pure package pulled in '{mod}'"
