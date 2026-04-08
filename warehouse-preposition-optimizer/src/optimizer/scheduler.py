"""Pre-positioning scheduler: full pipeline from WMS state to dispatched tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from src.constraints.feasibility import FeasibilityEngine
from src.dispatch.task_queue import TaskQueue
from src.ingestion.wms_adapter import WMSAdapter, WarehouseState
from src.models.inventory import InventoryPosition, Location
from src.models.movements import CandidateMovement, MovementTask
from src.scoring.value_function import MovementScorer, ScoringContext

logger = structlog.get_logger(__name__)


@dataclass
class SchedulerConfig:
    """Configuration for the pre-positioning scheduler.

    Args:
        cycle_interval_seconds: Time between scheduling cycles.
        dispatch_batch_size: Number of tasks to dispatch per cycle.
        horizon_hours: Planning horizon for order lookups.
        max_candidates: Maximum candidates to evaluate per cycle.
        min_score_threshold: Minimum score to include a candidate.
    """

    cycle_interval_seconds: int = 60
    dispatch_batch_size: int = 5
    horizon_hours: float = 24.0
    max_candidates: int = 50
    min_score_threshold: float = 0.1


def _manhattan_distance(loc_a: Location, loc_b: Location) -> float:
    """Compute Manhattan distance between two locations.

    Args:
        loc_a: First location.
        loc_b: Second location.

    Returns:
        Manhattan distance in meters.
    """
    return abs(loc_a.x - loc_b.x) + abs(loc_a.y - loc_b.y)


def _find_best_staging_location(
    position: InventoryPosition,
    dock_door: int,
    staging_locations: list[Location],
) -> Location | None:
    """Find the best staging location for a position relative to a dock door.

    Prefers staging locations assigned to the target dock door. Falls back
    to the closest staging location by Manhattan distance.

    Args:
        position: The inventory position to be moved.
        dock_door: The dock door number for the target appointment.
        staging_locations: All available staging locations.

    Returns:
        Best staging location, or None if no staging locations available.
    """
    if not staging_locations:
        return None

    # First: staging locations assigned to this dock door
    door_locations = [
        loc for loc in staging_locations if loc.nearest_dock_door == dock_door
    ]

    if door_locations:
        return min(door_locations, key=lambda loc: _manhattan_distance(position.location, loc))

    # Fallback: closest staging location overall
    return min(staging_locations, key=lambda loc: _manhattan_distance(position.location, loc))


class PrePositionScheduler:
    """Runs the full pre-positioning pipeline: fetch → generate → filter → score → dispatch.

    Args:
        scorer: Movement scoring engine.
        feasibility: Constraint feasibility engine.
        wms: WMS adapter for state retrieval.
        task_queue: Redis-backed task queue for dispatching.
        config: Scheduler configuration parameters.
    """

    def __init__(
        self,
        scorer: MovementScorer,
        feasibility: FeasibilityEngine,
        wms: WMSAdapter,
        task_queue: TaskQueue,
        config: SchedulerConfig,
    ) -> None:
        self._scorer = scorer
        self._feasibility = feasibility
        self._wms = wms
        self._task_queue = task_queue
        self._config = config

    async def generate_candidates(self) -> list[CandidateMovement]:
        """Run the full candidate generation pipeline.

        Steps:
        1. Fetch warehouse state from WMS.
        2. Generate (inventory_position, staging_location) pairs per appointment.
        3. Filter infeasible movements via constraint engine.
        4. Score each feasible candidate.
        5. Deduplicate (keep highest score per SKU).
        6. Return top N by score.

        Returns:
            Scored, feasible, deduplicated candidates sorted by score descending.
        """
        state = await self._wms.get_warehouse_state(self._config.horizon_hours)

        if not state.appointments:
            logger.info("scheduler.no_appointments")
            return []

        context = ScoringContext(
            orders=state.outbound_orders,
            appointments=state.appointments,
            resource_utilization=_compute_avg_utilization(state.resource_utilization),
        )

        candidates: list[CandidateMovement] = []

        for appointment in state.appointments:
            for position in state.inventory_positions:
                staging_loc = _find_best_staging_location(
                    position, appointment.dock_door, state.staging_locations
                )
                if staging_loc is None:
                    continue

                # Skip if already at a staging location for this door
                if (
                    position.location.is_staging
                    and position.location.nearest_dock_door == appointment.dock_door
                ):
                    continue

                # Skip if source and target are the same
                if position.location.location_id == staging_loc.location_id:
                    continue

                candidate = CandidateMovement(
                    sku_id=position.sku.sku_id,
                    from_location=position.location,
                    to_location=staging_loc,
                    reason=(
                        f"Pre-stage for appointment {appointment.appointment_id} "
                        f"at dock door {appointment.dock_door}"
                    ),
                )

                # Check feasibility first (hard constraints)
                feasibility_result = self._feasibility.evaluate(candidate, state)
                if not feasibility_result.feasible:
                    logger.debug(
                        "scheduler.candidate_infeasible",
                        sku_id=candidate.sku_id,
                        violations=[v.description for v in feasibility_result.violations],
                    )
                    continue

                # Score the candidate
                score = self._scorer.score(candidate, context)
                if score < self._config.min_score_threshold:
                    continue

                candidates.append(candidate)

        # Deduplicate: keep highest score per SKU
        best_by_sku: dict[str, CandidateMovement] = {}
        for candidate in candidates:
            existing = best_by_sku.get(candidate.sku_id)
            if existing is None or candidate.score > existing.score:
                best_by_sku[candidate.sku_id] = candidate

        deduped = sorted(best_by_sku.values(), key=lambda c: c.score, reverse=True)
        top_n = deduped[: self._config.max_candidates]

        logger.info(
            "scheduler.candidates_generated",
            count=len(top_n),
            total_evaluated=len(candidates),
        )
        return top_n

    async def dispatch_top_movements(self, n: int = 5) -> list[MovementTask]:
        """Generate candidates and dispatch the top N as tasks.

        Args:
            n: Number of top candidates to dispatch.

        Returns:
            List of dispatched MovementTask instances.
        """
        candidates = await self.generate_candidates()
        top = candidates[:n]
        tasks: list[MovementTask] = []

        for candidate in top:
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
            await self._task_queue.push(task)
            tasks.append(task)
            logger.info(
                "scheduler.task_dispatched",
                movement_id=str(task.movement_id),
                sku_id=task.sku_id,
                score=round(task.score, 4),
            )

        return tasks

    async def run_cycle(
        self,
    ) -> tuple[list[CandidateMovement], list[MovementTask]]:
        """Run one full scheduling cycle.

        Generates candidates, dispatches the top batch, and returns both.

        Returns:
            Tuple of (all_candidates, dispatched_tasks).
        """
        logger.info("scheduler.cycle_start")
        candidates = await self.generate_candidates()
        tasks: list[MovementTask] = []

        top = candidates[: self._config.dispatch_batch_size]
        for candidate in top:
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
            await self._task_queue.push(task)
            tasks.append(task)

        logger.info(
            "scheduler.cycle_complete",
            candidates=len(candidates),
            dispatched=len(tasks),
        )
        return candidates, tasks


def _compute_avg_utilization(resource_utilization: dict[str, float]) -> float:
    """Compute average resource utilization across the fleet.

    Args:
        resource_utilization: Map of resource_id to utilization fraction.

    Returns:
        Average utilization, or 0.0 if no resources reported.
    """
    if not resource_utilization:
        return 0.0
    return sum(resource_utilization.values()) / len(resource_utilization)
