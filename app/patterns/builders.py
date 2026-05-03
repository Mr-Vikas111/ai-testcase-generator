"""Builder pattern implementations for API response objects."""

from __future__ import annotations

from typing import Any


class BatchAcceptedResponseBuilder:
    """Builds the webhook accepted response in a fluent style."""

    def __init__(self) -> None:
        self._body: dict[str, Any] = {
            "ok": True,
            "batch_id": None,
            "results_url": None,
            "total": 0,
            "filter": {},
            "methods": {},
        }

    def with_batch(self, batch_id: str, results_url: str) -> "BatchAcceptedResponseBuilder":
        self._body["batch_id"] = batch_id
        self._body["results_url"] = results_url
        return self

    def with_total(self, total: int) -> "BatchAcceptedResponseBuilder":
        self._body["total"] = total
        return self

    def with_filter(self, filter_report: dict[str, Any]) -> "BatchAcceptedResponseBuilder":
        self._body["filter"] = filter_report
        return self

    def with_methods(self, methods: dict[str, int]) -> "BatchAcceptedResponseBuilder":
        self._body["methods"] = methods
        return self

    def build(self) -> dict[str, Any]:
        return dict(self._body)
