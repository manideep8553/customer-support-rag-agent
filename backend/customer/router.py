import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.database import get_db
from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.customer.service import CustomerService

logger = logging.getLogger("gigacorp.customer.router")


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

    return router
