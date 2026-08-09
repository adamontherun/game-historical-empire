"""Deterministic RNG substreams via stable hash.

Spec: never use global random state. Derive substreams via BLAKE2b/SHA-256 over
canonical serialization of key material:

    run_seed, ruleset_version, turn, namespace, entity_id, ordinal

Canonical encoding is JSON array ``[run_seed, ruleset_version, turn, namespace,
entity_id, ordinal]`` with ``separators=(',',':')`` — unambiguous, length-
prefixed via JSON quoting, so delimiter-containing strings cannot collide
(e.g. ``\"a|b\"|\"c\"`` vs ``\"a\"|\"b|c\"`` yield distinct serializations).

Same inputs -> same int seed -> same random.Random sequence.
Different namespace -> different seed (verified by tests).
No use of built-in hash function.

All helpers are sync and import only hashlib/json/random/typing — no FastAPI/etc.
"""

from __future__ import annotations

import hashlib
import json
import random

# Canonical digest size: 8 bytes = 64-bit seed, fits Python Random int seed
# and keeps values within 2**63-1 for stability across Python versions.
_DIGEST_SIZE = 8
_SEED_MASK = (1 << 63) - 1


def derive_seed(
    run_seed: str,
    ruleset_version: str,
    turn: int,
    namespace: str,
    entity_id: str,
    ordinal: int = 0,
) -> int:
    """Derive deterministic int seed from key material via BLAKE2b.

    Canonical serialization is JSON array
    ``[run_seed, ruleset_version, turn, namespace, entity_id, ordinal]``
    with ``separators=(',',':')`` — unambiguous for delimiter-containing
    values. Uses ``hashlib.blake2b(digest_size=8)``.

    Args:
        run_seed: Opaque run seed (str), e.g. "seed-001".
        ruleset_version: Ruleset version string, e.g. "1.0".
        turn: Current turn number, non-negative.
        namespace: System namespace, e.g. "market", "rival".
        entity_id: Entity id, e.g. "home_valley", "mira".
        ordinal: Ordinal for multiple draws in same context.

    Returns:
        Deterministic int seed in [0, 2**63-1].
    """
    payload = [run_seed, ruleset_version, turn, namespace, entity_id, ordinal]
    canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.blake2b(canonical.encode("utf-8"), digest_size=_DIGEST_SIZE).hexdigest()
    return int(digest, 16) & _SEED_MASK


def make_rng(seed: int) -> random.Random:
    """Create isolated random.Random from int seed — no global state.

    Args:
        seed: Int seed from derive_seed.

    Returns:
        Isolated Random instance seeded deterministically.
    """
    return random.Random(seed)


def rng_for(
    run_seed: str,
    ruleset_version: str,
    turn: int,
    namespace: str,
    entity_id: str,
    ordinal: int = 0,
) -> random.Random:
    """Convenience: derive seed from key material and return Random.

    Args:
        run_seed: Opaque run seed.
        ruleset_version: Ruleset version.
        turn: Turn number.
        namespace: System namespace.
        entity_id: Entity id.
        ordinal: Ordinal.

    Returns:
        Deterministic Random for the given substream.
    """
    seed = derive_seed(run_seed, ruleset_version, turn, namespace, entity_id, ordinal)
    return make_rng(seed)
