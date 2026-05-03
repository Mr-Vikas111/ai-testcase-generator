"""FastAPI app bootstrap and lifecycle wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import create_router
from app.patterns.factory import ServiceFactory


def create_application(
    model: str | None = None,
    provider: str | None = None,
) -> FastAPI:
    facade = ServiceFactory.create_facade(explicit_model=model, provider=provider)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.facade = facade
        facade.recover_from_disk()
        facade.cleanup(days=7)
        yield

    app = FastAPI(
        title="AI Test API",
        description="Webhook + Ollama runner powered by FastAPI",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(create_router(facade))
    return app


app = create_application()
