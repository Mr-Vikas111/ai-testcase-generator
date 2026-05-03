"""Factory pattern for constructing app dependencies."""

from __future__ import annotations

import os

from app.core import config, store as store_module
from app.integrations import ollama_client
from app.integrations.llm_adapter import AdapterFactory, LLMAdapter
from app.services import BatchProcessor, WebhookFacade


class ServiceFactory:
    """Creates concrete services while keeping wiring centralized."""

    @staticmethod
    def create_model(explicit_model: str | None = None) -> str:
        return explicit_model or os.getenv("MODEL_OLLAMA", ollama_client.OLLAMA_MODEL)

    @staticmethod
    def create_store() -> store_module.BatchStore:
        return store_module.store

    @staticmethod
    def create_adapter(provider: str | None = None) -> LLMAdapter:
        """Build an LLMAdapter for the given provider (default: config.LLM_PROVIDER)."""
        return AdapterFactory.create(provider or config.LLM_PROVIDER)

    @classmethod
    def create_batch_processor(
        cls,
        explicit_model: str | None = None,
        provider: str | None = None,
    ) -> BatchProcessor:
        model = cls.create_model(explicit_model)
        adapter = cls.create_adapter(provider)
        return BatchProcessor(db=cls.create_store(), model=model, adapter=adapter)

    @classmethod
    def create_facade(
        cls,
        explicit_model: str | None = None,
        provider: str | None = None,
    ) -> WebhookFacade:
        model = cls.create_model(explicit_model)
        processor = cls.create_batch_processor(model, provider)
        return WebhookFacade(db=cls.create_store(), processor=processor, model=model)
