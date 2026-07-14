import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.customer.models import (
    CustomerProfile, ShippingAddress, Order, OrderItem,
    Subscription, SavedPaymentMethod, SupportTicket,
    LoyaltyTier, AccountStatus, OrderStatus, SubscriptionStatus,
    PaymentMethodType, TicketStatus, TicketPriority,
)
from backend.auth.models import User

logger = logging.getLogger("gigacorp.customer.seed")


async def seed_customer_data(db: AsyncSession):
    """Seed demo customer data for the first registered user if no customer profiles exist."""
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
        customer_id=profile.id,
        label="Home",
        full_name=user.display_name or user.username,
        street_line1="742 Evergreen Terrace",
        city="Springfield",
        state="IL",
        postal_code="62701",
        country="United States",
        phone=user.phone or "+1-555-123-4567",
        is_default=True,
    )
    addr2 = ShippingAddress(
        customer_id=profile.id,
        label="Office",
        full_name=user.display_name or user.username,
        company=user.company or "Acme Corp",
        street_line1="200 Innovation Drive",
        street_line2="Suite 300",
        city="San Francisco",
        state="CA",
        postal_code="94105",
        country="United States",
        phone="+1-555-987-6543",
        is_default=False,
    )
    addr_intl = ShippingAddress(
        customer_id=profile.id,
        label="International Office",
        full_name=user.display_name or user.username,
        company="GigaCorp India",
        street_line1="91 MG Road",
        city="Bangalore",
        state="Karnataka",
        postal_code="560001",
        country="India",
        phone="+91-80-4123-4567",
        is_default=False,
    )
    db.add_all([addr1, addr2, addr_intl])
    await db.flush()

    pm1 = SavedPaymentMethod(
        customer_id=profile.id,
        method_type=PaymentMethodType.CREDIT_CARD,
        label="Visa ending in 4242",
        last_four="4242",
        card_brand="Visa",
        expiry_month=12,
        expiry_year=2028,
        is_default=True,
        billing_address_id=addr1.id,
    )
    pm2 = SavedPaymentMethod(
        customer_id=profile.id,
        method_type=PaymentMethodType.PAYPAL,
        label="PayPal - john@example.com",
        email=user.email,
        is_default=False,
    )
    pm3 = SavedPaymentMethod(
        customer_id=profile.id,
        method_type=PaymentMethodType.ACH,
        label="Business Checking - Bank of America",
        is_default=False,
    )
    db.add_all([pm1, pm2, pm3])
    await db.flush()

    orders_data = [
        {
            "order_number": "ORD-2025-001",
            "status": OrderStatus.DELIVERED,
            "subtotal": Decimal("12000.00"),
            "tax": Decimal("1200.00"),
            "shipping_cost": Decimal("0.00"),
            "total": Decimal("13200.00"),
            "estimated_delivery": today - timedelta(days=35),
            "delivered_at": now - timedelta(days=30),
            "created_at": now - timedelta(days=45),
            "shipping_address_id": addr1.id,
            "tracking_number": "1Z999AA10123456784",
            "carrier": "UPS",
            "items": [
                {"product_name": "GigaBox Enterprise", "product_category": "Hardware", "quantity": 1, "unit_price": Decimal("12000.00"), "total_price": Decimal("12000.00"), "warranty_months": 36, "warranty_expires": today + timedelta(days=365*3 - 45)},
            ],
        },
        {
            "order_number": "ORD-2025-002",
            "status": OrderStatus.SHIPPED,
            "subtotal": Decimal("4500.00"),
            "tax": Decimal("450.00"),
            "shipping_cost": Decimal("24.99"),
            "total": Decimal("4974.99"),
            "estimated_delivery": today + timedelta(days=3),
            "created_at": now - timedelta(days=7),
            "shipping_address_id": addr2.id,
            "tracking_number": "9400111899223456789012",
            "carrier": "USPS",
            "items": [
                {"product_name": "GigaAnalytics - Annual License", "product_category": "Software", "quantity": 10, "unit_price": Decimal("450.00"), "total_price": Decimal("4500.00"), "warranty_months": 12, "warranty_expires": today + timedelta(days=365 - 7)},
            ],
        },
        {
            "order_number": "ORD-2025-003",
            "status": OrderStatus.CONFIRMED,
            "subtotal": Decimal("24999.00"),
            "tax": Decimal("2500.00"),
            "shipping_cost": Decimal("0.00"),
            "total": Decimal("27499.00"),
            "estimated_delivery": today + timedelta(days=10),
            "created_at": now - timedelta(days=2),
            "shipping_address_id": addr_intl.id,
            "tracking_number": "DHL-INTL-7845129630",
            "carrier": "DHL",
            "items": [
                {"product_name": "Server R420", "product_category": "Hardware", "quantity": 2, "unit_price": Decimal("8499.00"), "total_price": Decimal("16998.00"), "warranty_months": 36, "warranty_expires": today + timedelta(days=365*3 - 2)},
                {"product_name": "GigaSecure Enterprise License", "product_category": "Software", "quantity": 50, "unit_price": Decimal("150.00"), "total_price": Decimal("7500.00"), "warranty_months": 12, "warranty_expires": today + timedelta(days=365 - 2)},
            ],
        },
        {
            "order_number": "ORD-2025-004",
            "status": OrderStatus.PENDING,
            "subtotal": Decimal("59.99"),
            "tax": Decimal("6.00"),
            "shipping_cost": Decimal("12.99"),
            "total": Decimal("78.98"),
            "created_at": now - timedelta(hours=5),
            "shipping_address_id": addr1.id,
            "items": [
                {"product_name": "GigaCorp Wireless Mouse", "product_category": "Peripherals", "quantity": 1, "unit_price": Decimal("59.99"), "total_price": Decimal("59.99"), "warranty_months": 12, "warranty_expires": today + timedelta(days=365)},
            ],
        },
    ]

    for od in orders_data:
        items = od.pop("items")
        order = Order(customer_id=profile.id, **od)
        db.add(order)
        await db.flush()
        for it in items:
            item = OrderItem(order_id=order.id, **it)
            db.add(item)

    sub1 = Subscription(
        customer_id=profile.id,
        plan_name="GigaAnalytics Pro",
        plan_tier="pro",
        status=SubscriptionStatus.ACTIVE,
        billing_cycle="annual",
        amount=Decimal("299.00"),
        currency="USD",
        started_at=now - timedelta(days=180),
        next_billing_at=now + timedelta(days=185),
        auto_renew=True,
    )
    sub2 = Subscription(
        customer_id=profile.id,
        plan_name="GigaCloud Storage",
        plan_tier="business",
        status=SubscriptionStatus.ACTIVE,
        billing_cycle="monthly",
        amount=Decimal("49.99"),
        currency="USD",
        started_at=now - timedelta(days=90),
        next_billing_at=now + timedelta(days=25),
        auto_renew=True,
    )
    sub3 = Subscription(
        customer_id=profile.id,
        plan_name="GigaCorp Premium Support",
        plan_tier="premium",
        status=SubscriptionStatus.ACTIVE,
        billing_cycle="annual",
        amount=Decimal("999.00"),
        currency="USD",
        started_at=now - timedelta(days=30),
        next_billing_at=now + timedelta(days=335),
        auto_renew=True,
    )
    db.add_all([sub1, sub2, sub3])

    tickets_data = [
        {
            "ticket_number": "TKT-2025-001",
            "subject": "GigaBox Enterprise - Setup Assistance",
            "status": TicketStatus.RESOLVED,
            "priority": TicketPriority.HIGH,
            "category": "technical_support",
            "description": "Need help configuring the GigaBox Enterprise firewall settings for our network.",
            "assigned_to": "Alice Chen (Support Engineer)",
            "resolution": "Provided step-by-step firewall configuration guide. Customer confirmed setup complete.",
            "opened_at": now - timedelta(days=40),
            "resolved_at": now - timedelta(days=35),
        },
        {
            "ticket_number": "TKT-2025-002",
            "subject": "Billing Discrepancy - Annual License",
            "status": TicketStatus.RESOLVED,
            "priority": TicketPriority.MEDIUM,
            "category": "billing",
            "description": "Annual license invoice shows incorrect total. Charged $4,800 but agreement was for $4,500.",
            "assigned_to": "Bob Martinez (Billing)",
            "resolution": "Corrected invoice issued. Refund of $300 processed.",
            "opened_at": now - timedelta(days=20),
            "resolved_at": now - timedelta(days=15),
        },
        {
            "ticket_number": "TKT-2025-003",
            "subject": "Shipping Delay - Order ORD-2025-003 to India",
            "status": TicketStatus.IN_PROGRESS,
            "priority": TicketPriority.MEDIUM,
            "category": "shipping",
            "description": "International order to India has been delayed at customs. Need assistance with documentation.",
            "assigned_to": "Raj Patel (Logistics)",
            "opened_at": now - timedelta(days=1),
        },
        {
            "ticket_number": "TKT-2025-004",
            "subject": "Feature Request - API Rate Limit Increase",
            "status": TicketStatus.OPEN,
            "priority": TicketPriority.LOW,
            "category": "feature_request",
            "description": "Current API rate limit of 1000 req/hour is insufficient for our deployment. Requesting increase to 5000 req/hour.",
            "opened_at": now - timedelta(hours=6),
        },
    ]

    for td in tickets_data:
        ticket = SupportTicket(customer_id=profile.id, **td)
        db.add(ticket)

    await db.commit()
    logger.info(
        "Seeded customer data for %s: %d orders, %d subscriptions, %d tickets, %d addresses, %d payment methods",
        user.email,
        len(orders_data),
        3,
        len(tickets_data),
        3,
        3,
    )
