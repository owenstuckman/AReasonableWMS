"""Movement candidate and task management endpoints."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Request

from src.models.movements import CandidateMovement, MovementStatus, MovementTask

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/movements", tags=["movements"])


def _get_scheduler(request: Request) -> Any:
    """Extract scheduler from app state.

    Args:
        request: FastAPI request object.

    Returns:
        PrePositionScheduler instance.
    """
    return request.app.state.scheduler


def _get_task_queue(request: Request) -> Any:
    """Extract task queue from app state.

    Args:
        request: FastAPI request object.

    Returns:
        TaskQueue instance.
    """
    return request.app.state.task_queue


@router.get("/candidates", response_model=list[CandidateMovement])
async def get_candidates(
    scheduler: Annotated[Any, Depends(_get_scheduler)],
) -> list[CandidateMovement]:
    """Generate and return scored movement candidates.

    Returns:
        List of CandidateMovement instances sorted by score descending.
    """
    candidates = await scheduler.generate_candidates()
    return candidates


@router.post("/{movement_id}/approve", response_model=MovementTask)
async def approve_movement(
    movement_id: UUID,
    scheduler: Annotated[Any, Depends(_get_scheduler)],
    task_queue: Annotated[Any, Depends(_get_task_queue)],
) -> MovementTask:
    """Approve a candidate movement and dispatch it as a task.

    Args:
        movement_id: UUID of the candidate movement to approve.

    Returns:
        The dispatched MovementTask.
    """
    candidates = await scheduler.generate_candidates()
    candidate = next(
        (c for c in candidates if c.movement_id == movement_id), None
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate {movement_id} not found.")

    from datetime import UTC, datetime

    task = MovementTask(
        movement_id=candidate.movement_id,
        sku_id=candidate.sku_id,
        from_location=candidate.from_location,
        to_location=candidate.to_location,
        score=candidate.score,
        score_components=candidate.score_components,
        reason=candidate.reason,
        estimated_duration_seconds=candidate.estimated_duration_seconds,
        assigned_resource="UNASSIGNED",
        dispatched_at=datetime.now(UTC),
    )
    await task_queue.push(task)
    logger.info("movement.approved", movement_id=str(movement_id))
    return task


@router.post("/{movement_id}/reject")
async def reject_movement(
    movement_id: UUID,
    reason: Annotated[str, Body(embed=True)],
) -> dict[str, str]:
    """Record a rejection for a candidate movement.

    Args:
        movement_id: UUID of the candidate movement to reject.
        reason: Human-readable reason for rejection.

    Returns:
        Confirmation dictionary.
    """
    logger.info("movement.rejected", movement_id=str(movement_id), reason=reason)
    return {"status": "rejected", "movement_id": str(movement_id), "reason": reason}


@router.get("/active", response_model=list[MovementTask])
async def get_active_tasks(
    task_queue: Annotated[Any, Depends(_get_task_queue)],
) -> list[MovementTask]:
    """Return all currently active movement tasks.

    Returns:
        List of active MovementTask instances.
    """
    return await task_queue.get_active_tasks()


@router.get("/explain/{movement_id}")
async def explain_score(
    movement_id: UUID,
    scheduler: Annotated[Any, Depends(_get_scheduler)],
) -> dict[str, Any]:
    """Return detailed score breakdown for a candidate movement.

    Args:
        movement_id: UUID of the candidate to explain.

    Returns:
        Dictionary with score, score_components, and reason.
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
