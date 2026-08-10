"""Router — three endpoints only."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import CreateChoiceRequest, CreateGameRequest, GameView
from app.api.service import choose, create_game, get_game

router = APIRouter(prefix="/api/v1", tags=["games"])


@router.post("/games", response_model=GameView)
async def post_games(req: CreateGameRequest) -> GameView:
    return await create_game(req)


@router.get("/games/{game_id}", response_model=GameView)
async def get_games(game_id: str) -> GameView:
    return await get_game(game_id)


@router.post("/games/{game_id}/choices/{choice_id}", response_model=GameView)
async def post_choice(game_id: str, choice_id: str, body: CreateChoiceRequest) -> GameView:
    return await choose(game_id, choice_id, body.expected_revision)
