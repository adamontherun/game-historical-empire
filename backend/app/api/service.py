"""Service functions — plain, no FastAPI Depends."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException

from app.api.mappers import choice_map_for, to_game_view
from app.api.schemas import CreateGameRequest, GameView
from app.api.sessions import SESSION_STORE, GameSession
from app.engine.prototype import FiveTurnGame


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def create_game(req: CreateGameRequest) -> GameView:
    run_seed = req.run_seed if req.run_seed is not None else uuid.uuid4().hex
    version = req.ruleset_version if req.ruleset_version is not None else "1.0"
    game_id = uuid.uuid4().hex
    game = FiveTurnGame(seed=run_seed, version=version)

    session = GameSession(
        game_id=game_id,
        run_seed=run_seed,
        revision=0,
        game=game,
        created_at=_now_iso(),
        lock=asyncio.Lock(),
    )
    SESSION_STORE[game_id] = session
    # No lock needed on create — just created
    return to_game_view(session)


async def get_game(game_id: str) -> GameView:
    session = SESSION_STORE.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="game not found")
    async with session.lock:
        return to_game_view(session)


async def choose(game_id: str, choice_id: str, expected_revision: int) -> GameView:
    session = SESSION_STORE.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="game not found")
    async with session.lock:
        if expected_revision != session.revision:
            raise HTTPException(
                status_code=409,
                detail=f"conflict: expected_revision {expected_revision} != current {session.revision}",
                headers={"X-Current-Revision": str(session.revision)},
            )
        # DECISIONS 021: yield inside lock keeps per-session lock load-bearing until real I/O lands (Section 16)
        await asyncio.sleep(0)
        if session.game.is_complete:
            raise HTTPException(status_code=409, detail="game complete")
        cmap = choice_map_for(session)
        cmd = cmap.get(choice_id)
        if cmd is None:
            raise HTTPException(status_code=404, detail=f"unknown choice_id {choice_id!r}")
        # Single mutation path — never resolve_turn separately (would double-advance)
        session.game.submit(cmd)
        session.commands.append(cmd)
        session.revision += 1
        return to_game_view(session)
