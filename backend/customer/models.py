import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from backend.auth.database import Base


class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class LoyaltyTier(str, enum.Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    RETURN_REQUESTED = "return_requested"
    RETURN_APPROVED = "return_approved"
    RETURN_RECEIVED = "return_received"
    EXCHANGE_REQUESTED = "exchange_requested"
    EXCHANGE_APPROVED = "exchange_approved"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReturnStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    LABEL_SENT = "label_sent"
    ITEM_RECEIVED = "item_received"
    REFUND_PROCESSED = "refund_processed"
    CLOSED = "closed"


class ExchangeStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    ITEM_RECEIVED = "item_received"
    REPLACEMENT_SHIPPED = "replacement_shipped"
    COMPLETED = "completed"
    CLOSED = "closed"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PaymentMethodType(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    WIRE_TRANSFER = "wire_transfer"
    ACH = "ach"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _utcnow():
    return datetime.utcnow()


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    customer_id = Column(String(50), unique=True, nullable=False, index=True)
    account_status = Column(SAEnum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    loyalty_tier = Column(SAEnum(LoyaltyTier), default=LoyaltyTier.BRONZE, nullable=False)
    loyalty_points = Column(Integer, default=0, nullable=False)
    total_orders = Column(Integer, default=0, nullable=False)
    total_spent = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    marketing_opt_in = Column(Boolean, default=False, nullable=False)
    preferred_currency = Column(String(3), default="USD", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", backref="customer_profile", uselist=False)
    addresses = relationship("ShippingAddress", back_populates="customer", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="customer", cascade="all, delete-orphan")
    shipments = relationship("Shipment", back_populates="customer", cascade="all, delete-orphan")
    payment_methods = relationship("SavedPaymentMethod", back_populates="customer", cascade="all, delete-orphan")
    support_tickets = relationship("SupportTicket", back_populates="customer", cascade="all, delete-orphan")


class ShippingAddress(Base):
    __tablename__ = "shipping_addresses"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id = Column(Uuid(), ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(50), nullable=True)
    full_name = Column(String(200), nullable=False)
    company = Column(String(200), nullable=True)
    street_line1 = Column(String(255), nullable=False)
    street_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    customer = relationship("CustomerProfile", back_populates="addresses")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id = Column(Uuid(), ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    payment_status = Column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    shipping_cost = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    discount_amount = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    refunded_amount = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    shipping_address_id = Column(Uuid(), ForeignKey("shipping_addresses.id"), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    carrier = Column(String(100), nullable=True)
    estimated_delivery = Column(Date, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(String(500), nullable=True)
    return_window_end = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    customer = relationship("CustomerProfile", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    shipping_address = relationship("ShippingAddress")
    status_logs = relationship("OrderStatusLog", back_populates="order", cascade="all, delete-orphan",
                               order_by="OrderStatusLog.created_at")
    invoices = relationship("Invoice", back_populates="order", cascade="all, delete-orphan")
    returns = relationship("ReturnRequest", back_populates="order", cascade="all, delete-orphan")
    exchanges = relationship("ExchangeRequest", back_populates="order", cascade="all, delete-orphan")
    shipments = relationship("Shipment", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    order_id = Column(Uuid(), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    product_category = Column(String(100), nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    warranty_months = Column(Integer, nullable=True)
    warranty_expires = Column(Date, nullable=True)

    order = relationship("Order", back_populates="items")


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Uuid(), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=False)
    changed_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    order = relationship("Order", back_populates="status_logs")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    order_id = Column(Uuid(), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax = Column(Numeric(12, 2), nullable=False)
    shipping_cost = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    amount_paid = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    amount_due = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    issued_at = Column(DateTime, default=_utcnow, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    due_at = Column(DateTime, nullable=True)
    pdf_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    order = relationship("Order", back_populates="invoices")


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    order_id = Column(Uuid(), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    rma_number = Column(String(30), unique=True, nullable=False, index=True)
    status = Column(SAEnum(ReturnStatus), default=ReturnStatus.REQUESTED, nullable=False)
    reason = Column(String(500), nullable=False)
    items_json = Column(JSON, nullable=True)
    condition = Column(String(200), nullable=True)
    refund_amount = Column(Numeric(12, 2), nullable=True)
    return_label_url = Column(String(500), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    requested_at = Column(DateTime, default=_utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    item_received_at = Column(DateTime, nullable=True)
    refund_processed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    order = relationship("Order", back_populates="returns")


class ExchangeRequest(Base):
    __tablename__ = "exchange_requests"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    order_id = Column(Uuid(), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(SAEnum(ExchangeStatus), default=ExchangeStatus.REQUESTED, nullable=False)
    reason = Column(String(500), nullable=False)
    original_product = Column(String(200), nullable=False)
    replacement_product = Column(String(200), nullable=False)
    additional_payment = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    requested_at = Column(DateTime, default=_utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    replacement_shipped_at = Column(DateTime, nullable=True)
    tracking_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    order = relationship("Order", back_populates="exchanges")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id = Column(Uuid(), ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_name = Column(String(200), nullable=False)
    plan_tier = Column(String(50), nullable=True)
    status = Column(SAEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)
    billing_cycle = Column(String(20), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    started_at = Column(DateTime, nullable=False)
    next_billing_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    customer = relationship("CustomerProfile", back_populates="subscriptions")


class SavedPaymentMethod(Base):
    __tablename__ = "saved_payment_methods"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id = Column(Uuid(), ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    method_type = Column(SAEnum(PaymentMethodType), nullable=False)
    label = Column(String(100), nullable=True)
    last_four = Column(String(4), nullable=True)
    card_brand = Column(String(50), nullable=True)
    expiry_month = Column(Integer, nullable=True)
    expiry_year = Column(Integer, nullable=True)
    email = Column(String(255), nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    billing_address_id = Column(Uuid(), ForeignKey("shipping_addresses.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    customer = relationship("CustomerProfile", back_populates="payment_methods")
    billing_address = relationship("ShippingAddress")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id = Column(Uuid(), ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_number = Column(String(30), unique=True, nullable=False, index=True)
    subject = Column(String(300), nullable=False)
    status = Column(SAEnum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = Column(SAEnum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    category = Column(String(100), nullable=True)
    subcategory = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    assigned_to = Column(String(200), nullable=True)
    resolution = Column(Text, nullable=True)
    opened_at = Column(DateTime, default=_utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(100), nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    escalation_reason = Column(Text, nullable=True)
    related_order_number = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    customer = relationship("CustomerProfile", back_populates="support_tickets")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan",
                            order_by="TicketComment.created_at")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(Uuid(), ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    author = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    ticket = relationship("SupportTicket", back_populates="comments")


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(Uuid(), ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    content_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, default=_utcnow, nullable=False)

    ticket = relationship("SupportTicket", back_populates="attachments")


class ShipmentStatus(str, enum.Enum):
    PRE_TRANSIT = "pre_transit"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    RETURNED = "returned"
    AVAILABLE_FOR_PICKUP = "available_for_pickup"


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    order_id = Column(Uuid(), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id = Column(Uuid(), ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    tracking_number = Column(String(100), unique=True, nullable=False, index=True)
    courier = Column(String(100), nullable=False)
    courier_code = Column(String(20), nullable=True)
    status = Column(SAEnum(ShipmentStatus), default=ShipmentStatus.PRE_TRANSIT, nullable=False)
    estimated_delivery = Column(Date, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    origin_location = Column(String(255), nullable=True)
    current_location = Column(String(255), nullable=True)
    last_update = Column(DateTime, default=_utcnow, nullable=False)
    weight_lb = Column(Numeric(8, 2), nullable=True)
    package_count = Column(Integer, default=1, nullable=False)
    destination_address_id = Column(Uuid(), ForeignKey("shipping_addresses.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    order = relationship("Order", back_populates="shipments")
    customer = relationship("CustomerProfile")
    events = relationship("ShipmentEvent", back_populates="shipment", cascade="all, delete-orphan",
                          order_by="ShipmentEvent.timestamp")
    destination_address = relationship("ShippingAddress")


class ShipmentEvent(Base):
    __tablename__ = "shipment_events"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(Uuid(), ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), nullable=False)
    location = Column(String(255), nullable=True)
    description = Column(String(500), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    shipment = relationship("Shipment", back_populates="events")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), unique=True, nullable=False)
    tier = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    monthly_price = Column(Numeric(10, 2), nullable=False)
    annual_price = Column(Numeric(10, 2), nullable=False)
    features = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
