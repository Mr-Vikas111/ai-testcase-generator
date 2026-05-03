"""FastAPI routes for webhook processing."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.core import sanitize
from app.patterns.builders import BatchAcceptedResponseBuilder
from app.schemas import WebhookPayload
from app.services import WebhookFacade

import logging
log = logging.getLogger(__name__)


def create_router(facade: WebhookFacade) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, Any]:
        return facade.health()

    @router.get("/results/{batch_id}")
    def get_results(batch_id: str) -> dict[str, Any]:
        entry = facade.get_results(batch_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Unknown batch_id: {batch_id}")
        return entry

    @router.get("/batches")
    def list_batches(limit: int = Query(default=50, ge=1, le=500)) -> dict[str, Any]:
        return facade.list_batches(limit=limit)

    @router.get("/admin/cleanup")
    def cleanup(days: int = Query(default=7, ge=1, le=365)) -> dict[str, Any]:
        return facade.cleanup(days=days)

    @router.post("/webhook")
    def webhook(payload: WebhookPayload, request: Request) -> dict[str, Any]:
        if not payload.requests:
            raise HTTPException(status_code=400, detail="'requests' must be a non-empty list")

        try:
            requests_list, filter_report = facade.validate_payload(payload.requests)
        except sanitize.ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if not requests_list:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "No usable requests after validation (all dropped)",
                    "filter": filter_report,
                },
            )

        client_ip = request.client.host if request.client else "unknown"
        body_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        batch_id = facade.create_batch(
            body=body_dict,
            requests_list=requests_list,
            filter_report=filter_report,
            client_ip=client_ip,
        )

        host = request.headers.get("host", "127.0.0.1:5055")
        results_url = f"http://{host}/results/{batch_id}"
        log.info("[Webhook] Batch %s accepted — results will be available at %s", batch_id, results_url)
        facade.start_background(batch_id, requests_list)

        methods = facade.methods_counter(requests_list)

        return (
            BatchAcceptedResponseBuilder()
            .with_batch(batch_id=batch_id, results_url=results_url)
            .with_total(len(requests_list))
            .with_filter(filter_report)
            .with_methods(methods)
            .build()
        )

    return router
