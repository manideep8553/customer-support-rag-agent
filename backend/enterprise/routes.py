import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.database import get_db
from backend.auth.dependencies import get_current_user, require_permission, require_role
from backend.auth.models import User, Permission
from backend.config import settings
from backend.enterprise.audit.service import get_audit_service
from backend.enterprise.audit.models import AuditAction
from backend.enterprise.notifications.service import get_notification_service
from backend.enterprise.file_store.service import get_file_store
from backend.enterprise.file_store.models import StoredFile
from backend.enterprise.monitoring.metrics import get_metrics_collector

logger = logging.getLogger("gigacorp.enterprise.routes")


def build_enterprise_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/enterprise", tags=["Enterprise"])

    # ── Audit Logs ────────────────────────────────────────────────────

    @router.get(
        "/audit-logs",
        dependencies=[Depends(require_permission(Permission.READ_AUDIT_LOGS))],
    )
    async def get_audit_logs(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        outcome: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
    ):
        audit = get_audit_service()
        action_enum = AuditAction(action) if action else None
        from_dt = datetime.fromisoformat(from_date) if from_date else None
        to_dt = datetime.fromisoformat(to_date) if to_date else None

        entries, total = await audit.query(
            db=db,
            limit=limit,
            offset=offset,
            actor_id=actor_id,
            action=action_enum,
            resource_type=resource_type,
            resource_id=resource_id,
            from_date=from_dt,
            to_date=to_dt,
            outcome=outcome,
        )
        return {"entries": entries, "total": total, "limit": limit, "offset": offset}

    @router.get("/audit-logs/summary", dependencies=[Depends(require_permission(Permission.READ_AUDIT_LOGS))])
    async def audit_summary(db: AsyncSession = Depends(get_db)):
        audit = get_audit_service()
        entries, total = await audit.query(db=db, limit=1)
        return {
            "total_entries": total,
            "audit_enabled": settings.audit_enabled,
        }

    # ── Notifications ─────────────────────────────────────────────────

    @router.get("/notifications")
    async def get_my_notifications(current_user: User = Depends(get_current_user)):
        ws = get_notification_service()
        return {"status": "notifications_available", "user_id": str(current_user.id)}

    @router.post("/notifications/send", dependencies=[Depends(require_permission(Permission.SEND_NOTIFICATIONS))])
    async def send_notification(
        user_id: str,
        title: str,
        body: str,
        category: str = "general",
        current_user: User = Depends(get_current_user),
    ):
        service = get_notification_service()
        notification = await service.send(
            user_id=user_id,
            title=title,
            body=body,
            category=category,
        )
        return {"status": "sent", "notification_id": notification.id}

    # ── File Uploads ──────────────────────────────────────────────────

    @router.post("/files/upload")
    async def upload_file(
        file: UploadFile = File(...),
        is_public: bool = Form(False),
        current_user: User = Depends(get_current_user),
    ):
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        allowed = {e.strip().lstrip(".") for e in settings.allowed_upload_extensions.split(",")}
        if ext and ext not in allowed:
            raise HTTPException(status_code=400, detail=f"File type '.{ext}' not allowed")

        content = await file.read()
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_size_mb} MB limit")

        store = get_file_store()
        stored = await store.upload(
            content=content,
            original_filename=file.filename or "unnamed",
            content_type=file.content_type,
            uploaded_by=str(current_user.id),
            is_public=is_public,
        )
        return {
            "status": "uploaded",
            "file": stored.model_dump(),
            "url": await store.get_url(stored.stored_path),
        }

    @router.get("/files/{file_id}")
    async def get_file(file_id: str):
        store = get_file_store()
        # In a real app, resolve file_id to stored_path from DB
        return {"file_id": file_id, "note": "File retrieval requires stored_path lookup"}

    # ── Metrics ───────────────────────────────────────────────────────

    @router.get("/metrics")
    async def get_metrics():
        collector = get_metrics_collector()
        return collector.snapshot()

    @router.get("/health/detailed")
    async def detailed_health(db: AsyncSession = Depends(get_db)):
        checks = {}
        try:
            from sqlalchemy import select, func
            from backend.auth.models import User
            await db.execute(select(func.count(User.id)))
            checks["database"] = {"status": "healthy"}
        except Exception as e:
            checks["database"] = {"status": "unhealthy", "error": str(e)}

        try:
            from backend.di.container import container
            vs = container.vector_store
            checks["vector_store"] = {
                "status": "healthy" if vs and vs.is_initialized else "degraded",
            }
        except Exception as e:
            checks["vector_store"] = {"status": "unhealthy", "error": str(e)}

        try:
            from backend.enterprise.cache_provider.redis_cache import get_cache
            cache = await get_cache()
            await cache.exists("health_check")
            checks["redis"] = {"status": "healthy"}
        except Exception as e:
            checks["redis"] = {"status": "unhealthy", "error": str(e)}

        try:
            checks["email"] = {
                "status": "configured" if settings.smtp_host else "not_configured",
            }
        except Exception as e:
            checks["email"] = {"status": "unhealthy", "error": str(e)}

        overall = all(c.get("status") == "healthy" for c in checks.values())
        return {
            "overall": "healthy" if overall else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        }

    # ── Rate Limit Status ─────────────────────────────────────────────

    @router.get("/rate-limits")
    async def get_rate_limits(current_user: User = Depends(get_current_user)):
        return {
            "chat_per_minute": settings.rate_limit_chat_per_minute,
            "chat_per_hour": settings.rate_limit_chat_per_hour,
            "ingest_per_minute": settings.rate_limit_ingest_per_minute,
            "auth_per_minute": settings.rate_limit_auth_per_minute,
        }

    return router
