"""Generic PostgreSQL WMS adapter with Redis caching."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.ingestion.wms_adapter import WMSAdapter
from src.models.inventory import (
    ABCClass,
    HazmatClass,
    InventoryPosition,
    Location,
    SKU,
    TemperatureZone,
)
from src.models.orders import AppointmentStatus, CarrierAppointment, OrderLine, OutboundOrder

logger = structlog.get_logger(__name__)

# Default column mappings from DB columns to model fields
_DEFAULT_TABLE_NAMES: dict[str, str] = {
    "locations": "locations",
    "skus": "skus",
    "inventory_positions": "inventory_positions",
    "carrier_appointments": "carrier_appointments",
    "outbound_orders": "outbound_orders",
    "order_lines": "order_lines",
}


def _parse_datetime(value: Any) -> datetime:
    """Parse a datetime value from DB row.

    Args:
        value: Raw datetime value from DB.

    Returns:
        UTC-aware datetime.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    return datetime.fromisoformat(str(value)).replace(tzinfo=UTC)


def _row_to_location(row: Any) -> Location:
    """Convert a DB row mapping to a Location model.

    Args:
        row: Row mapping from SQLAlchemy result.

    Returns:
        Location model instance.
    """
    return Location(
        location_id=str(row["location_id"]),
        zone=str(row["zone"]),
        aisle=int(row["aisle"]),
        bay=int(row["bay"]),
        level=int(row["level"]),
        x=float(row["x"]),
        y=float(row["y"]),
        temperature_zone=TemperatureZone(row.get("temperature_zone", "AMBIENT")),
        max_weight_kg=float(row.get("max_weight_kg", 2000.0)),
        max_volume_m3=float(row.get("max_volume_m3", 10.0)),
        is_staging=bool(row.get("is_staging", False)),
        nearest_dock_door=row.get("nearest_dock_door"),
    )


def _row_to_sku(row: Any) -> SKU:
    """Convert a DB row mapping to a SKU model.

    Args:
        row: Row mapping from SQLAlchemy result.

    Returns:
        SKU model instance.
    """
    hazmat_raw = row.get("hazmat_class")
    hazmat_class = HazmatClass(hazmat_raw) if hazmat_raw else None
    return SKU(
        sku_id=str(row["sku_id"]),
        description=str(row.get("description", "")),
        weight_kg=float(row.get("weight_kg", 0.0)),
        volume_m3=float(row.get("volume_m3", 0.0)),
        hazmat_class=hazmat_class,
        requires_temperature_zone=TemperatureZone(
            row.get("requires_temperature_zone", "AMBIENT")
        ),
        abc_class=ABCClass(row.get("abc_class", "C")),
    )


class GenericDBAdapter(WMSAdapter):
    """WMS adapter that reads from PostgreSQL with Redis caching.

    Args:
        database_url: Async SQLAlchemy database URL.
        redis_client: Connected redis.asyncio.Redis client.
        cache_ttl_seconds: How long to cache results in Redis.
        table_names: Optional overrides for table name mapping.
    """

    def __init__(
        self,
        database_url: str,
        redis_client: Any,
        cache_ttl_seconds: int = 60,
        table_names: dict[str, str] | None = None,
    ) -> None:
        self._database_url = database_url
        self._redis = redis_client
        self._cache_ttl = cache_ttl_seconds
        self._tables = {**_DEFAULT_TABLE_NAMES, **(table_names or {})}
        self._engine: AsyncEngine | None = None
        self._session_factory: Any = None

    async def connect(self) -> None:
        """Initialize the database connection pool.

        Returns:
            None
        """
        self._engine = create_async_engine(self._database_url, pool_size=5, max_overflow=10)
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("generic_db_adapter.connected", database_url=self._database_url)

    async def disconnect(self) -> None:
        """Close the database connection pool.

        Returns:
            None
        """
        if self._engine:
            await self._engine.dispose()
            logger.info("generic_db_adapter.disconnected")

    async def _get_cached(self, key: str) -> Any | None:
        """Retrieve a cached JSON value from Redis.

        Args:
            key: Cache key.

        Returns:
            Deserialized value or None if not cached.
        """
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("cache.get_failed", key=key, error=str(exc))
        return None

    async def _set_cached(self, key: str, value: Any) -> None:
        """Store a JSON-serializable value in Redis with TTL.

        Args:
            key: Cache key.
            value: JSON-serializable value.

        Returns:
            None
        """
        if self._redis is None:
            return
        try:
            await self._redis.setex(key, self._cache_ttl, json.dumps(value, default=str))
        except Exception as exc:
            logger.warning("cache.set_failed", key=key, error=str(exc))

    def _get_session(self) -> AsyncSession:
        """Create a new async database session.

        Returns:
            AsyncSession instance.
        """
        if self._session_factory is None:
            raise RuntimeError("Adapter not connected. Call connect() first.")
        return self._session_factory()

    async def get_inventory_positions(
        self, zone: str | None = None
    ) -> list[InventoryPosition]:
        """Fetch inventory positions from DB, with Redis caching.

        Args:
            zone: Optional zone filter.

        Returns:
            List of InventoryPosition instances.
        """
        cache_key = f"wms:inventory:{zone or 'all'}"
        cached = await self._get_cached(cache_key)
        if cached is not None:
            logger.debug("cache.hit", key=cache_key)
            return [InventoryPosition.model_validate(item) for item in cached]

        t0 = time.perf_counter()
        locs_tbl = self._tables["locations"]
        skus_tbl = self._tables["skus"]
        inv_tbl = self._tables["inventory_positions"]

        zone_clause = "AND l.zone = :zone" if zone else ""
        query = text(f"""
            SELECT
                ip.position_id,
                ip.quantity,
                ip.lot_number,
                ip.expiry_date,
                l.location_id, l.zone, l.aisle, l.bay, l.level, l.x, l.y,
                l.temperature_zone, l.max_weight_kg, l.max_volume_m3,
                l.is_staging, l.nearest_dock_door,
                s.sku_id, s.description, s.weight_kg, s.volume_m3,
                s.hazmat_class, s.requires_temperature_zone, s.abc_class
            FROM {inv_tbl} ip
            JOIN {locs_tbl} l ON ip.location_id = l.location_id
            JOIN {skus_tbl} s ON ip.sku_id = s.sku_id
            {zone_clause}
        """)

        positions: list[InventoryPosition] = []
        async with self._get_session() as session:
            params: dict[str, Any] = {}
            if zone:
                params["zone"] = zone
            result = await session.execute(query, params)
            rows = result.mappings().all()

        duration = time.perf_counter() - t0
        logger.info(
            "wms.poll",
            table="inventory_positions",
            rows=len(rows),
            duration_seconds=round(duration, 3),
        )

        for row in rows:
            loc = _row_to_location(row)
            sku = _row_to_sku(row)
            positions.append(
                InventoryPosition(
                    position_id=str(row["position_id"]),
                    sku=sku,
                    location=loc,
                    quantity=int(row["quantity"]),
                    lot_number=row.get("lot_number"),
                    expiry_date=_parse_datetime(row["expiry_date"]) if row.get("expiry_date") else None,
                )
            )

        await self._set_cached(cache_key, [p.model_dump(mode="json") for p in positions])
        return positions

    async def get_outbound_orders(
        self, horizon_hours: float = 24
    ) -> list[OutboundOrder]:
        """Fetch outbound orders with cutoff within horizon.

        Args:
            horizon_hours: Planning horizon in hours.

        Returns:
            List of OutboundOrder instances.
        """
        cache_key = f"wms:orders:{int(horizon_hours)}"
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return [OutboundOrder.model_validate(item) for item in cached]

        t0 = time.perf_counter()
        cutoff = datetime.now(UTC) + timedelta(hours=horizon_hours)
        orders_tbl = self._tables["outbound_orders"]
        lines_tbl = self._tables["order_lines"]
        appts_tbl = self._tables["carrier_appointments"]

        query = text(f"""
            SELECT
                o.order_id, o.priority, o.cutoff_time,
                a.appointment_id, a.carrier, a.dock_door,
                a.scheduled_arrival, a.scheduled_departure, a.status AS appt_status,
                ol.line_id, ol.sku_id, ol.quantity, ol.picked
            FROM {orders_tbl} o
            JOIN {appts_tbl} a ON o.appointment_id = a.appointment_id
            JOIN {lines_tbl} ol ON ol.order_id = o.order_id
            WHERE o.cutoff_time <= :cutoff
            ORDER BY o.order_id, ol.line_id
        """)

        async with self._get_session() as session:
            result = await session.execute(query, {"cutoff": cutoff})
            rows = result.mappings().all()

        duration = time.perf_counter() - t0
        logger.info("wms.poll", table="outbound_orders", rows=len(rows), duration_seconds=round(duration, 3))

        orders_map: dict[str, OutboundOrder] = {}
        for row in rows:
            oid = str(row["order_id"])
            if oid not in orders_map:
                appt = CarrierAppointment(
                    appointment_id=str(row["appointment_id"]),
                    carrier=str(row["carrier"]),
                    dock_door=int(row["dock_door"]),
                    scheduled_arrival=_parse_datetime(row["scheduled_arrival"]),
                    scheduled_departure=_parse_datetime(row["scheduled_departure"]),
                    status=AppointmentStatus(row["appt_status"]),
                )
                orders_map[oid] = OutboundOrder(
                    order_id=oid,
                    appointment=appt,
                    lines=[],
                    priority=int(row["priority"]),
                    cutoff_time=_parse_datetime(row["cutoff_time"]),
                )
            orders_map[oid].lines.append(
                OrderLine(
                    line_id=str(row["line_id"]),
                    sku_id=str(row["sku_id"]),
                    quantity=int(row["quantity"]),
                    picked=bool(row["picked"]),
                )
            )

        orders = sorted(orders_map.values(), key=lambda o: o.cutoff_time)
        await self._set_cached(cache_key, [o.model_dump(mode="json") for o in orders])
        return orders

    async def get_carrier_appointments(
        self, horizon_hours: float = 24
    ) -> list[CarrierAppointment]:
        """Fetch carrier appointments within the planning horizon.

        Args:
            horizon_hours: Planning horizon in hours.

        Returns:
            List of CarrierAppointment instances sorted by scheduled_arrival.
        """
        cache_key = f"wms:appointments:{int(horizon_hours)}"
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return [CarrierAppointment.model_validate(item) for item in cached]

        t0 = time.perf_counter()
        cutoff = datetime.now(UTC) + timedelta(hours=horizon_hours)
        appts_tbl = self._tables["carrier_appointments"]

        query = text(f"""
            SELECT appointment_id, carrier, dock_door,
                   scheduled_arrival, scheduled_departure, status
            FROM {appts_tbl}
            WHERE scheduled_arrival <= :cutoff
            ORDER BY scheduled_arrival
        """)

        async with self._get_session() as session:
            result = await session.execute(query, {"cutoff": cutoff})
            rows = result.mappings().all()

        duration = time.perf_counter() - t0
        logger.info("wms.poll", table="carrier_appointments", rows=len(rows), duration_seconds=round(duration, 3))

        appointments = [
            CarrierAppointment(
                appointment_id=str(row["appointment_id"]),
                carrier=str(row["carrier"]),
                dock_door=int(row["dock_door"]),
                scheduled_arrival=_parse_datetime(row["scheduled_arrival"]),
                scheduled_departure=_parse_datetime(row["scheduled_departure"]),
                status=AppointmentStatus(row["status"]),
            )
            for row in rows
        ]

        await self._set_cached(cache_key, [a.model_dump(mode="json") for a in appointments])
        return appointments

    async def get_staging_locations(
        self, dock_door: int | None = None
    ) -> list[Location]:
        """Fetch staging locations, optionally for a specific dock door.

        Args:
            dock_door: Optional dock door filter.

        Returns:
            List of staging Location instances.
        """
        cache_key = f"wms:staging:{dock_door or 'all'}"
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return [Location.model_validate(item) for item in cached]

        locs_tbl = self._tables["locations"]
        door_clause = "AND nearest_dock_door = :dock_door" if dock_door else ""
        query = text(f"""
            SELECT location_id, zone, aisle, bay, level, x, y,
                   temperature_zone, max_weight_kg, max_volume_m3,
                   is_staging, nearest_dock_door
            FROM {locs_tbl}
            WHERE is_staging = TRUE {door_clause}
        """)

        params: dict[str, Any] = {}
        if dock_door:
            params["dock_door"] = dock_door

        async with self._get_session() as session:
            result = await session.execute(query, params)
            rows = result.mappings().all()

        locations = [_row_to_location(row) for row in rows]
        await self._set_cached(cache_key, [loc.model_dump(mode="json") for loc in locations])
        return locations

    async def get_location_utilization(self) -> dict[str, float]:
        """Compute fill fraction for each location based on current inventory.

        Returns:
            Map of location_id to utilization fraction [0.0, 1.0].
        """
        cache_key = "wms:utilization"
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        inv_tbl = self._tables["inventory_positions"]
        locs_tbl = self._tables["locations"]
        skus_tbl = self._tables["skus"]

        query = text(f"""
            SELECT
                l.location_id,
                l.max_weight_kg,
                l.max_volume_m3,
                COALESCE(SUM(ip.quantity * s.weight_kg), 0) AS total_weight,
                COALESCE(SUM(ip.quantity * s.volume_m3), 0) AS total_volume
            FROM {locs_tbl} l
            LEFT JOIN {inv_tbl} ip ON ip.location_id = l.location_id
            LEFT JOIN {skus_tbl} s ON s.sku_id = ip.sku_id
            GROUP BY l.location_id, l.max_weight_kg, l.max_volume_m3
        """)

        async with self._get_session() as session:
            result = await session.execute(query)
            rows = result.mappings().all()

        utilization: dict[str, float] = {}
        for row in rows:
            max_w = float(row["max_weight_kg"]) or 1.0
            max_v = float(row["max_volume_m3"]) or 1.0
            weight_util = float(row["total_weight"]) / max_w
            volume_util = float(row["total_volume"]) / max_v
            utilization[str(row["location_id"])] = min(1.0, max(weight_util, volume_util))

        await self._set_cached(cache_key, utilization)
        return utilization
