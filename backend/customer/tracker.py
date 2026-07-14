import logging
import random
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.customer.models import (
    Order,
    OrderItem,
    Shipment,
    ShipmentEvent,
    ShipmentStatus,
    ShippingAddress,
)

logger = logging.getLogger("gigacorp.customer.tracker")

TRACKING_STATUS_PATTERNS: dict[str, list[dict]] = {
    "ups": [
        {"delay_min": 0, "delay_max": 30, "status": ShipmentStatus.PRE_TRANSIT,
         "desc": "Shipping label created. UPS awaiting item."},
        {"delay_min": 30, "delay_max": 120, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Origin scan: package received at UPS facility."},
        {"delay_min": 120, "delay_max": 300, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Departed from origin facility. In transit to destination."},
        {"delay_min": 300, "delay_max": 600, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Arrived at regional sorting facility."},
        {"delay_min": 600, "delay_max": 1000, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Departed regional facility. Package is moving within UPS network."},
        {"delay_min": 1000, "delay_max": 2000, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Arrived at destination sort facility."},
        {"delay_min": 2000, "delay_max": 3000, "status": ShipmentStatus.OUT_FOR_DELIVERY,
         "desc": "Out for delivery with UPS driver."},
        {"delay_min": 3000, "delay_max": 99999, "status": ShipmentStatus.DELIVERED,
         "desc": "Delivered. Signed for by recipient."},
    ],
    "usps": [
        {"delay_min": 0, "delay_max": 60, "status": ShipmentStatus.PRE_TRANSIT,
         "desc": "USPS in possession of item. Pre-shipment stage."},
        {"delay_min": 60, "delay_max": 180, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Accepted at USPS origin facility."},
        {"delay_min": 180, "delay_max": 360, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Departed USPS regional facility."},
        {"delay_min": 360, "delay_max": 720, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "In transit to next facility. Your package is moving within the USPS network."},
        {"delay_min": 720, "delay_max": 1500, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Arrived at USPS destination facility."},
        {"delay_min": 1500, "delay_max": 2500, "status": ShipmentStatus.OUT_FOR_DELIVERY,
         "desc": "Out for delivery with USPS carrier."},
        {"delay_min": 2500, "delay_max": 99999, "status": ShipmentStatus.DELIVERED,
         "desc": "Delivered to individual. Mailbox or front door."},
    ],
    "dhl": [
        {"delay_min": 0, "delay_max": 60, "status": ShipmentStatus.PRE_TRANSIT,
         "desc": "Shipment information received by DHL."},
        {"delay_min": 60, "delay_max": 180, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Departed from DHL origin facility."},
        {"delay_min": 180, "delay_max": 480, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Processed at DHL hub. In transit."},
        {"delay_min": 480, "delay_max": 1000, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Customs clearance completed. In transit to destination."},
        {"delay_min": 1000, "delay_max": 2000, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Arrived at DHL destination facility."},
        {"delay_min": 2000, "delay_max": 3000, "status": ShipmentStatus.OUT_FOR_DELIVERY,
         "desc": "With DHL delivery courier. Out for delivery."},
        {"delay_min": 3000, "delay_max": 99999, "status": ShipmentStatus.DELIVERED,
         "desc": "Delivered. Signed for by recipient."},
    ],
    "fedex": [
        {"delay_min": 0, "delay_max": 45, "status": ShipmentStatus.PRE_TRANSIT,
         "desc": "Label created. FedEx awaits package."},
        {"delay_min": 45, "delay_max": 150, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Picked up. Package received at FedEx station."},
        {"delay_min": 150, "delay_max": 400, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Arrived at FedEx hub. In transit."},
        {"delay_min": 400, "delay_max": 900, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "Departed FedEx hub. Package in transit."},
        {"delay_min": 900, "delay_max": 1800, "status": ShipmentStatus.IN_TRANSIT,
         "desc": "At local FedEx facility. Sorting complete."},
        {"delay_min": 1800, "delay_max": 2800, "status": ShipmentStatus.OUT_FOR_DELIVERY,
         "desc": "On FedEx vehicle for delivery."},
        {"delay_min": 2800, "delay_max": 99999, "status": ShipmentStatus.DELIVERED,
         "desc": "Delivered. Left at front door."},
    ],
}

WAREHOUSE_LOCATIONS: list[str] = [
    "Warehouse A, Dallas, TX",
    "Warehouse B, Memphis, TN",
    "Warehouse C, Louisville, KY",
    "Distribution Center East, Edison, NJ",
    "Distribution Center West, Reno, NV",
    "Regional Hub, Chicago, IL",
    "Regional Hub, Atlanta, GA",
    "Sorting Facility, Kansas City, MO",
    "International Gateway, Los Angeles, CA",
    "International Gateway, New York, NY",
]

COURIER_NAMES: dict[str, str] = {
    "ups": "UPS",
    "usps": "USPS",
    "dhl": "DHL Express",
    "fedex": "FedEx",
}


class CourierTracker:
    def __init__(self, simulation_enabled: bool = True):
        self.simulation_enabled = simulation_enabled

    async def track(self, tracking_number: str, db: AsyncSession) -> Optional[dict]:
        result = await db.execute(
            select(Shipment).where(Shipment.tracking_number == tracking_number)
        )
        shipment = result.scalar_one_or_none()
        if not shipment:
            return None

        if self.simulation_enabled:
            await self._simulate_progress(shipment, db)

        return await self._build_response(shipment, db)

    async def track_by_order(self, order_id, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(Shipment).where(Shipment.order_id == order_id)
        )
        shipments = result.scalars().all()
        return [await self._build_response(s, db) for s in shipments]

    async def get_customer_shipments(self, customer_id, db: AsyncSession, limit: int = 10) -> list[dict]:
        result = await db.execute(
            select(Shipment).where(Shipment.customer_id == customer_id)
            .order_by(desc(Shipment.last_update)).limit(limit)
        )
        shipments = result.scalars().all()
        return [await self._build_response(s, db) for s in shipments]

    async def get_customer_tracking_context(self, customer_id, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(Shipment).where(Shipment.customer_id == customer_id)
            .order_by(desc(Shipment.last_update)).limit(5)
        )
        shipments = result.scalars().all()
        return [await self._build_lightweight_context(s, db) for s in shipments]

    async def _simulate_progress(self, shipment: Shipment, db: AsyncSession):
        if shipment.status == ShipmentStatus.DELIVERED:
            return

        now = datetime.utcnow()
        shipped_at = shipment.shipped_at or shipment.created_at
        elapsed_minutes = (now - shipped_at).total_seconds() / 60.0
        courier_code = shipment.courier_code or "ups"
        patterns = TRACKING_STATUS_PATTERNS.get(courier_code, TRACKING_STATUS_PATTERNS["ups"])

        new_locations = [
            loc for loc in WAREHOUSE_LOCATIONS
            if loc != shipment.origin_location
        ]

        for pattern in patterns:
            if pattern["delay_min"] <= elapsed_minutes < pattern["delay_max"]:
                target_status = pattern["status"]
                if target_status == shipment.status:
                    return

                event_time = now
                loc = random.choice(new_locations) if new_locations else None

                if target_status == ShipmentStatus.OUT_FOR_DELIVERY:
                    loc = "Local delivery route"

                event = ShipmentEvent(
                    shipment_id=shipment.id,
                    status=target_status.value,
                    location=loc,
                    description=pattern["desc"],
                    timestamp=event_time,
                )
                db.add(event)

                if target_status == ShipmentStatus.DELIVERED:
                    loc = (await self._get_destination_city(shipment, db)) or loc

                shipment.status = target_status
                shipment.current_location = loc
                shipment.last_update = event_time

                if target_status == ShipmentStatus.DELIVERED:
                    shipment.delivered_at = event_time

                await db.flush()
                logger.info("Shipment %s simulated: %s -> %s", shipment.tracking_number, shipment.status.value, target_status.value)
                return

    async def _get_destination_city(self, shipment: Shipment, db: AsyncSession) -> Optional[str]:
        if shipment.destination_address_id:
            result = await db.execute(
                select(ShippingAddress).where(ShippingAddress.id == shipment.destination_address_id)
            )
            addr = result.scalar_one_or_none()
            if addr:
                return f"{addr.city}, {addr.state or addr.country}"
        return None

    async def _build_response(self, shipment: Shipment, db: AsyncSession) -> dict:
        events_result = await db.execute(
            select(ShipmentEvent).where(ShipmentEvent.shipment_id == shipment.id)
            .order_by(ShipmentEvent.timestamp)
        )
        events = events_result.scalars().all()

        order_info = None
        if shipment.order_id:
            result = await db.execute(
                select(Order).where(Order.id == shipment.order_id)
            )
            order = result.scalar_one_or_none()
            if order:
                items_result = await db.execute(
                    select(OrderItem).where(OrderItem.order_id == order.id)
                )
                items = items_result.scalars().all()
                order_info = {
                    "order_number": order.order_number,
                    "items": [
                        {"product_name": i.product_name, "quantity": i.quantity}
                        for i in items
                    ],
                }

        return {
            "tracking_number": shipment.tracking_number,
            "courier": shipment.courier,
            "courier_code": shipment.courier_code,
            "status": shipment.status.value,
            "status_label": shipment.status.value.replace("_", " ").title(),
            "estimated_delivery": shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else None,
            "origin_location": shipment.origin_location,
            "current_location": shipment.current_location,
            "last_update": shipment.last_update.isoformat(),
            "shipped_at": shipment.shipped_at.isoformat() if shipment.shipped_at else None,
            "delivered_at": shipment.delivered_at.isoformat() if shipment.delivered_at else None,
            "weight_lb": float(shipment.weight_lb) if shipment.weight_lb else None,
            "package_count": shipment.package_count,
            "order": order_info,
            "timeline": [
                {
                    "status": e.status,
                    "status_label": e.status.replace("_", " ").title(),
                    "location": e.location,
                    "description": e.description,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in events
            ],
        }

    async def _build_lightweight_context(self, shipment: Shipment, db: AsyncSession) -> dict:
        return {
            "tracking_number": shipment.tracking_number,
            "courier": shipment.courier,
            "status": shipment.status.value,
            "status_label": shipment.status.value.replace("_", " ").title(),
            "estimated_delivery": shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else None,
            "current_location": shipment.current_location,
            "last_update": shipment.last_update.isoformat(),
            "order_number": (await self._get_order_number(shipment, db)),
        }

    async def _get_order_number(self, shipment: Shipment, db: AsyncSession) -> Optional[str]:
        if shipment.order_id:
            result = await db.execute(
                select(Order.order_number).where(Order.id == shipment.order_id)
            )
            return result.scalar_one_or_none()
        return None

    async def refresh_shipment(self, tracking_number: str, db: AsyncSession) -> Optional[dict]:
        result = await db.execute(
            select(Shipment).where(Shipment.tracking_number == tracking_number)
        )
        shipment = result.scalar_one_or_none()
        if not shipment:
            return None
        await self._simulate_progress(shipment, db)
        return await self._build_response(shipment, db)

    async def initialize_shipment(self, order: Order, customer_id, courier_code: str,
                                   tracking_number: str, db: AsyncSession) -> Shipment:
        courier_name = COURIER_NAMES.get(courier_code, courier_code.upper())
        origin = random.choice(WAREHOUSE_LOCATIONS)
        estimated = (datetime.utcnow() + timedelta(days=random.randint(3, 10)).date())

        shipment = Shipment(
            order_id=order.id,
            customer_id=customer_id,
            tracking_number=tracking_number,
            courier=courier_name,
            courier_code=courier_code,
            status=ShipmentStatus.PRE_TRANSIT,
            estimated_delivery=estimated,
            shipped_at=datetime.utcnow(),
            origin_location=origin,
            current_location=origin,
            last_update=datetime.utcnow(),
            destination_address_id=order.shipping_address_id,
        )
        db.add(shipment)
        await db.flush()

        initial_event = ShipmentEvent(
            shipment_id=shipment.id,
            status=ShipmentStatus.PRE_TRANSIT.value,
            location=origin,
            description=f"Shipping label created. {courier_name} awaiting item.",
            timestamp=datetime.utcnow(),
        )
        db.add(initial_event)
        await db.flush()

        return shipment
