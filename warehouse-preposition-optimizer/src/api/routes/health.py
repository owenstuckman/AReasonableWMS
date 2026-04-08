"""Health and metrics endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Return system health status.

    Returns:
        Dictionary with status and component health indicators.
    """
    return {
        "status": "ok",
        "components": {
            "api": "ok",
        },
    }


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> PlainTextResponse:
    """Return Prometheus metrics in text exposition format.

    Returns:
        Prometheus-formatted metrics as plain text.
    """
    content = generate_latest()
    return PlainTextResponse(content=content, media_type=CONTENT_TYPE_LATEST)
