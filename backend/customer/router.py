import logging
import time

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.database import get_db
from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.customer.service import CustomerService

logger = logging.getLogger("gigacorp.customer.router")


class CancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class ReturnRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    items: list[dict] = Field(default_factory=list)


class ExchangeRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    original_product: str = Field(..., min_length=1, max_length=200)
    replacement_product: str = Field(..., min_length=1, max_length=200)


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=30)
    notes: str | None = None


def build_customer_router(service: CustomerService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/customer", tags=["Customer"])

    @router.get("/profile")
    async def get_full_profile(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        data = await service.get_full_profile(current_user.id, db)
        if not data:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        return data

    @router.get("/orders")
    async def list_orders(
        limit: int = 10,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        orders = await service.get_orders(current_user.id, db, limit=limit)
        return {"orders": orders, "count": len(orders)}

    @router.get("/orders/{order_number}")
    async def get_order(
        order_number: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        order = await service.get_order_by_number(current_user.id, order_number, db)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    @router.get("/orders/latest")
    async def latest_order(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        order = await service.get_latest_order(current_user.id, db)
        if not order:
            raise HTTPException(status_code=404, detail="No orders found")
        return order

    @router.post("/orders/{order_number}/cancel")
    async def cancel_order(
        order_number: str, body: CancelRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        try:
            result = await service.cancel_order(current_user.id, order_number, body.reason, db)
            return {"status": "cancelled", "order": result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/orders/{order_number}/return")
    async def return_order(
        order_number: str, body: ReturnRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        try:
            result = await service.request_return(current_user.id, order_number, body.reason, body.items, db)
            return {"status": "return_requested", "return": result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/orders/{order_number}/exchange")
    async def exchange_order(
        order_number: str, body: ExchangeRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        try:
            result = await service.request_exchange(
                current_user.id, order_number, body.reason,
                body.original_product, body.replacement_product, db,
            )
            return {"status": "exchange_requested", "exchange": result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/orders/{order_number}/invoice")
    async def get_order_invoice(
        order_number: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        invoice = await service.get_invoice(current_user.id, order_number, db)
        if not invoice:
            raise HTTPException(status_code=404, detail="Order not found")
        return invoice

    @router.get("/orders/{order_number}/history")
    async def order_status_history(
        order_number: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        history = await service.get_order_status_log(current_user.id, order_number, db)
        if history is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return {"order_number": order_number, "history": history}

    @router.patch("/orders/{order_number}/status")
    async def update_status(
        order_number: str, body: StatusUpdateRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        try:
            result = await service.update_order_status(current_user.id, order_number, body.status, body.notes, db)
            return {"status": "updated", "order": result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/subscriptions")
    async def list_subscriptions(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        subs = await service.get_subscriptions(current_user.id, db)
        return {"subscriptions": subs, "count": len(subs)}

    @router.get("/payment-methods")
    async def list_payment_methods(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        methods = await service.get_payment_methods(current_user.id, db)
        return {"payment_methods": methods, "count": len(methods)}

    @router.get("/loyalty")
    async def get_loyalty(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        loyalty = await service.get_loyalty(current_user.id, db)
        if not loyalty:
            raise HTTPException(status_code=404, detail="Loyalty account not found")
        return loyalty

    @router.get("/addresses")
    async def list_addresses(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        addrs = await service.get_shipping_addresses(current_user.id, db)
        return {"addresses": addrs, "count": len(addrs)}

    @router.get("/support-tickets")
    async def list_tickets(
        limit: int = 10,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        tickets = await service.get_support_tickets(current_user.id, db, limit=limit)
        return {"support_tickets": tickets, "count": len(tickets)}

    @router.get("/shipments")
    async def list_shipments(
        limit: int = 10,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        shipments = await service.get_my_shipments(current_user.id, db, limit=limit)
        return {"shipments": shipments, "count": len(shipments)}

    @router.get("/shipments/track/{tracking_number}")
    async def track_shipment(
        tracking_number: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        result = await service.track_shipment(tracking_number, db)
        if not result:
            raise HTTPException(status_code=404, detail="Tracking number not found")
        return result

    @router.post("/shipments/track/{tracking_number}/refresh")
    async def refresh_shipment(
        tracking_number: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        result = await service.refresh_tracking(tracking_number, db)
        if not result:
            raise HTTPException(status_code=404, detail="Tracking number not found")
        return result

    @router.get("/orders/{order_number}/shipments")
    async def get_order_shipments(
        order_number: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        shipments = await service.get_order_shipments(current_user.id, order_number, db)
        return {"order_number": order_number, "shipments": shipments, "count": len(shipments)}

    return router
