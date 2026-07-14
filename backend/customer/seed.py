import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.customer.models import (
    CustomerProfile, ShippingAddress, Order, OrderItem, OrderStatusLog,
    Invoice, ReturnRequest, Subscription, SavedPaymentMethod, SupportTicket,
    LoyaltyTier, AccountStatus, OrderStatus, PaymentStatus, ReturnStatus,
    SubscriptionStatus, PaymentMethodType, TicketStatus, TicketPriority,
    Shipment, ShipmentStatus, ShipmentEvent,
)
from backend.auth.models import User

logger = logging.getLogger("gigacorp.customer.seed")


async def seed_customer_data(db: AsyncSession):
    result = await db.execute(select(CustomerProfile).limit(1))
    if result.scalar_one_or_none():
        logger.info("Customer profiles already exist — skipping seed")
        return

    result = await db.execute(select(User).order_by(User.created_at).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        logger.info("No users found — skipping customer seed")
        return

    now = datetime.utcnow()
    today = date.today()

    profile = CustomerProfile(
        user_id=user.id,
        customer_id=f"CUST-{str(user.id)[:8].upper()}",
        account_status=AccountStatus.ACTIVE,
        loyalty_tier=LoyaltyTier.GOLD,
        loyalty_points=6200,
        total_orders=8,
        total_spent=Decimal("45750.00"),
        marketing_opt_in=True,
    )
    db.add(profile)
    await db.flush()
    logger.info("Seeded customer profile %s for user %s", profile.customer_id, user.email)

    addr1 = ShippingAddress(
        customer_id=profile.id, label="Home",
        full_name=user.display_name or user.username,
        street_line1="742 Evergreen Terrace", city="Springfield",
        state="IL", postal_code="62701", country="United States",
        phone=user.phone or "+1-555-123-4567", is_default=True,
    )
    addr2 = ShippingAddress(
        customer_id=profile.id, label="Office",
        full_name=user.display_name or user.username,
        company=user.company or "Acme Corp",
        street_line1="200 Innovation Drive", street_line2="Suite 300",
        city="San Francisco", state="CA", postal_code="94105",
        country="United States", phone="+1-555-987-6543", is_default=False,
    )
    addr_intl = ShippingAddress(
        customer_id=profile.id, label="International Office",
        full_name=user.display_name or user.username, company="GigaCorp India",
        street_line1="91 MG Road", city="Bangalore", state="Karnataka",
        postal_code="560001", country="India",
        phone="+91-80-4123-4567", is_default=False,
    )
    db.add_all([addr1, addr2, addr_intl])
    await db.flush()

    pm1 = SavedPaymentMethod(
        customer_id=profile.id, method_type=PaymentMethodType.CREDIT_CARD,
        label="Visa ending in 4242", last_four="4242", card_brand="Visa",
        expiry_month=12, expiry_year=2028, is_default=True, billing_address_id=addr1.id,
    )
    pm2 = SavedPaymentMethod(
        customer_id=profile.id, method_type=PaymentMethodType.PAYPAL,
        label="PayPal - john@example.com", email=user.email, is_default=False,
    )
    pm3 = SavedPaymentMethod(
        customer_id=profile.id, method_type=PaymentMethodType.ACH,
        label="Business Checking - Bank of America", is_default=False,
    )
    db.add_all([pm1, pm2, pm3])
    await db.flush()

    orders_data = [
        {
            "order_number": "ORD-2025-001", "status": OrderStatus.DELIVERED,
            "payment_status": PaymentStatus.PAID,
            "subtotal": Decimal("12000.00"), "tax": Decimal("1200.00"),
            "shipping_cost": Decimal("0.00"), "total": Decimal("13200.00"),
            "estimated_delivery": today - timedelta(days=35),
            "delivered_at": now - timedelta(days=30), "created_at": now - timedelta(days=45),
            "shipping_address_id": addr1.id,
            "tracking_number": "1Z999AA10123456784", "carrier": "UPS",
            "return_window_end": today + timedelta(days=5),
            "items": [
                {"product_name": "GigaBox Enterprise", "product_category": "Hardware",
                 "quantity": 1, "unit_price": Decimal("12000.00"), "total_price": Decimal("12000.00"),
                 "warranty_months": 36, "warranty_expires": today + timedelta(days=365*3 - 45)},
            ],
            "logs": [
                ("pending", "confirmed", "system"),
                ("confirmed", "processing", "system"),
                ("processing", "shipped", "warehouse"),
                ("shipped", "delivered", "system"),
            ],
        },
        {
            "order_number": "ORD-2025-002", "status": OrderStatus.SHIPPED,
            "payment_status": PaymentStatus.PAID,
            "subtotal": Decimal("4500.00"), "tax": Decimal("450.00"),
            "shipping_cost": Decimal("24.99"), "discount_amount": Decimal("450.00"),
            "total": Decimal("4524.99"),
            "estimated_delivery": today + timedelta(days=3),
            "created_at": now - timedelta(days=7),
            "shipping_address_id": addr2.id,
            "tracking_number": "9400111899223456789012", "carrier": "USPS",
            "return_window_end": today + timedelta(days=38),
            "items": [
                {"product_name": "GigaAnalytics - Annual License", "product_category": "Software",
                 "quantity": 10, "unit_price": Decimal("450.00"), "total_price": Decimal("4500.00"),
                 "warranty_months": 12, "warranty_expires": today + timedelta(days=365 - 7)},
            ],
            "logs": [
                ("pending", "confirmed", "system"),
                ("confirmed", "processing", "system"),
                ("processing", "shipped", "warehouse"),
            ],
        },
        {
            "order_number": "ORD-2025-003", "status": OrderStatus.CONFIRMED,
            "payment_status": PaymentStatus.PAID,
            "subtotal": Decimal("24999.00"), "tax": Decimal("2500.00"),
            "shipping_cost": Decimal("0.00"), "total": Decimal("27499.00"),
            "estimated_delivery": today + timedelta(days=10),
            "created_at": now - timedelta(days=2),
            "shipping_address_id": addr_intl.id,
            "tracking_number": "DHL-INTL-7845129630", "carrier": "DHL",
            "return_window_end": today + timedelta(days=43),
            "items": [
                {"product_name": "Server R420", "product_category": "Hardware",
                 "quantity": 2, "unit_price": Decimal("8499.00"), "total_price": Decimal("16998.00"),
                 "warranty_months": 36, "warranty_expires": today + timedelta(days=365*3 - 2)},
                {"product_name": "GigaSecure Enterprise License", "product_category": "Software",
                 "quantity": 50, "unit_price": Decimal("150.00"), "total_price": Decimal("7500.00"),
                 "warranty_months": 12, "warranty_expires": today + timedelta(days=365 - 2)},
            ],
            "logs": [
                ("pending", "confirmed", "system"),
            ],
        },
        {
            "order_number": "ORD-2025-004", "status": OrderStatus.PENDING,
            "payment_status": PaymentStatus.PENDING,
            "subtotal": Decimal("59.99"), "tax": Decimal("6.00"),
            "shipping_cost": Decimal("12.99"), "total": Decimal("78.98"),
            "created_at": now - timedelta(hours=5),
            "shipping_address_id": addr1.id,
            "return_window_end": today + timedelta(days=60),
            "items": [
                {"product_name": "GigaCorp Wireless Mouse", "product_category": "Peripherals",
                 "quantity": 1, "unit_price": Decimal("59.99"), "total_price": Decimal("59.99"),
                 "warranty_months": 12, "warranty_expires": today + timedelta(days=365)},
            ],
            "logs": [],
        },
        {
            "order_number": "ORD-2024-099", "status": OrderStatus.REFUNDED,
            "payment_status": PaymentStatus.REFUNDED,
            "subtotal": Decimal("299.00"), "tax": Decimal("29.90"),
            "shipping_cost": Decimal("0.00"), "refunded_amount": Decimal("328.90"),
            "total": Decimal("328.90"),
            "created_at": now - timedelta(days=120), "delivered_at": now - timedelta(days=105),
            "cancelled_at": now - timedelta(days=90),
            "cancellation_reason": "Customer requested refund — software did not meet requirements",
            "shipping_address_id": addr1.id,
            "items": [
                {"product_name": "GigaAnalytics Pro - Annual", "product_category": "Software",
                 "quantity": 1, "unit_price": Decimal("299.00"), "total_price": Decimal("299.00"),
                 "warranty_months": None, "warranty_expires": None},
            ],
            "logs": [
                ("pending", "confirmed", "system"),
                ("confirmed", "shipped", "warehouse"),
                ("shipped", "delivered", "system"),
                ("delivered", "return_requested", "customer"),
                ("return_requested", "return_approved", "support"),
                ("return_approved", "return_received", "warehouse"),
                ("return_received", "refunded", "system"),
            ],
        },
    ]

    for od in orders_data:
        logs = od.pop("logs")
        items = od.pop("items")
        order = Order(customer_id=profile.id, **od)
        db.add(order)
        await db.flush()
        for it in items:
            item = OrderItem(order_id=order.id, **it)
            db.add(item)
        for i, (from_s, to_s, by) in enumerate(logs):
            log = OrderStatusLog(
                order_id=order.id, from_status=from_s, to_status=to_s,
                changed_by=by,
                created_at=order.created_at + timedelta(seconds=(i + 1) * 60),
            )
            db.add(log)

        if od.get("status") in (OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED):
            paid = od.get("total", 0)
            inv = Invoice(
                order_id=order.id,
                invoice_number=f"INV-{od['order_number']}",
                subtotal=od.get("subtotal", 0),
                tax=od.get("tax", 0),
                shipping_cost=od.get("shipping_cost", 0),
                discount_amount=od.get("discount_amount", Decimal("0.00")),
                total=od.get("total", 0),
                amount_paid=paid,
                amount_due=Decimal("0.00"),
                issued_at=order.created_at,
                paid_at=order.delivered_at or (order.created_at + timedelta(hours=2)),
                due_at=order.created_at + timedelta(days=30),
                pdf_url=f"https://portal.gigacorp.com/invoices/{od['order_number']}.pdf",
            )
            db.add(inv)

    return_req = ReturnRequest(
        order_id=(await db.execute(
            select(Order).where(Order.order_number == "ORD-2024-099")
        )).scalar_one().id,
        rma_number="RMA-ORD-2024-099-001",
        status=ReturnStatus.REFUND_PROCESSED,
        reason="Software did not meet requirements for our use case. Requesting full refund as per 30-day policy.",
        refund_amount=Decimal("328.90"),
        return_label_url="https://portal.gigacorp.com/labels/RMA-ORD-2024-099-001.pdf",
        tracking_number="1Z999RMA10123456784",
        requested_at=now - timedelta(days=95),
        approved_at=now - timedelta(days=93),
        item_received_at=now - timedelta(days=91),
        refund_processed_at=now - timedelta(days=90),
    )
    db.add(return_req)

    sub1 = Subscription(
        customer_id=profile.id, plan_name="GigaAnalytics Pro", plan_tier="pro",
        status=SubscriptionStatus.ACTIVE, billing_cycle="annual",
        amount=Decimal("299.00"), currency="USD",
        started_at=now - timedelta(days=180), next_billing_at=now + timedelta(days=185), auto_renew=True,
    )
    sub2 = Subscription(
        customer_id=profile.id, plan_name="GigaCloud Storage", plan_tier="business",
        status=SubscriptionStatus.ACTIVE, billing_cycle="monthly",
        amount=Decimal("49.99"), currency="USD",
        started_at=now - timedelta(days=90), next_billing_at=now + timedelta(days=25), auto_renew=True,
    )
    sub3 = Subscription(
        customer_id=profile.id, plan_name="GigaCorp Premium Support", plan_tier="premium",
        status=SubscriptionStatus.ACTIVE, billing_cycle="annual",
        amount=Decimal("999.00"), currency="USD",
        started_at=now - timedelta(days=30), next_billing_at=now + timedelta(days=335), auto_renew=True,
    )
    db.add_all([sub1, sub2, sub3])

    tickets_data = [
        {
            "ticket_number": "TKT-2025-001",
            "subject": "GigaBox Enterprise - Setup Assistance",
            "status": TicketStatus.RESOLVED, "priority": TicketPriority.HIGH,
            "category": "technical_support",
            "description": "Need help configuring the GigaBox Enterprise firewall settings for our network.",
            "assigned_to": "Alice Chen (Support Engineer)",
            "resolution": "Provided step-by-step firewall configuration guide. Customer confirmed setup complete.",
            "opened_at": now - timedelta(days=40), "resolved_at": now - timedelta(days=35),
        },
        {
            "ticket_number": "TKT-2025-002",
            "subject": "Billing Discrepancy - Annual License",
            "status": TicketStatus.RESOLVED, "priority": TicketPriority.MEDIUM,
            "category": "billing",
            "description": "Annual license invoice shows incorrect total. Charged $4,800 but agreement was for $4,500.",
            "assigned_to": "Bob Martinez (Billing)",
            "resolution": "Corrected invoice issued. Refund of $300 processed.",
            "opened_at": now - timedelta(days=20), "resolved_at": now - timedelta(days=15),
        },
        {
            "ticket_number": "TKT-2025-003",
            "subject": "Shipping Delay - Order ORD-2025-003 to India",
            "status": TicketStatus.IN_PROGRESS, "priority": TicketPriority.MEDIUM,
            "category": "shipping",
            "description": "International order to India has been delayed at customs. Need assistance with documentation.",
            "assigned_to": "Raj Patel (Logistics)",
            "opened_at": now - timedelta(days=1),
        },
        {
            "ticket_number": "TKT-2025-004",
            "subject": "Feature Request - API Rate Limit Increase",
            "status": TicketStatus.OPEN, "priority": TicketPriority.LOW,
            "category": "feature_request",
            "description": "Current API rate limit of 1000 req/hour is insufficient for our deployment. Requesting increase to 5000 req/hour.",
            "opened_at": now - timedelta(hours=6),
        },
    ]
    for td in tickets_data:
        ticket = SupportTicket(customer_id=profile.id, **td)
        db.add(ticket)

    # ── Shipments ──────────────────────────────────────────────────────
    now_ish = datetime.utcnow()
    shipments_data = [
        {
            "order_number": "ORD-2025-001",
            "tracking_number": "1Z999AA10123456784",
            "courier": "UPS", "courier_code": "ups",
            "status": ShipmentStatus.DELIVERED,
            "origin": "Warehouse A, Dallas, TX",
            "shipped_at": now - timedelta(days=42),
            "delivered_at": now - timedelta(days=30),
            "estimated": today - timedelta(days=35),
            "events": [
                (ShipmentStatus.PRE_TRANSIT, "Warehouse A, Dallas, TX",
                 "Shipping label created. UPS awaiting item.", now - timedelta(days=42)),
                (ShipmentStatus.IN_TRANSIT, "Warehouse A, Dallas, TX",
                 "Origin scan: package received at UPS facility.", now - timedelta(days=41)),
                (ShipmentStatus.IN_TRANSIT, "UPS Hub, Memphis, TN",
                 "Departed from origin facility. In transit.", now - timedelta(days=40)),
                (ShipmentStatus.IN_TRANSIT, "Regional Hub, Chicago, IL",
                 "Arrived at regional sorting facility.", now - timedelta(days=38)),
                (ShipmentStatus.IN_TRANSIT, "Regional Hub, Chicago, IL",
                 "Departed regional facility.", now - timedelta(days=37)),
                (ShipmentStatus.IN_TRANSIT, "Destination Sort Facility, Springfield, IL",
                 "Arrived at destination sort facility.", now - timedelta(days=36)),
                (ShipmentStatus.OUT_FOR_DELIVERY, "Local delivery route",
                 "Out for delivery with UPS driver.", now - timedelta(days=30)),
                (ShipmentStatus.DELIVERED, "Springfield, IL",
                 "Delivered. Signed for by recipient.", now - timedelta(days=30)),
            ],
        },
        {
            "order_number": "ORD-2025-002",
            "tracking_number": "9400111899223456789012",
            "courier": "USPS", "courier_code": "usps",
            "status": ShipmentStatus.IN_TRANSIT,
            "origin": "Warehouse B, Memphis, TN",
            "shipped_at": now - timedelta(days=7),
            "estimated": today + timedelta(days=3),
            "events": [
                (ShipmentStatus.PRE_TRANSIT, "Warehouse B, Memphis, TN",
                 "USPS in possession of item.", now - timedelta(days=7)),
                (ShipmentStatus.IN_TRANSIT, "Memphis, TN",
                 "Accepted at USPS origin facility.", now - timedelta(days=6)),
                (ShipmentStatus.IN_TRANSIT, "USPS Regional Facility, Memphis, TN",
                 "Departed USPS regional facility.", now - timedelta(days=5)),
                (ShipmentStatus.IN_TRANSIT, "In transit",
                 "In transit to next facility.", now - timedelta(days=3)),
            ],
        },
        {
            "order_number": "ORD-2025-003",
            "tracking_number": "DHL-INTL-7845129630",
            "courier": "DHL Express", "courier_code": "dhl",
            "status": ShipmentStatus.PRE_TRANSIT,
            "origin": "International Gateway, New York, NY",
            "shipped_at": now - timedelta(days=2),
            "estimated": today + timedelta(days=10),
            "events": [
                (ShipmentStatus.PRE_TRANSIT, "International Gateway, New York, NY",
                 "Shipment information received by DHL.", now - timedelta(days=2)),
            ],
        },
    ]

    for sd in shipments_data:
        order_result = await db.execute(
            select(Order).where(Order.order_number == sd["order_number"])
        )
        order = order_result.scalar_one_or_none()
        if not order:
            continue

        shipment = Shipment(
            order_id=order.id,
            customer_id=profile.id,
            tracking_number=sd["tracking_number"],
            courier=sd["courier"],
            courier_code=sd["courier_code"],
            status=sd["status"],
            estimated_delivery=sd["estimated"],
            shipped_at=sd["shipped_at"],
            delivered_at=sd.get("delivered_at"),
            origin_location=sd["origin"],
            current_location=sd["events"][-1][1] if sd["events"] else sd["origin"],
            last_update=sd["events"][-1][3] if sd["events"] else sd["shipped_at"],
            destination_address_id=order.shipping_address_id,
        )
        db.add(shipment)
        await db.flush()

        for ev_status, ev_loc, ev_desc, ev_ts in sd["events"]:
            event = ShipmentEvent(
                shipment_id=shipment.id,
                status=ev_status.value,
                location=ev_loc,
                description=ev_desc,
                timestamp=ev_ts,
            )
            db.add(event)

    await db.commit()
    logger.info(
        "Seeded customer data for %s: %d orders, %d subscriptions, %d tickets, %d addresses, %d payment methods",
        user.email, len(orders_data), 3, len(tickets_data), 3, 3,
    )
