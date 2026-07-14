import time
import uuid
import logging
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.enterprise.audit.service import get_audit_service
from backend.enterprise.audit.models import AuditAction
from backend.enterprise.monitoring.metrics import get_metrics_collector

logger = logging.getLogger("gigacorp.middleware")


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        request.state.start_time = time.monotonic()

        async def send_with_correlation(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers.append((b"X-Correlation-ID", correlation_id.encode()))
                message["headers"] = headers
            await original_send(message)

        original_send = request.scope.get("send")
        if original_send:
            request.scope["send"] = send_with_correlation

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._audit = get_audit_service()
        self._exclude_paths: set[str] = {"/health", "/metrics", "/api/v1/health", "/api/v1/chat/stream"}
        self._exclude_prefixes: tuple = ("/static", "/assets")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self._exclude_paths or path.startswith(self._exclude_prefixes):
            return await call_next(request)

        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        start_time = getattr(request.state, "start_time", time.monotonic())

        try:
            response = await call_next(request)
            duration_ms = (time.monotonic() - start_time) * 1000

            if path.startswith("/api/"):
                actor_id = None
                actor_email = None
                actor_role = None
                try:
                    if hasattr(request, "user") and request.user:
                        actor_id = str(request.user.id)
                        actor_email = request.user.email
                        actor_role = request.user.role.value if hasattr(request.user, "role") else None
                except Exception:
                    pass

                await self._audit.log(
                    action=AuditAction.API_CALL,
                    resource_type="api",
                    resource_id=path,
                    actor_id=actor_id,
                    actor_email=actor_email,
                    actor_role=actor_role,
                    correlation_id=correlation_id,
                    outcome="success" if response.status_code < 400 else "error",
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    request_method=request.method,
                    request_path=path,
                    response_status=response.status_code,
                    duration_ms=int(duration_ms),
                )

            get_metrics_collector().timing("request.duration", duration_ms, {"path": path, "method": request.method})
            get_metrics_collector().increment("request.count", 1, {"path": path, "method": request.method, "status": str(response.status_code)})

            return response

        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            get_metrics_collector().increment("request.error", 1, {"path": path})
            raise


class MetricsEndpointMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            from starlette.responses import PlainTextResponse
            metrics = get_metrics_collector().prometheus_metrics()
            return PlainTextResponse(metrics)
        return await call_next(request)
