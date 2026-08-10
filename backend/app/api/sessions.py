"""In-memory game sessions — Section 10.

Per-session asyncio.Lock so GET and POST on the same game cannot tear.
Unrelated games proceed independently — no global serialization.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.domain.types import PlayerCommand
from app.engine.prototype import FiveTurnGame


@dataclass
class GameSession:
    """Session envelope — revision lives here, not on GameState."""

    game_id: str
    run_seed: str
    revision: int
    game: FiveTurnGame
    created_at: str
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    # No revision_history — not needed, would be persistence scaffolding (C7).
    commands: list[PlayerCommand] = field(default_factory=list)


SESSION_STORE: dict[str, GameSession] = {}
