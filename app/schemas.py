"""Pydantic schemas for FastAPI request/response contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WebhookPayload(BaseModel):
    """Incoming payload from the browser extension."""

    requests: list[dict[str, Any]] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Server health response model."""

    status: str
    server: str
    ollama_model: str
    ollama_models: list[str]
    storage: str
