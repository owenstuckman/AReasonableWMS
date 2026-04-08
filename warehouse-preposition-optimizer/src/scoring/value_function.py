"""Movement value function: V(m) = (T_saved * P_load * W_order) / (C_move + C_opportunity)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.config import ResourceConfig
from src.models.inventory import Location
from src.models.movements import CandidateMovement
from src.models.orders import CarrierAppointment, OutboundOrder
from src.scoring.demand_predictor import DemandPredictor
from src.scoring.weights import ScoringWeights

_ORDER_WEIGHT_MIN = 0.1
_ORDER_WEIGHT_MAX = 10.0


@dataclass
class ScoringContext:
    """Context data required to score a candidate movement.

    Args:
        orders: Outbound orders within the planning horizon.
        appointments: Carrier appointments within the planning horizon.
        resource_utilization: Current fleet utilization fraction [0.0, 1.0].
    """

    orders: list[OutboundOrder] = field(default_factory=list)
    appointments: list[CarrierAppointment] = field(default_factory=list)
    resource_utilization: float = 0.0


class MovementScorer:
    """Computes value function scores for candidate movements.

    Implements V(m) = (T_saved * P_load * W_order) / (C_move + C_opportunity)
    where each term is weighted by the ScoringWeights configuration.

    Args:
        weights: Scoring weight configuration.
        config: Physical resource configuration for cost estimates.
    """

    def __init__(self, weights: ScoringWeights, config: ResourceConfig) -> None:
        self._weights = weights
        self._config = config
        self._predictor = DemandPredictor()

    def score(
        self, candidate: CandidateMovement, context: ScoringContext
    ) -> float:
        """Compute V(m) for a candidate movement and store components on the candidate.

        Short-circuits to 0.0 if T_saved <= 0 (movement won't save time) or
        P_load == 0.0 (SKU won't load on any appointment in the window).

        Args:
            candidate: The candidate movement to score. score_components is populated.
            context: Scoring context with orders, appointments, and utilization.

        Returns:
            The computed score V(m), or 0.0 if the movement is not beneficial.
        """
        # Find the best appointment for this SKU to determine P_load and W_order
        best_appointment: CarrierAppointment | None = None
        best_p_load = 0.0
        best_w_order = 0.0

        for appointment in context.appointments:
            p_load = self._compute_load_probability(
                candidate.sku_id, appointment, context.orders
            )
            if p_load > 0.0:
                # Find the highest-priority order for this appointment
                for order in context.orders:
                    if order.appointment.appointment_id == appointment.appointment_id:
                        w_order = self._compute_order_weight(order)
                        if w_order > best_w_order or best_appointment is None:
                            best_appointment = appointment
                            best_p_load = p_load
                            best_w_order = w_order

        if best_appointment is None or best_p_load == 0.0:
            candidate.score_components = {
                "t_saved": 0.0,
                "p_load": 0.0,
                "w_order": 0.0,
                "c_move": 0.0,
                "c_opportunity": 0.0,
            }
            candidate.score = 0.0
            return 0.0

        # Determine dock door coordinates from the appointment's dock door
        dock_door_x, dock_door_y = _dock_door_coords(best_appointment.dock_door)

        t_saved = self._compute_time_saved(
            candidate.from_location,
            candidate.to_location,
            dock_door_x,
            dock_door_y,
        )

        if t_saved <= 0.0:
            candidate.score_components = {
                "t_saved": t_saved,
                "p_load": best_p_load,
                "w_order": best_w_order,
                "c_move": 0.0,
                "c_opportunity": 0.0,
            }
            candidate.score = 0.0
            return 0.0

        c_move = self._compute_movement_cost(candidate.from_location, candidate.to_location)
        c_opportunity = self._compute_opportunity_cost(context.resource_utilization)

        denominator = (
            self._weights.movement_cost * c_move
            + self._weights.opportunity_cost * c_opportunity
        )
        if denominator <= 0.0:
            denominator = 1.0

        numerator = (
            self._weights.time_saved * t_saved
            * self._weights.load_probability * best_p_load
            * self._weights.order_priority * best_w_order
        )

        score = numerator / denominator

        candidate.score_components = {
            "t_saved": t_saved,
            "p_load": best_p_load,
            "w_order": best_w_order,
            "c_move": c_move,
            "c_opportunity": c_opportunity,
            "numerator": numerator,
            "denominator": denominator,
        }
        candidate.score = score
        return score

    def _compute_time_saved(
        self,
        from_loc: Location,
        to_loc: Location,
        dock_door_x: float,
        dock_door_y: float,
    ) -> float:
        """Compute seconds saved by moving SKU closer to dock door.

        Uses Manhattan distance difference converted to seconds at forklift speed.

        Args:
            from_loc: Current location of the SKU.
            to_loc: Proposed staging location.
            dock_door_x: X coordinate of the target dock door.
            dock_door_y: Y coordinate of the target dock door.

        Returns:
            Seconds saved (positive means the move saves time). Can be negative.
        """
        dist_from = abs(from_loc.x - dock_door_x) + abs(from_loc.y - dock_door_y)
        dist_to = abs(to_loc.x - dock_door_x) + abs(to_loc.y - dock_door_y)
        distance_saved = dist_from - dist_to
        return distance_saved / self._config.forklift_speed_mps

    def _compute_load_probability(
        self,
        sku_id: str,
        appointment: CarrierAppointment,
        orders: list[OutboundOrder],
    ) -> float:
        """Delegate to DemandPredictor for load probability.

        Args:
            sku_id: SKU identifier.
            appointment: Target carrier appointment.
            orders: All outbound orders in the horizon.

        Returns:
            Probability in [0.0, 1.0].
        """
        return self._predictor.predict(sku_id, appointment, orders)

    def _compute_order_weight(self, order: OutboundOrder) -> float:
        """Compute urgency-weighted order priority.

        W_order = priority * exp(-time_until_cutoff / decay_constant), clamped to [0.1, 10.0].

        Args:
            order: The outbound order.

        Returns:
            Urgency weight in [0.1, 10.0].
        """
        now = datetime.now(UTC)
        cutoff = order.cutoff_time
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=UTC)

        time_until_cutoff = (cutoff - now).total_seconds()
        decay = math.exp(-time_until_cutoff / self._weights.decay_constant_seconds)
        raw_weight = order.priority * decay
        return max(_ORDER_WEIGHT_MIN, min(_ORDER_WEIGHT_MAX, raw_weight))

    def _compute_movement_cost(
        self, from_loc: Location, to_loc: Location
    ) -> float:
        """Compute total time cost of executing the movement in seconds.

        Args:
            from_loc: Origin location.
            to_loc: Destination location.

        Returns:
            Travel time + handling time in seconds.
        """
        distance = abs(from_loc.x - to_loc.x) + abs(from_loc.y - to_loc.y)
        travel_time = distance / self._config.forklift_speed_mps
        return travel_time + self._config.handling_time_seconds

    def _compute_opportunity_cost(self, resource_utilization: float) -> float:
        """Compute opportunity cost based on fleet utilization.

        Formula: base * (1 / (1 - min(util, 0.95)))
        High utilization makes each resource more expensive to commit.

        Args:
            resource_utilization: Current fleet utilization [0.0, 1.0].

        Returns:
            Opportunity cost in seconds.
        """
        capped_util = min(resource_utilization, 0.95)
        return self._config.base_opportunity_seconds * (1.0 / (1.0 - capped_util))


def _dock_door_coords(dock_door: int) -> tuple[float, float]:
    """Return approximate (x, y) coordinates for a dock door.

    In a real deployment, dock door coordinates would come from the WMS.
    This stub places dock doors at x=0 and y = door_number * 5 meters.

    Args:
        dock_door: Dock door number.

    Returns:
        (x, y) coordinate tuple in meters.
    """
    return 0.0, float(dock_door) * 5.0
