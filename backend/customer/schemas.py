from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ShippingAddressSchema(BaseModel):
    id: UUID
    label: Optional[str] = None
    full_name: str
    company: Optional[str] = None
    street_line1: str
    street_line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str
    phone: Optional[str] = None
    is_default: bool

    model_config = {"from_attributes": True}


class OrderItemSchema(BaseModel):
    id: UUID
    product_name: str
    product_category: Optional[str] = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    warranty_months: Optional[int] = None
    warranty_expires: Optional[date] = None

    model_config = {"from_attributes": True}


class OrderSchema(BaseModel):
    id: UUID
    order_number: str
    status: str
    subtotal: Decimal
    tax: Decimal
    shipping_cost: Decimal
    total: Decimal
    currency: str
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    estimated_delivery: Optional[date] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    items: list[OrderItemSchema] = []

    model_config = {"from_attributes": True}


class SubscriptionSchema(BaseModel):
    id: UUID
    plan_name: str
    plan_tier: Optional[str] = None
    status: str
    billing_cycle: str
    amount: Decimal
    currency: str
    started_at: datetime
    next_billing_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    auto_renew: bool

    model_config = {"from_attributes": True}


class SavedPaymentMethodSchema(BaseModel):
    id: UUID
    method_type: str
    label: Optional[str] = None
    last_four: Optional[str] = None
    card_brand: Optional[str] = None
    email: Optional[str] = None
    is_default: bool

    model_config = {"from_attributes": True}


class SupportTicketSchema(BaseModel):
    id: UUID
    ticket_number: str
    subject: str
    status: str
    priority: str
    category: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    opened_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LoyaltyAccountSchema(BaseModel):
    tier: str
    points: int
    total_orders: int
    total_spent: Decimal
    points_to_next_tier: Optional[int] = None
    next_tier: Optional[str] = None

    model_config = {"from_attributes": True}


class CustomerProfileSchema(BaseModel):
    id: UUID
    customer_id: str
    email: str
    username: str
    display_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    account_status: str
    loyalty: LoyaltyAccountSchema
    addresses: list[ShippingAddressSchema] = []
    payment_methods: list[SavedPaymentMethodSchema] = []

    model_config = {"from_attributes": True}


class FullCustomerProfileSchema(BaseModel):
    profile: CustomerProfileSchema
    orders: list[OrderSchema] = []
    subscriptions: list[SubscriptionSchema] = []
    support_tickets: list[SupportTicketSchema] = []

    model_config = {"from_attributes": True}


class SubscriptionPlanSchema(BaseModel):
    id: UUID
    name: str
    tier: str
    description: Optional[str] = None
    monthly_price: Decimal
    annual_price: Decimal
    features: Optional[dict] = None

    model_config = {"from_attributes": True}
