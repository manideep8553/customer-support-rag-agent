import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.database import async_session_factory
from backend.config import settings
from backend.enterprise.audit.models import AuditAction, AuditLog

logger = logging.getLogger("gigacorp.audit")


class AuditService:
    def __init__(self):
        self._enabled = settings.audit_enabled

    async def log(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_email: Optional[str] = None,
        actor_role: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
        outcome: str = "success",
        error_message: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        request_body_preview: Optional[str] = None,
        response_status: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> Optional[str]:
        if not self._enabled:
            return None

        if request_body_preview and len(request_body_preview) > settings.audit_log_body_max_length:
            request_body_preview = request_body_preview[:settings.audit_log_body_max_length]

        entry_id = str(uuid.uuid4())
        try:
            async with async_session_factory() as db:
                log_entry = AuditLog(
                    id=uuid.UUID(entry_id),
                    timestamp=datetime.utcnow(),
                    actor_id=uuid.UUID(actor_id) if actor_id else None,
                    actor_email=actor_email,
                    actor_role=actor_role,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details or {},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    correlation_id=correlation_id or entry_id,
                    outcome=outcome,
                    error_message=error_message,
                    request_method=request_method,
                    request_path=request_path,
                    request_body_preview=request_body_preview,
                    response_status=response_status,
                    duration_ms=duration_ms,
                )
                db.add(log_entry)
                await db.commit()
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)

        return entry_id

    async def query(
        self,
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        actor_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        outcome: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        conditions = []
        if actor_id:
            conditions.append(AuditLog.actor_id == uuid.UUID(actor_id))
        if action:
            conditions.append(AuditLog.action == action)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if resource_id:
            conditions.append(AuditLog.resource_id == resource_id)
        if from_date:
            conditions.append(AuditLog.timestamp >= from_date)
        if to_date:
            conditions.append(AuditLog.timestamp <= to_date)
        if outcome:
            conditions.append(AuditLog.outcome == outcome)

        from sqlalchemy import and_, func

        query = select(AuditLog)
        if conditions:
            query = query.where(and_(*conditions))

        count_query = select(func.count(AuditLog.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = (await db.execute(count_query)).scalar() or 0

        query = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit)
        result = await db.execute(query)
        entries = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "timestamp": e.timestamp.isoformat(),
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "actor_email": e.actor_email,
                "actor_role": e.actor_role,
                "action": e.action.value,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "details": e.details,
                "ip_address": e.ip_address,
                "correlation_id": e.correlation_id,
                "outcome": e.outcome,
                "error_message": e.error_message,
                "request_method": e.request_method,
                "request_path": e.request_path,
                "response_status": e.response_status,
                "duration_ms": e.duration_ms,
            }
            for e in entries
        ], total


_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
