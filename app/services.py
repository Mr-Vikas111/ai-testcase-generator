"""Application services and orchestration logic."""

from __future__ import annotations

import threading
from collections import Counter
from typing import Any

from app.agents.orchestrator import AgentOrchestrator
from app.core import sanitize
from app.core import store as store_module
from app.integrations import ollama_client
from app.integrations.llm_adapter import AdapterFactory, LLMAdapter


class BatchProcessor:
    """Delegates batch execution to the AgentOrchestrator pipeline."""

    def __init__(
        self,
        db: store_module.BatchStore,
        model: str,
        adapter: LLMAdapter | None = None,
    ) -> None:
        self._db = db
        self._model = model
        self._orchestrator = AgentOrchestrator(model=model, db=db, adapter=adapter)

    def process_batch(self, batch_id: str, requests_list: list[dict[str, Any]]) -> None:
        """Delegate to the AgentOrchestrator (Generator → Executor → Analyst)."""
        self._orchestrator.run_batch(batch_id, requests_list)


class WebhookFacade:
    """Facade pattern: single entry point for webhook business operations."""

    def __init__(
        self,
        db: store_module.BatchStore,
        processor: BatchProcessor,
        model: str,
    ) -> None:
        self._db = db
        self._processor = processor
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "server": "ai-test-api webhook + Ollama runner (FastAPI)",
            "ollama_model": self._model,
            "ollama_models": ollama_client.list_models(),
            "storage": str(store_module.STORAGE_DIR),
        }

    def get_results(self, batch_id: str) -> dict[str, Any] | None:
        return self._db.get(batch_id) or self._db.get_from_disk(batch_id)

    def list_batches(self, limit: int) -> dict[str, Any]:
        batches = self._db.list_batches(limit=limit)
        return {"total": len(batches), "batches": batches}

    def cleanup(self, days: int) -> dict[str, Any]:
        removed = self._db.cleanup(max_age_days=days)
        return {"removed": removed, "max_age_days": days}

    def validate_payload(self, raw_requests: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return sanitize.filter_requests(raw_requests)

    def create_batch(
        self,
        body: dict[str, Any],
        requests_list: list[dict[str, Any]],
        filter_report: dict[str, Any],
        client_ip: str,
    ) -> str:
        return self._db.create_batch(body, requests_list, filter_report, client_ip)

    def methods_counter(self, requests_list: list[dict[str, Any]]) -> dict[str, int]:
        counter = Counter((r.get("method") or "?").upper() for r in requests_list)
        return dict(sorted(counter.items()))

    def start_background(self, batch_id: str, requests_list: list[dict[str, Any]]) -> None:
        worker = threading.Thread(
            target=self._processor.process_batch,
            args=(batch_id, requests_list),
            daemon=True,
        )
        worker.start()

    def recover_from_disk(self) -> int:
        return self._db.recover_from_disk()
