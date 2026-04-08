"""Scoring explanation endpoints (re-exported from movements for clarity)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/scoring", tags=["scoring"])


def _get_scheduler(request: Request) -> Any:
    """Extract scheduler from app state.

    Args:
        request: FastAPI request.

    Returns:
        PrePositionScheduler instance.
    """
    return request.app.state.scheduler


@router.get("/explain/{movement_id}")
async def explain_score(
    movement_id: UUID,
    scheduler: Annotated[Any, Depends(_get_scheduler)],
) -> dict[str, Any]:
    """Return detailed score breakdown for a candidate movement.

    Args:
        movement_id: UUID of the candidate to explain.

    Returns:
        Score breakdown dictionary.
    """
    candidates = await scheduler.generate_candidates()
    candidate = next(
        (c for c in candidates if c.movement_id == movement_id), None
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate {movement_id} not found.")

    return {
        "movement_id": str(movement_id),
        "sku_id": candidate.sku_id,
        "score": candidate.score,
        "score_components": candidate.score_components,
        "reason": candidate.reason,
        "from_location": candidate.from_location.location_id,
        "to_location": candidate.to_location.location_id,
    }
