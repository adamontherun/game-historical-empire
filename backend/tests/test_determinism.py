"""Tests for deterministic RNG — AC #3, #4, #5."""

from __future__ import annotations

import ast
from pathlib import Path

from app.engine.rng import derive_seed, make_rng, rng_for


def test_derive_seed_stable_same_material() -> None:
    s1 = derive_seed("seed-001", "1.0", 1, "market", "home_valley", 0)
    s2 = derive_seed("seed-001", "1.0", 1, "market", "home_valley", 0)
    assert s1 == s2


def test_derive_seed_golden_values() -> None:
    # Golden values generated via blake2b(digest_size=8) over JSON canonical
    # [run_seed, ruleset_version, turn, namespace, entity_id, ordinal].
    assert derive_seed("seed-001", "1.0", 1, "market", "home_valley", 0) == 9000414367206956173
    assert derive_seed("seed-001", "1.0", 1, "market", "home_valley", 1) == 8070410502144384724
    assert derive_seed("seed-001", "1.0", 1, "rival", "mira", 0) == 6965261172636434297


def test_different_namespaces_produce_different_streams() -> None:
    a = derive_seed("seed-001", "1.0", 1, "market", "home_valley", 0)
    b = derive_seed("seed-001", "1.0", 1, "rival", "home_valley", 0)
    assert a != b


def test_different_turns_produce_different_seeds() -> None:
    a = derive_seed("seed-001", "1.0", 1, "market", "home_valley", 0)
    b = derive_seed("seed-001", "1.0", 2, "market", "home_valley", 0)
    assert a != b


def test_different_ordinals_produce_different_seeds() -> None:
    a = derive_seed("seed-001", "1.0", 1, "market", "home_valley", 0)
    b = derive_seed("seed-001", "1.0", 1, "market", "home_valley", 1)
    assert a != b


def test_different_entity_ids_produce_different_seeds() -> None:
    a = derive_seed("seed-001", "1.0", 1, "market", "home_valley", 0)
    b = derive_seed("seed-001", "1.0", 1, "market", "river_town", 0)
    assert a != b


def test_delimiter_collision_regression() -> None:
    """RNG serialization must not collide on delimiter-containing strings.

    Old naive '|'-join would give same canonical string for
    ('a|b','c') vs ('a','b|c'); JSON array encoding must distinguish them.
    """
    a = derive_seed("a|b", "c", 1, "ns", "e", 0)
    b = derive_seed("a", "b|c", 1, "ns", "e", 0)
    assert a != b

    c = derive_seed("ab", "1.0", 1, "c|d", "e", 0)
    d = derive_seed("ab|c", "1.0", 1, "d", "e", 0)
    assert c != d

    # Also ensure '|' inside a single field changes the seed
    e = derive_seed("seed|001", "1.0", 1, "market", "home_valley", 0)
    f = derive_seed("seed001", "1.0", 1, "market", "home_valley", 0)
    assert e != f


def test_make_rng_deterministic_sequence() -> None:
    seed = derive_seed("seed-001", "1.0", 1, "market", "home_valley", 0)
    r1 = make_rng(seed)
    r2 = make_rng(seed)
    assert [r1.randint(0, 1000) for _ in range(5)] == [r2.randint(0, 1000) for _ in range(5)]


def test_rng_for_convenience_same_as_derive() -> None:
    seed = derive_seed("seed-001", "1.0", 1, "market", "home_valley", 0)
    r1 = make_rng(seed)
    r2 = rng_for("seed-001", "1.0", 1, "market", "home_valley", 0)
    assert [r1.random() for _ in range(3)] == [r2.random() for _ in range(3)]


def test_no_global_random_usage_in_engine() -> None:
    """AC #5: engine must not use global random functions (all files)."""
    engine_dir = Path(__file__).parent.parent / "app" / "engine"
    for path in engine_dir.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if not source.strip():
            continue
        tree = ast.parse(source, filename=str(path))
        # Allowed: import random, random.Random
        # Forbidden: random.random(), random.randint(), etc. as globals
        # Also forbidden: from random import ...
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module != "random", (
                    f"{path.name} must not use 'from random import ...' (global state risk)"
                )
            if isinstance(node, ast.Attribute):
                # e.g. random.randint -> flag if Attribute under Name 'random' and not 'Random'
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "random"
                    and node.attr != "Random"
                ):
                    # Catch random.* not Random; make_rng uses Random ok
                    # Excluded Random above; other attrs forbidden
                    # hashlib etc are fine
                    raise AssertionError(
                        f"{path.name} must not use global random.{node.attr}"
                        " — use Random instance instead"
                    )
        # Also ensure no built-in hash() usage in engine files
        if "hash(" in source and "hashlib" not in source:
            raise AssertionError(f"{path.name} appears to use built-in hash() — forbidden")


def test_no_hash_builtin_in_domain_or_engine() -> None:
    """Ensure deterministic hash uses hashlib, not built-in hash()."""
    for sub in ("engine", "domain"):
        root = Path(__file__).parent.parent / "app" / sub
        for p in root.rglob("*.py"):
            src = p.read_text(encoding="utf-8")
            # Ignore comments and hashlib lines: simple check for ' hash(' pattern
            # This is a heuristic; proper AST check would be stricter but this suffices for AC #5.
            # We check that 'hash(' does not appear unless it's 'hashlib.'
            lines = src.splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "hashlib" in line:
                    continue
                assert "hash(" not in line, f"{p.name} appears to use built-in hash() — forbidden"
