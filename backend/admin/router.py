import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.admin.schemas import (
    AdminDashboardStats,
    AdminOrderUpdate,
    AdminRefundAction,
    AdminRoleUpdate,
    AdminShipmentCreate,
    AdminShipmentUpdate,
    AdminTicketComment,
    AdminTicketUpdate,
)
from backend.auth.database import get_db
from backend.auth.dependencies import require_role
from backend.auth.models import User, UserRole
from backend.config import settings
from backend.customer.models import (
    CustomerProfile,
    Order,
    OrderStatus,
    OrderStatusLog,
    ReturnRequest,
    ReturnStatus,
    Shipment,
    ShipmentEvent,
    ShipmentStatus,
    SupportTicket,
    TicketComment,
    TicketStatus,
)
from backend.customer.service import CustomerService
from backend.knowledge_base.store import KnowledgeBaseManager
from backend.orchestration.graph import SupportGraph
from backend.ports.memory import Memory
from backend.ports.vector_store import VectorStore

logger = logging.getLogger("gigacorp.admin")


def build_admin_router(
    customer_service: CustomerService,
    kb_manager: KnowledgeBaseManager,
    orchestrator: SupportGraph,
    memory: Memory,
    vector_store: VectorStore,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])
    admin_only = [Depends(require_role("admin"))]

    @router.get("/dashboard", dependencies=admin_only)
    async def dashboard(db: AsyncSession = Depends(get_db)):
        uc = await db.execute(select(func.count(User.id)))
        cc = await db.execute(select(func.count(CustomerProfile.id)))
        oc = await db.execute(select(func.count(Order.id)))
        tc = await db.execute(select(func.count(SupportTicket.id)))
        otc = await db.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.status == TicketStatus.OPEN)
        )
        itc = await db.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.status == TicketStatus.IN_PROGRESS)
        )
        sc = await db.execute(select(func.count(Shipment.id)))
        rc = await db.execute(
            select(func.count(ReturnRequest.id)).where(ReturnRequest.status == ReturnStatus.REQUESTED)
        )
        sessions = orchestrator.list_sessions()
        kb_status = kb_manager.status()

        return AdminDashboardStats(
            total_users=uc.scalar() or 0,
            total_customers=cc.scalar() or 0,
            total_orders=oc.scalar() or 0,
            total_tickets=tc.scalar() or 0,
            open_tickets=(otc.scalar() or 0) + (itc.scalar() or 0),
            pending_tickets=otc.scalar() or 0,
            total_shipments=sc.scalar() or 0,
            pending_refunds=rc.scalar() or 0,
            kb_chunks=kb_status.get("chunk_count", 0),
            kb_initialized=kb_status.get("initialized", False),
            active_sessions=len(sessions),
            total_conversations=len(sessions),
        )

    @router.get("/users", dependencies=admin_only)
    async def list_users(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        search: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
    ):
        query = select(User)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                User.email.ilike(pattern) | User.username.ilike(pattern) | User.display_name.ilike(pattern)
            )
        query = query.order_by(desc(User.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        return {
            "users": [u.to_dict() for u in users],
            "total": len(users),
            "skip": skip,
            "limit": limit,
        }

    @router.patch("/users/{user_id}/role", dependencies=admin_only)
    async def update_user_role(
        user_id: UUID, body: AdminRoleUpdate, db: AsyncSession = Depends(get_db)
    ):
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        try:
            user.role = UserRole(body.role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")
        user.updated_at = datetime.utcnow()
        await db.flush()
        return {"status": "updated", "user": user.to_dict()}

    @router.get("/customers", dependencies=admin_only)
    async def list_customers(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        search: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
    ):
        query = select(CustomerProfile)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                CustomerProfile.display_name.ilike(pattern)
                | CustomerProfile.email.ilike(pattern)
                | CustomerProfile.company.ilike(pattern)
            )
        query = query.order_by(desc(CustomerProfile.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        customers = result.scalars().all()

        await db.execute(select(func.count(Order.id)).where(Order.customer_id.in_([c.id for c in customers])))
        order_counts = {}
        if customers:
            from sqlalchemy import func as sf
            counts = await db.execute(
                select(Order.customer_id, sf.count(Order.id).label("cnt"))
                .where(Order.customer_id.in_([c.id for c in customers]))
                .group_by(Order.customer_id)
            )
            for row in counts:
                order_counts[str(row.customer_id)] = row.cnt

        return {
            "customers": [
                {
                    "id": str(c.id),
                    "user_id": str(c.user_id) if c.user_id else None,
                    "display_name": c.display_name,
                    "email": c.email,
                    "company": c.company,
                    "phone": c.phone,
                    "account_status": c.account_status.value if c.account_status else "active",
                    "loyalty_tier": c.loyalty_tier.value if c.loyalty_tier else "bronze",
                    "loyalty_points": c.loyalty_points,
                    "order_count": order_counts.get(str(c.id), 0),
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in customers
            ],
            "total": len(customers),
            "skip": skip,
            "limit": limit,
        }

    @router.get("/customers/{customer_id}", dependencies=admin_only)
    async def get_customer_detail(
        customer_id: UUID, db: AsyncSession = Depends(get_db)
    ):
        result = await db.execute(select(CustomerProfile).where(CustomerProfile.id == customer_id))
        c = result.scalar_one_or_none()
        if not c:
            raise HTTPException(status_code=404, detail="Customer not found")

        orders_result = await db.execute(
            select(Order).where(Order.customer_id == c.id).order_by(desc(Order.created_at)).limit(20)
        )
        orders = orders_result.scalars().all()

        tickets_result = await db.execute(
            select(SupportTicket).where(SupportTicket.customer_id == c.id)
            .order_by(desc(SupportTicket.created_at)).limit(20)
        )
        tickets = tickets_result.scalars().all()

        shipments_result = await db.execute(
            select(Shipment).where(Shipment.customer_id == c.id)
            .order_by(desc(Shipment.created_at)).limit(20)
        )
        shipments = shipments_result.scalars().all()

        return {
            "customer": {
                "id": str(c.id),
                "user_id": str(c.user_id) if c.user_id else None,
                "display_name": c.display_name,
                "email": c.email,
                "company": c.company,
                "phone": c.phone,
                "account_status": c.account_status.value if c.account_status else "active",
                "loyalty_tier": c.loyalty_tier.value if c.loyalty_tier else "bronze",
                "loyalty_points": c.loyalty_points,
                "total_spent": float(c.total_spent) if c.total_spent else 0,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            },
            "orders": [
                {
                    "order_number": o.order_number,
                    "status": o.status.value,
                    "total": float(o.total),
                    "created_at": o.created_at.isoformat(),
                }
                for o in orders
            ],
            "tickets": [
                {
                    "ticket_number": t.ticket_number,
                    "subject": t.subject,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "created_at": t.created_at.isoformat(),
                }
                for t in tickets
            ],
            "shipments": [
                {
                    "tracking_number": s.tracking_number,
                    "courier": s.courier,
                    "status": s.status.value if hasattr(s.status, 'value') else s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in shipments
            ],
        }

    @router.get("/orders", dependencies=admin_only)
    async def list_orders(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        status: Optional[str] = None,
        search: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
    ):
        query = select(Order)
        if status:
            try:
                st = OrderStatus(status)
                query = query.where(Order.status == st)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        if search:
            query = query.where(Order.order_number.ilike(f"%{search}%"))
        query = query.order_by(desc(Order.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        orders = result.scalars().all()
        return {
            "orders": [
                {
                    "id": str(o.id),
                    "order_number": o.order_number,
                    "customer_id": str(o.customer_id),
                    "status": o.status.value,
                    "total": float(o.total),
                    "created_at": o.created_at.isoformat(),
                }
                for o in orders
            ],
            "total": len(orders),
        }

    @router.get("/orders/{order_number}", dependencies=admin_only)
    async def get_order_detail(order_number: str, db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Order).where(Order.order_number == order_number))
        o = result.scalar_one_or_none()
        if not o:
            raise HTTPException(status_code=404, detail="Order not found")
        logs_result = await db.execute(
            select(OrderStatusLog).where(OrderStatusLog.order_id == o.id)
            .order_by(desc(OrderStatusLog.created_at))
        )
        logs = logs_result.scalars().all()
        return {
            "id": str(o.id),
            "order_number": o.order_number,
            "customer_id": str(o.customer_id),
            "status": o.status.value,
            "payment_status": o.payment_status.value if o.payment_status else None,
            "total": float(o.total),
            "shipping_method": o.shipping_method,
            "tracking_number": o.tracking_number,
            "carrier": o.carrier,
            "estimated_delivery": o.estimated_delivery.isoformat() if o.estimated_delivery else None,
            "notes": o.notes,
            "created_at": o.created_at.isoformat(),
            "status_logs": [
                {
                    "from_status": entry.from_status,
                    "to_status": entry.to_status,
                    "changed_by": entry.changed_by,
                    "notes": entry.notes,
                    "created_at": entry.created_at.isoformat(),
                }
                for entry in logs
            ],
        }

    @router.patch("/orders/{order_number}/status", dependencies=admin_only)
    async def update_order_status(
        order_number: str, body: AdminOrderUpdate, db: AsyncSession = Depends(get_db)
    ):
        result = await db.execute(select(Order).where(Order.order_number == order_number))
        o = result.scalar_one_or_none()
        if not o:
            raise HTTPException(status_code=404, detail="Order not found")
        try:
            new_status = OrderStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
        old_status = o.status.value
        o.status = new_status
        o.updated_at = datetime.utcnow()
        log = OrderStatusLog(
            order_id=o.id,
            from_status=old_status,
            to_status=body.status,
            changed_by="admin",
            notes=body.notes,
        )
        db.add(log)
        await db.flush()
        return {"status": "updated", "order_number": o.order_number, "new_status": body.status}

    @router.get("/tickets", dependencies=admin_only)
    async def list_tickets(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        status: Optional[str] = None,
        search: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
    ):
        query = select(SupportTicket)
        if status:
            try:
                st = TicketStatus(status)
                query = query.where(SupportTicket.status == st)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        if search:
            query = query.where(
                SupportTicket.ticket_number.ilike(f"%{search}%")
                | SupportTicket.subject.ilike(f"%{search}%")
            )
        query = query.order_by(desc(SupportTicket.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        tickets = result.scalars().all()

        cc = {}
        if tickets:
            from sqlalchemy import func as sf
            counts = await db.execute(
                select(SupportTicket.id, sf.count(TicketComment.id).label("cnt"))
                .outerjoin(TicketComment, TicketComment.ticket_id == SupportTicket.id)
                .where(SupportTicket.id.in_([t.id for t in tickets]))
                .group_by(SupportTicket.id)
            )
            for row in counts:
                cc[str(row.id)] = row.cnt

        return {
            "tickets": [
                {
                    "id": str(t.id),
                    "ticket_number": t.ticket_number,
                    "customer_id": str(t.customer_id),
                    "subject": t.subject,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "category": t.category,
                    "assigned_to": t.assigned_to,
                    "comment_count": cc.get(str(t.id), 0),
                    "created_at": t.created_at.isoformat(),
                }
                for t in tickets
            ],
            "total": len(tickets),
        }

    @router.get("/tickets/{ticket_id}", dependencies=admin_only)
    async def get_ticket_detail(ticket_id: UUID, db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        t = result.scalar_one_or_none()
        if not t:
            raise HTTPException(status_code=404, detail="Ticket not found")
        comments_result = await db.execute(
            select(TicketComment).where(TicketComment.ticket_id == t.id)
            .order_by(TicketComment.created_at)
        )
        comments = comments_result.scalars().all()
        return {
            "id": str(t.id),
            "ticket_number": t.ticket_number,
            "customer_id": str(t.customer_id),
            "subject": t.subject,
            "status": t.status.value,
            "priority": t.priority.value,
            "category": t.category,
            "subcategory": t.subcategory,
            "description": t.description,
            "assigned_to": t.assigned_to,
            "resolution": t.resolution,
            "related_order_number": t.related_order_number,
            "escalation_reason": t.escalation_reason,
            "tags": t.tags,
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            "created_at": t.created_at.isoformat(),
            "comments": [
                {
                    "id": str(c.id),
                    "author": c.author,
                    "body": c.body,
                    "is_internal": c.is_internal,
                    "created_at": c.created_at.isoformat(),
                }
                for c in comments
            ],
        }

    @router.patch("/tickets/{ticket_id}", dependencies=admin_only)
    async def update_ticket(
        ticket_id: UUID, body: AdminTicketUpdate, db: AsyncSession = Depends(get_db)
    ):
        result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        t = result.scalar_one_or_none()
        if not t:
            raise HTTPException(status_code=404, detail="Ticket not found")
        now = datetime.utcnow()
        if body.status:
            try:
                t.status = TicketStatus(body.status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
            if body.status == "resolved":
                t.resolved_at = now
            elif body.status == "closed":
                t.closed_at = now
                t.closed_by = "admin"
        if body.assigned_to is not None:
            t.assigned_to = body.assigned_to
        t.updated_at = now
        if body.note:
            comment = TicketComment(
                ticket_id=t.id, author="Admin", body=body.note, is_internal=True,
            )
            db.add(comment)
        await db.flush()
        return {"status": "updated", "ticket_number": t.ticket_number}

    @router.post("/tickets/{ticket_id}/comments", dependencies=admin_only)
    async def add_ticket_comment(
        ticket_id: UUID, body: AdminTicketComment, db: AsyncSession = Depends(get_db)
    ):
        result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        t = result.scalar_one_or_none()
        if not t:
            raise HTTPException(status_code=404, detail="Ticket not found")
        comment = TicketComment(
            ticket_id=t.id, author="Admin", body=body.body, is_internal=body.is_internal,
        )
        db.add(comment)
        t.updated_at = datetime.utcnow()
        await db.flush()
        return {"status": "comment_added", "comment_id": str(comment.id)}

    @router.get("/refunds", dependencies=admin_only)
    async def list_refunds(
        status: Optional[str] = None,
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        db: AsyncSession = Depends(get_db),
    ):
        query = select(ReturnRequest, Order.order_number, Order.customer_id).join(
            Order, ReturnRequest.order_id == Order.id
        )
        if status:
            try:
                rs = ReturnStatus(status)
                query = query.where(ReturnRequest.status == rs)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        query = query.order_by(desc(ReturnRequest.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        rows = result.all()
        return {
            "refunds": [
                {
                    "id": str(r.id),
                    "order_number": order_number,
                    "customer_id": str(customer_id),
                    "reason": r.reason,
                    "status": r.status.value,
                    "refund_amount": float(r.refund_amount) if r.refund_amount else 0,
                    "rma_number": r.rma_number,
                    "created_at": r.created_at.isoformat(),
                }
                for r, order_number, customer_id in rows
            ],
            "total": len(rows),
        }

    @router.post("/refunds/{refund_id}/approve", dependencies=admin_only)
    async def approve_refund(
        refund_id: UUID, body: AdminRefundAction = AdminRefundAction(),
        db: AsyncSession = Depends(get_db),
    ):
        result = await db.execute(select(ReturnRequest).where(ReturnRequest.id == refund_id))
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="Refund not found")
        if r.status != ReturnStatus.REQUESTED:
            raise HTTPException(status_code=400, detail=f"Refund is already {r.status.value}")
        r.status = ReturnStatus.APPROVED
        r.notes = (r.notes or "") + f"\n[Admin approved: {body.notes or 'No notes'}]"
        r.updated_at = datetime.utcnow()
        await db.flush()
        return {"status": "approved", "refund_id": str(r.id)}

    @router.post("/refunds/{refund_id}/reject", dependencies=admin_only)
    async def reject_refund(
        refund_id: UUID, body: AdminRefundAction = AdminRefundAction(),
        db: AsyncSession = Depends(get_db),
    ):
        result = await db.execute(select(ReturnRequest).where(ReturnRequest.id == refund_id))
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="Refund not found")
        if r.status != ReturnStatus.REQUESTED:
            raise HTTPException(status_code=400, detail=f"Refund is already {r.status.value}")
        r.status = ReturnStatus.REJECTED
        r.notes = (r.notes or "") + f"\n[Admin rejected: {body.notes or 'No notes'}]"
        r.updated_at = datetime.utcnow()
        await db.flush()
        return {"status": "rejected", "refund_id": str(r.id)}

    @router.get("/shipments", dependencies=admin_only)
    async def list_shipments(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        status: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
    ):
        query = select(Shipment)
        if status:
            try:
                ss = ShipmentStatus(status)
                query = query.where(Shipment.status == ss)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        query = query.order_by(desc(Shipment.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        shipments = result.scalars().all()
        return {
            "shipments": [
                {
                    "id": str(s.id),
                    "tracking_number": s.tracking_number,
                    "courier": s.courier,
                    "customer_id": str(s.customer_id) if s.customer_id else None,
                    "status": s.status.value,
                    "current_location": s.current_location,
                    "estimated_delivery": s.estimated_delivery.isoformat() if s.estimated_delivery else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in shipments
            ],
            "total": len(shipments),
        }

    @router.post("/shipments", dependencies=admin_only)
    async def create_shipment(
        body: AdminShipmentCreate, db: AsyncSession = Depends(get_db)
    ):
        order_result = await db.execute(
            select(Order).where(Order.order_number == body.order_number)
        )
        o = order_result.scalar_one_or_none()
        if not o:
            raise HTTPException(status_code=404, detail="Order not found")
        try:
            ss = ShipmentStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
        now = datetime.utcnow()
        shipment = Shipment(
            customer_id=o.customer_id,
            order_id=o.id,
            tracking_number=body.tracking_number,
            courier=body.courier,
            courier_code=body.courier_code,
            status=ss,
            estimated_delivery=datetime.fromisoformat(body.estimated_delivery) if body.estimated_delivery else None,
            current_location="",
            weight_lb=body.weight_lb,
            package_count=body.package_count,
            created_at=now,
        )
        db.add(shipment)
        await db.flush()
        event = ShipmentEvent(
            shipment_id=shipment.id,
            status=ss.value,
            location="Shipping label created",
            description="Shipment created by admin",
            timestamp=now,
        )
        db.add(event)
        await db.flush()
        return {"status": "created", "tracking_number": shipment.tracking_number}

    @router.patch("/shipments/{tracking_number}", dependencies=admin_only)
    async def update_shipment(
        tracking_number: str, body: AdminShipmentUpdate,
        db: AsyncSession = Depends(get_db),
    ):
        result = await db.execute(
            select(Shipment).where(Shipment.tracking_number == tracking_number)
        )
        s = result.scalar_one_or_none()
        if not s:
            raise HTTPException(status_code=404, detail="Shipment not found")
        now = datetime.utcnow()
        if body.status:
            try:
                s.status = ShipmentStatus(body.status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
            event = ShipmentEvent(
                shipment_id=s.id, status=body.status,
                location=body.current_location or s.current_location or "",
                description=f"Status updated to {body.status}",
                timestamp=now,
            )
            db.add(event)
        if body.current_location is not None:
            s.current_location = body.current_location
        if body.estimated_delivery is not None:
            s.estimated_delivery = datetime.fromisoformat(body.estimated_delivery)
        if body.last_update is not None:
            s.last_update = body.last_update
        s.updated_at = now
        await db.flush()
        return {"status": "updated", "tracking_number": s.tracking_number}

    @router.get("/knowledge-base", dependencies=admin_only)
    async def list_knowledge_base():
        kb_path = settings.knowledge_base_path
        files = []
        if kb_path.exists():
            for f in sorted(kb_path.iterdir()):
                if f.is_file() and f.suffix.lower() in (".md", ".txt", ".pdf", ".html"):
                    files.append({
                        "name": f.name,
                        "size_bytes": f.stat().st_size,
                        "last_modified": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
                    })
        return {"files": files, "total": len(files)}

    @router.post("/knowledge-base/upload", dependencies=admin_only)
    async def upload_knowledge_base_file(file: UploadFile = File(...)):
        kb_path = settings.knowledge_base_path
        kb_path.mkdir(parents=True, exist_ok=True)
        file_path = kb_path / file.filename
        content = await file.read()
        file_path.write_bytes(content)
        result = kb_manager.ingest_file(str(file_path))
        return {
            "status": result.get("status", "success"),
            "filename": file.filename,
            "chunks_ingested": result.get("chunks_ingested", 0),
            "message": result.get("message", "File uploaded and ingested"),
        }

    @router.delete("/knowledge-base/{filename}", dependencies=admin_only)
    async def delete_knowledge_base_file(filename: str):
        kb_path = settings.knowledge_base_path / filename
        if not kb_path.exists() or not kb_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        kb_path.unlink()
        kb_manager.rebuild()
        return {"status": "deleted", "filename": filename}

    @router.post("/knowledge-base/rebuild", dependencies=admin_only)
    async def rebuild_knowledge_base():
        try:
            result = kb_manager.rebuild()
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/analytics/overview", dependencies=admin_only)
    async def analytics_overview(db: AsyncSession = Depends(get_db)):
        total_orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
        total_tickets = (await db.execute(select(func.count(SupportTicket.id)))).scalar() or 0
        resolved_tickets = (await db.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.status == TicketStatus.RESOLVED)
        )).scalar() or 0
        sessions = orchestrator.list_sessions()
        return {
            "total_orders": total_orders,
            "total_tickets": total_tickets,
            "resolved_tickets": resolved_tickets,
            "resolution_rate": round(resolved_tickets / total_tickets * 100, 1) if total_tickets > 0 else 0,
            "active_sessions": len(sessions),
        }

    @router.get("/sessions", dependencies=admin_only)
    async def list_sessions(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
        all_sessions = orchestrator.list_sessions()
        total = len(all_sessions)
        paginated = all_sessions[skip:skip + limit]
        result = []
        for sid in paginated:
            try:
                info = memory.get_session_info(sid)
                if info:
                    result.append(info.to_dict())
                else:
                    result.append({"session_id": sid, "message_count": 0})
            except Exception:
                result.append({"session_id": sid, "message_count": 0})
        return {"sessions": result, "total": total}

    @router.get("/sessions/{session_id}/messages", dependencies=admin_only)
    async def get_session_messages(session_id: str):
        try:
            messages = orchestrator.get_history(session_id)
            summary = ""
            try:
                summary = memory.get_summary(session_id)
            except Exception:
                pass
            return {"session_id": session_id, "messages": messages, "summary": summary}
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Session not found: {e}")

    @router.get("/health", dependencies=admin_only)
    async def system_health(db: AsyncSession = Depends(get_db)):
        checks = {}
        try:
            await db.execute(select(func.count(User.id)))
            checks["database"] = {"status": "healthy", "detail": "Connected"}
        except Exception as e:
            checks["database"] = {"status": "unhealthy", "detail": str(e)}

        try:
            vs_init = vector_store.is_initialized if hasattr(vector_store, 'is_initialized') else False
            vs_count = vector_store.chunk_count if hasattr(vector_store, 'chunk_count') else 0
            checks["vector_store"] = {
                "status": "healthy" if vs_init else "degraded",
                "detail": f"{'Initialized' if vs_init else 'Not initialized'} ({vs_count} chunks)",
            }
        except Exception as e:
            checks["vector_store"] = {"status": "unhealthy", "detail": str(e)}

        try:
            sessions = orchestrator.list_sessions()
            checks["memory"] = {"status": "healthy", "detail": f"{len(sessions)} active sessions"}
        except Exception as e:
            checks["memory"] = {"status": "unhealthy", "detail": str(e)}

        try:
            kb_status = kb_manager.status()
            checks["knowledge_base"] = {
                "status": "healthy" if kb_status.get("initialized") else "degraded",
                "detail": f"{kb_status.get('chunk_count', 0)} chunks",
            }
        except Exception as e:
            checks["knowledge_base"] = {"status": "unhealthy", "detail": str(e)}

        llm_available = orchestrator.llm is not None
        checks["llm"] = {
            "status": "healthy" if llm_available else "degraded",
            "detail": "LLM configured" if llm_available else "Rule-based mode (no LLM)",
        }

        overall = all(c.get("status") == "healthy" for c in checks.values())
        return {"overall": "healthy" if overall else "degraded", "checks": checks}

    return router
