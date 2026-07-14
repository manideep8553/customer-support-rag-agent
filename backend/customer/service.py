import logging
from uuid import UUID
from typing import Optional
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.customer.models import (
    CustomerProfile, ShippingAddress, Order, OrderItem,
    Subscription, SavedPaymentMethod, SupportTicket,
    LoyaltyTier, AccountStatus, OrderStatus, SubscriptionStatus,
    TicketStatus,
)

logger = logging.getLogger("gigacorp.customer.service")

LOYALTY_THRESHOLDS = [
    (LoyaltyTier.PLATINUM, 10000),
    (LoyaltyTier.GOLD, 5000),
    (LoyaltyTier.SILVER, 1000),
    (LoyaltyTier.BRONZE, 0),
]


def _next_tier(points: int) -> tuple[Optional[str], Optional[int]]:
    for tier, threshold in reversed(LOYALTY_THRESHOLDS):
        if points < threshold:
            return tier.value, threshold - points
    return None, None


class CustomerService:
    def __init__(self, db_factory):
        self._db_factory = db_factory

    async def _session(self):
        async with self._db_factory() as s:
            yield s

    async def get_customer_by_user_id(self, user_id: UUID, db: AsyncSession) -> Optional[CustomerProfile]:
        result = await db.execute(
            select(CustomerProfile).where(CustomerProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_customer(self, user_id: UUID, email: str, display_name: str, db: AsyncSession) -> CustomerProfile:
        profile = await self.get_customer_by_user_id(user_id, db)
        if profile:
            return profile
        cust_id = f"CUST-{str(user_id)[:8].upper()}"
        profile = CustomerProfile(
            user_id=user_id,
            customer_id=cust_id,
            account_status=AccountStatus.ACTIVE,
            loyalty_tier=LoyaltyTier.BRONZE,
            loyalty_points=0,
        )
        db.add(profile)
        await db.flush()
        logger.info("Created customer profile %s for user %s", cust_id, user_id)
        return profile

    async def get_full_profile(self, user_id: UUID, db: AsyncSession) -> Optional[dict]:
        profile = await self.get_customer_by_user_id(user_id, db)
        if not profile:
            return None
        return await self._build_full_profile(profile, db)

    async def _build_full_profile(self, profile: CustomerProfile, db: AsyncSession) -> dict:
        result_addr = await db.execute(
            select(ShippingAddress).where(ShippingAddress.customer_id == profile.id)
        )
        addresses = result_addr.scalars().all()

        result_orders = await db.execute(
            select(Order).where(Order.customer_id == profile.id).order_by(desc(Order.created_at))
        )
        orders = result_orders.scalars().all()

        result_subs = await db.execute(
            select(Subscription).where(Subscription.customer_id == profile.id).order_by(desc(Subscription.created_at))
        )
        subscriptions = result_subs.scalars().all()

        result_pm = await db.execute(
            select(SavedPaymentMethod).where(SavedPaymentMethod.customer_id == profile.id)
        )
        payment_methods = result_pm.scalars().all()

        result_tickets = await db.execute(
            select(SupportTicket).where(SupportTicket.customer_id == profile.id).order_by(desc(SupportTicket.created_at))
        )
        support_tickets = result_tickets.scalars().all()

        orders_data = []
        for o in orders:
            result_items = await db.execute(
                select(OrderItem).where(OrderItem.order_id == o.id)
            )
            items = result_items.scalars().all()
            orders_data.append({
                "id": str(o.id),
                "order_number": o.order_number,
                "status": o.status.value,
                "subtotal": float(o.subtotal),
                "tax": float(o.tax),
                "shipping_cost": float(o.shipping_cost),
                "total": float(o.total),
                "currency": o.currency,
                "tracking_number": o.tracking_number,
                "carrier": o.carrier,
                "estimated_delivery": o.estimated_delivery.isoformat() if o.estimated_delivery else None,
                "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
                "created_at": o.created_at.isoformat(),
                "items": [
                    {
                        "product_name": i.product_name,
                        "product_category": i.product_category,
                        "quantity": i.quantity,
                        "unit_price": float(i.unit_price),
                        "total_price": float(i.total_price),
                        "warranty_months": i.warranty_months,
                        "warranty_expires": i.warranty_expires.isoformat() if i.warranty_expires else None,
                    }
                    for i in items
                ],
            })

        next_tier_name, points_needed = _next_tier(profile.loyalty_points)

        from backend.auth.models import User
        result_user = await db.execute(select(User).where(User.id == profile.user_id))
        user = result_user.scalar_one_or_none()

        return {
            "profile": {
                "id": str(profile.id),
                "customer_id": profile.customer_id,
                "email": user.email if user else "",
                "username": user.username if user else "",
                "display_name": user.display_name if user else "",
                "company": user.company if user else "",
                "phone": user.phone if user else "",
                "account_status": profile.account_status.value,
                "loyalty": {
                    "tier": profile.loyalty_tier.value,
                    "points": profile.loyalty_points,
                    "total_orders": profile.total_orders,
                    "total_spent": float(profile.total_spent),
                    "points_to_next_tier": points_needed,
                    "next_tier": next_tier_name,
                },
                "addresses": [
                    {
                        "id": str(a.id),
                        "label": a.label,
                        "full_name": a.full_name,
                        "company": a.company,
                        "street_line1": a.street_line1,
                        "street_line2": a.street_line2,
                        "city": a.city,
                        "state": a.state,
                        "postal_code": a.postal_code,
                        "country": a.country,
                        "phone": a.phone,
                        "is_default": a.is_default,
                    }
                    for a in addresses
                ],
                "payment_methods": [
                    {
                        "id": str(p.id),
                        "method_type": p.method_type.value,
                        "label": p.label,
                        "last_four": p.last_four,
                        "card_brand": p.card_brand,
                        "email": p.email,
                        "is_default": p.is_default,
                    }
                    for p in payment_methods
                ],
            },
            "orders": orders_data,
            "subscriptions": [
                {
                    "id": str(s.id),
                    "plan_name": s.plan_name,
                    "plan_tier": s.plan_tier,
                    "status": s.status.value,
                    "billing_cycle": s.billing_cycle,
                    "amount": float(s.amount),
                    "currency": s.currency,
                    "started_at": s.started_at.isoformat(),
                    "next_billing_at": s.next_billing_at.isoformat() if s.next_billing_at else None,
                    "cancelled_at": s.cancelled_at.isoformat() if s.cancelled_at else None,
                    "auto_renew": s.auto_renew,
                }
                for s in subscriptions
            ],
            "support_tickets": [
                {
                    "id": str(t.id),
                    "ticket_number": t.ticket_number,
                    "subject": t.subject,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "category": t.category,
                    "assigned_to": t.assigned_to,
                    "resolution": t.resolution,
                    "opened_at": t.opened_at.isoformat(),
                    "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
                }
                for t in support_tickets
            ],
        }

    async def get_orders(self, user_id: UUID, db: AsyncSession, limit: int = 10) -> list:
        profile = await self.get_customer_by_user_id(user_id, db)
        if not profile:
            return []
        result = await db.execute(
            select(Order).where(Order.customer_id == profile.id)
            .order_by(desc(Order.created_at)).limit(limit)
        )
        orders = result.scalars().all()
        result_list = []
        for o in orders:
            result_items = await db.execute(select(OrderItem).where(OrderItem.order_id == o.id))
            items = result_items.scalars().all()
            result_list.append({
                "id": str(o.id),
                "order_number": o.order_number,
                "status": o.status.value,
                "total": float(o.total),
                "currency": o.currency,
                "tracking_number": o.tracking_number,
                "carrier": o.carrier,
                "estimated_delivery": o.estimated_delivery.isoformat() if o.estimated_delivery else None,
                "created_at": o.created_at.isoformat(),
                "items": [
                    {
                        "product_name": i.product_name,
                        "quantity": i.quantity,
                        "unit_price": float(i.unit_price),
                        "total_price": float(i.total_price),
                    }
                    for i in items
                ],
            })
        return result_list

    async def get_order_by_number(self, user_id: UUID, order_number: str, db: AsyncSession) -> Optional[dict]:
        profile = await self.get_customer_by_user_id(user_id, db)
        if not profile:
            return None
        result = await db.execute(
            select(Order).where(Order.customer_id == profile.id, Order.order_number == order_number)
        )
        o = result.scalar_one_or_none()
        if not o:
            return None
        result_items = await db.execute(select(OrderItem).where(OrderItem.order_id == o.id))
        items = result_items.scalars().all()
        return {
            "id": str(o.id),
            "order_number": o.order_number,
            "status": o.status.value,
            "subtotal": float(o.subtotal),
            "tax": float(o.tax),
            "shipping_cost": float(o.shipping_cost),
            "total": float(o.total),
            "currency": o.currency,
            "tracking_number": o.tracking_number,
            "carrier": o.carrier,
            "estimated_delivery": o.estimated_delivery.isoformat() if o.estimated_delivery else None,
            "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
            "created_at": o.created_at.isoformat(),
            "items": [
                {
                    "product_name": i.product_name,
                    "product_category": i.product_category,
                    "quantity": i.quantity,
                    "unit_price": float(i.unit_price),
                    "total_price": float(i.total_price),
                    "warranty_months": i.warranty_months,
                    "warranty_expires": i.warranty_expires.isoformat() if i.warranty_expires else None,
                }
                for i in items
            ],
        }

    async def get_latest_order(self, user_id: UUID, db: AsyncSession) -> Optional[dict]:
        profile = await self.get_customer_by_user_id(user_id, db)
        if not profile:
            return None
        result = await db.execute(
            select(Order).where(Order.customer_id == profile.id)
            .order_by(desc(Order.created_at)).limit(1)
        )
        o = result.scalar_one_or_none()
        if not o:
            return None
        result_items = await db.execute(select(OrderItem).where(OrderItem.order_id == o.id))
        items = result_items.scalars().all()
        return {
            "id": str(o.id),
            "order_number": o.order_number,
            "status": o.status.value,
            "total": float(o.total),
            "currency": o.currency,
            "tracking_number": o.tracking_number,
            "carrier": o.carrier,
            "estimated_delivery": o.estimated_delivery.isoformat() if o.estimated_delivery else None,
            "created_at": o.created_at.isoformat(),
            "items": [
                {
                    "product_name": i.product_name,
                    "quantity": i.quantity,
                    "unit_price": float(i.unit_price),
                    "total_price": float(i.total_price),
                }
                for i in items
            ],
        }

    async def get_subscriptions(self, user_id: UUID, db: AsyncSession) -> list:
        profile = await self.get_customer_by_user_id(user_id, db)
        if not profile:
            return []
        result = await db.execute(
            select(Subscription).where(Subscription.customer_id == profile.id)
            .order_by(desc(Subscription.created_at))
        )
        subs = result.scalars().all()
        return [
            {
                "id": str(s.id),
                "plan_name": s.plan_name,
                "plan_tier": s.plan_tier,
                "status": s.status.value,
                "billing_cycle": s.billing_cycle,
                "amount": float(s.amount),
                "currency": s.currency,
                "started_at": s.started_at.isoformat(),
                "next_billing_at": s.next_billing_at.isoformat() if s.next_billing_at else None,
                "auto_renew": s.auto_renew,
            }
            for s in subs
        ]

    async def get_payment_methods(self, user_id: UUID, db: AsyncSession) -> list:
        profile = await self.get_customer_by_user_id(user_id, db)
        if not profile:
            return []
        result = await db.execute(
            select(SavedPaymentMethod).where(SavedPaymentMethod.customer_id == profile.id)
        )
        pms = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "method_type": p.method_type.value,
                "label": p.label,
                "last_four": p.last_four,
                "card_brand": p.card_brand,
                "email": p.email,
                "is_default": p.is_default,
            }
            for p in pms
        ]

    async def get_support_tickets(self, user_id: UUID, db: AsyncSession, limit: int = 10) -> list:
        profile = await self.get_customer_by_user_id(user_id, db)
        if not profile:
            return []
        result = await db.execute(
            select(SupportTicket).where(SupportTicket.customer_id == profile.id)
            .order_by(desc(SupportTicket.created_at)).limit(limit)
        )
        tickets = result.scalars().all()
        return [
            {
                "id": str(t.id),
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "status": t.status.value,
                "priority": t.priority.value,
                "category": t.category,
                "assigned_to": t.assigned_to,
                "resolution": t.resolution,
                "opened_at": t.opened_at.isoformat(),
                "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
            }
            for t in tickets
        ]

    async def get_loyalty(self, user_id: UUID, db: AsyncSession) -> Optional[dict]:
        profile = await self.get_customer_by_user_id(user_id, db)
        if not profile:
            return None
        next_tier_name, points_needed = _next_tier(profile.loyalty_points)
        tier_benefits = {
            "bronze": "Basic support, standard response times",
            "silver": "Priority support, 10% discount on annual plans",
            "gold": "Priority support, 15% discount, dedicated account manager",
            "platinum": "24/7 premium support, 20% discount, dedicated manager, early access",
        }
        return {
            "tier": profile.loyalty_tier.value,
            "points": profile.loyalty_points,
            "total_orders": profile.total_orders,
            "total_spent": float(profile.total_spent),
            "benefits": tier_benefits.get(profile.loyalty_tier.value, ""),
            "points_to_next_tier": points_needed,
            "next_tier": next_tier_name,
        }

    async def get_chat_context(self, user_id: UUID, db: AsyncSession) -> Optional[dict]:
        """Load lightweight customer data for chatbot context."""
        profile = await self.get_customer_by_user_id(user_id, db)
        if not profile:
            return None

        result = await db.execute(
            select(Order).where(Order.customer_id == profile.id)
            .order_by(desc(Order.created_at)).limit(3)
        )
        recent_orders = result.scalars().all()
        orders_data = []
        for o in recent_orders:
            result_items = await db.execute(select(OrderItem).where(OrderItem.order_id == o.id))
            items = result_items.scalars().all()
            orders_data.append({
                "order_number": o.order_number,
                "status": o.status.value,
                "total": float(o.total),
                "currency": o.currency,
                "tracking_number": o.tracking_number,
                "carrier": o.carrier,
                "estimated_delivery": o.estimated_delivery.isoformat() if o.estimated_delivery else None,
                "created_at": o.created_at.isoformat(),
                "item_count": len(items),
                "items": [
                    {
                        "product_name": i.product_name,
                        "product_category": i.product_category,
                        "quantity": i.quantity,
                        "unit_price": float(i.unit_price),
                        "warranty_months": i.warranty_months,
                        "warranty_expires": i.warranty_expires.isoformat() if i.warranty_expires else None,
                    }
                    for i in items
                ],
            })

        result_subs = await db.execute(
            select(Subscription).where(
                Subscription.customer_id == profile.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        subs = result_subs.scalars().all()

        result_addr = await db.execute(
            select(ShippingAddress).where(
                ShippingAddress.customer_id == profile.id,
                ShippingAddress.is_default == True,
            ).limit(1)
        )
        default_addr = result_addr.scalar_one_or_none()

        result_pm = await db.execute(
            select(SavedPaymentMethod).where(SavedPaymentMethod.customer_id == profile.id)
        )
        pms = result_pm.scalars().all()

        result_tickets = await db.execute(
            select(SupportTicket).where(
                SupportTicket.customer_id == profile.id,
                SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_CUSTOMER]),
            )
        )
        open_tickets = result_tickets.scalars().all()

        next_tier_name, points_needed = _next_tier(profile.loyalty_points)

        from backend.auth.models import User
        result_user = await db.execute(select(User).where(User.id == profile.user_id))
        user = result_user.scalar_one_or_none()

        return {
            "customer_id": profile.customer_id,
            "display_name": user.display_name if user else "",
            "email": user.email if user else "",
            "phone": user.phone if user else "",
            "company": user.company if user else "",
            "account_status": profile.account_status.value,
            "loyalty": {
                "tier": profile.loyalty_tier.value,
                "points": profile.loyalty_points,
                "total_orders": profile.total_orders,
                "total_spent": float(profile.total_spent),
                "next_tier": next_tier_name,
                "points_to_next_tier": points_needed,
            },
            "subscriptions": [
                {
                    "plan_name": s.plan_name,
                    "plan_tier": s.plan_tier,
                    "status": s.status.value,
                    "billing_cycle": s.billing_cycle,
                    "amount": float(s.amount),
                    "currency": s.currency,
                    "next_billing_at": s.next_billing_at.isoformat() if s.next_billing_at else None,
                    "auto_renew": s.auto_renew,
                }
                for s in subs
            ],
            "payment_methods": [
                {
                    "method_type": p.method_type.value,
                    "label": p.label,
                    "last_four": p.last_four,
                    "card_brand": p.card_brand,
                    "is_default": p.is_default,
                }
                for p in pms
            ],
            "default_address": {
                "street_line1": default_addr.street_line1,
                "street_line2": default_addr.street_line2,
                "city": default_addr.city,
                "state": default_addr.state,
                "postal_code": default_addr.postal_code,
                "country": default_addr.country,
            } if default_addr else None,
            "recent_orders": orders_data,
            "open_tickets": [
                {
                    "ticket_number": t.ticket_number,
                    "subject": t.subject,
                    "priority": t.priority.value,
                    "category": t.category,
                    "opened_at": t.opened_at.isoformat(),
                }
                for t in open_tickets
            ],
        }

    async def get_shipping_addresses(self, user_id: UUID, db: AsyncSession) -> list:
        profile = await self.get_customer_by_user_id(user_id, db)
        if not profile:
            return []
        result = await db.execute(
            select(ShippingAddress).where(ShippingAddress.customer_id == profile.id)
        )
        addrs = result.scalars().all()
        return [
            {
                "id": str(a.id),
                "label": a.label,
                "full_name": a.full_name,
                "street_line1": a.street_line1,
                "street_line2": a.street_line2,
                "city": a.city,
                "state": a.state,
                "postal_code": a.postal_code,
                "country": a.country,
                "phone": a.phone,
                "is_default": a.is_default,
            }
            for a in addrs
        ]
