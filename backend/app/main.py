"""FastAPI app factory — Section 10 minimal boundary."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.router import router


def create_app() -> FastAPI:
    app = FastAPI(title="Historical Empire — Section 10")
    app.include_router(router)
    return app


app = create_app()
