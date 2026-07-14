from typing import Optional

from pydantic import BaseModel, Field


class AdminDashboardStats(BaseModel):
    total_users: int = 0
    total_customers: int = 0
    total_orders: int = 0
    total_tickets: int = 0
    pending_tickets: int = 0
    open_tickets: int = 0
    total_shipments: int = 0
    pending_refunds: int = 0
    kb_chunks: int = 0
    kb_initialized: bool = False
    active_sessions: int = 0
    total_conversations: int = 0


class AdminOrderUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=30)
    notes: Optional[str] = None


class AdminTicketUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    note: Optional[str] = None


class AdminTicketComment(BaseModel):
    body: str = Field(..., min_length=1)
    is_internal: bool = True


class AdminRefundAction(BaseModel):
    notes: Optional[str] = None


class AdminRoleUpdate(BaseModel):
    role: str = Field(..., pattern=r"^(user|admin|premium|support)$")


class AdminShipmentCreate(BaseModel):
    order_number: str
    courier: str
    courier_code: str
    tracking_number: str
    status: str = "pre_transit"
    estimated_delivery: Optional[str] = None
    weight_lb: Optional[float] = None
    package_count: int = 1


class AdminShipmentUpdate(BaseModel):
    status: Optional[str] = None
    current_location: Optional[str] = None
    estimated_delivery: Optional[str] = None
    last_update: Optional[str] = None


class AdminKBUploadResponse(BaseModel):
    status: str
    filename: str
    chunks_ingested: int
    message: str
