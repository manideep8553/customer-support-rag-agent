import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from traceback import format_exception

from fastapi import APIRouter, Depends, HTTPException, Body, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    SessionCreate,
    SessionInfo as SessionInfoSchema,
    HistoryRequest,
    HistoryResponse,
    MessageEntry,
    IngestRequest,
    IngestResponse,
    RebuildResponse,
    ClearMemoryResponse,
    DiagnosticsRequest,
    DiagnosticsResponse,
    DiagnosticsResult,
    ErrorDetail,
    SourceCitation,
)
from backend.ports.memory import SessionInfo
from backend.orchestration.graph import SupportGraph
from backend.knowledge_base.store import KnowledgeBaseManager
from backend.config import settings
from backend.errors import (
    GigaCorpError,
    EmbeddingError,
    VectorStoreError,
    LLMError,
    DocumentLoadError,
    RetrievalError,
    MemoryError,
    friendly_error,
    log_exception,
)
from backend.cache import embedding_cache, response_cache, token_cache
from backend.security import (
    verify_api_key,
    chat_rate_limiter,
    ingest_rate_limiter,
    get_client_ip,
    sanitize_text,
    validate_file_path,
)
from backend.auth.dependencies import get_optional_user
from backend.auth.models import User
from backend.auth.database import get_db
from backend.customer.service import CustomerService

logger = logging.getLogger(__name__)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _compute_confidence(sources: list[dict]) -> float:
    if not sources:
        return 0.0
    scores = [s.get("score", 0.0) for s in sources if isinstance(s.get("score"), (int, float))]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _format_sources(sources: list[dict]) -> list[SourceCitation]:
    return [
        SourceCitation(
            content=s.get("content", ""),
            score=s.get("score", 0.0),
            source=s.get("source", "unknown"),
            metadata=s.get("metadata", {}),
        )
        for s in sources
    ]


def _session_info_to_schema(info: SessionInfo) -> SessionInfoSchema:
    d = info.to_dict()
    d["created_at"] = datetime.fromisoformat(d["created_at"])
    d["last_active"] = datetime.fromisoformat(d["last_active"])
    return SessionInfoSchema(**d)


def build_router(orch: SupportGraph, kb_manager: KnowledgeBaseManager, customer_service: CustomerService | None = None) -> APIRouter:
    router = APIRouter(dependencies=[Depends(verify_api_key)])

    # ── Chat ───────────────────────────────────────────────────────────
    async def _chat_rate_limit(request: Request):
        client_ip = get_client_ip(request)
        chat_rate_limiter.check(client_ip)

    @router.post(
        "/chat",
        dependencies=[Depends(_chat_rate_limit)],
        response_model=ChatResponse,
        responses={
            200: {"description": "Successful response with answer and sources"},
            400: {"description": "Invalid request (empty message, etc.)"},
            422: {"description": "Validation error"},
            500: {"description": "Internal server error"},
        },
    )
    async def chat(request: ChatRequest, current_user: User = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        sanitized_message = sanitize_text(request.message, max_length=2000)
        start = time.monotonic()
        user_info = {"display_name": current_user.display_name, "company": current_user.company} if current_user else None
        if current_user and customer_service:
            try:
                customer_data = await customer_service.get_chat_context(current_user.id, db)
                if customer_data:
                    user_info["customer_data"] = customer_data
            except Exception as e:
                logger.warning("Failed to load customer data for user %s: %s", current_user.id, e)
        try:
            result = orch.query(request.session_id, sanitized_message, user_info=user_info)
        except GigaCorpError as e:
            log_exception(e, "chat.gigacorp_error")
            raise HTTPException(status_code=500, detail=friendly_error(e))
        except Exception as e:
            log_exception(e, "chat.unexpected_error")
            raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")

        elapsed = (time.monotonic() - start) * 1000
        sources_raw = result.get("sources", [])
        confidence = _compute_confidence(sources_raw)

        return ChatResponse(
            session_id=request.session_id,
            conversation_id=request.session_id,
            answer=result.get("answer", ""),
            sources=_format_sources(sources_raw),
            confidence=confidence,
            timestamp=_now(),
            processing_time_ms=round(elapsed, 1),
        )

    # ── Chat Stream ────────────────────────────────────────────────────
    @router.post(
        "/chat/stream",
        dependencies=[Depends(_chat_rate_limit)],
        response_class=EventSourceResponse,
        responses={
            200: {"description": "Server-Sent Events stream of tokens and sources"},
            400: {"description": "Invalid request"},
            422: {"description": "Validation error"},
        },
    )
    async def chat_stream(request: ChatRequest, current_user: User = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        sanitized_message = sanitize_text(request.message, max_length=2000)
        user_info = {"display_name": current_user.display_name, "company": current_user.company} if current_user else None
        if current_user and customer_service:
            try:
                customer_data = await customer_service.get_chat_context(current_user.id, db)
                if customer_data:
                    user_info["customer_data"] = customer_data
            except Exception as e:
                logger.warning("Failed to load customer data for user %s: %s", current_user.id, e)

        async def event_generator():
            try:
                async for event in orch.query_stream_llm(request.session_id, sanitized_message, user_info=user_info):
                    yield event
            except Exception as e:
                logger.exception("Stream error for session %s", request.session_id)
                yield f"data: {json.dumps({'type': 'error', 'detail': 'An error occurred processing your request.'})}\n\n"

        return EventSourceResponse(event_generator())

    # ── Sessions ──────────────────────────────────────────────────────
    @router.post(
        "/sessions",
        response_model=SessionInfoSchema,
        status_code=201,
        responses={
            201: {"description": "Session created"},
            409: {"description": "Session ID already exists"},
        },
    )
    async def create_session(body: SessionCreate = Body(default=None)):
        mem = orch.memory
        if body and body.session_id:
            existing = mem.get_session_info(body.session_id)
            if existing:
                return _session_info_to_schema(existing)
            session_id = body.session_id
            mem.create_session(session_id)
        else:
            session_id = mem.create_session()

        info = mem.get_session_info(session_id)
        if not info:
            info = SessionInfo(
                session_id=session_id,
                created_at=_now().isoformat(),
                last_active=_now().isoformat(),
                message_count=0,
            )
        return _session_info_to_schema(info)

    @router.get(
        "/sessions",
        response_model=list[SessionInfoSchema],
        responses={200: {"description": "List of all sessions"}},
    )
    async def list_sessions():
        mem = orch.memory
        session_ids = mem.list_sessions()
        result = []
        for sid in session_ids:
            info = mem.get_session_info(sid)
            if info:
                result.append(_session_info_to_schema(info))
        return result

    @router.get(
        "/sessions/{session_id}",
        response_model=SessionInfoSchema,
        responses={
            200: {"description": "Session info"},
            404: {"description": "Session not found"},
        },
    )
    async def get_session(session_id: str):
        info = orch.memory.get_session_info(session_id)
        if not info:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        return _session_info_to_schema(info)

    @router.delete(
        "/sessions/{session_id}",
        status_code=204,
        responses={
            204: {"description": "Session deleted"},
            404: {"description": "Session not found"},
        },
    )
    async def delete_session(session_id: str):
        deleted = orch.memory.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        return JSONResponse(status_code=204, content={})

    @router.post(
        "/sessions/{session_id}/memory/clear",
        response_model=ClearMemoryResponse,
        responses={
            200: {"description": "Session memory cleared"},
            404: {"description": "Session not found"},
        },
    )
    async def clear_session_memory(session_id: str):
        mem = orch.memory
        info = mem.get_session_info(session_id)
        if not info:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        try:
            mem.delete_session(session_id)
            mem.create_session(session_id)
        except Exception as e:
            logger.exception("Failed to clear memory for session %s", session_id)
            raise HTTPException(status_code=500, detail=str(e))
        return ClearMemoryResponse(
            status="success",
            session_id=session_id,
            message=f"Memory cleared for session '{session_id}'",
        )

    @router.post(
        "/sessions/{session_id}/history",
        response_model=HistoryResponse,
        responses={
            200: {"description": "Conversation history"},
            404: {"description": "Session not found"},
        },
    )
    async def get_history(session_id: str, body: HistoryRequest = Body(default=None)):
        limit = body.limit if body else 50
        messages = orch.get_history(session_id)
        if not messages:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or has no messages")
        entries = [
            MessageEntry(
                role=m["role"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]) if isinstance(m.get("timestamp"), str) else _now(),
            )
            for m in messages[-limit:]
        ]
        return HistoryResponse(session_id=session_id, messages=entries)

    @router.post(
        "/sessions/{session_id}/history/clear",
        response_model=ClearMemoryResponse,
        responses={
            200: {"description": "Conversation history cleared, session preserved"},
            404: {"description": "Session not found"},
        },
    )
    async def clear_session_history(session_id: str):
        mem = orch.memory
        info = mem.get_session_info(session_id)
        if not info:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        try:
            cleared = mem.clear_history(session_id)
            if not cleared:
                raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to clear history for session %s", session_id)
            raise HTTPException(status_code=500, detail=str(e))
        return ClearMemoryResponse(
            status="success",
            session_id=session_id,
            message=f"Chat history cleared for session '{session_id}'",
        )

    @router.post(
        "/memory/cleanup",
        responses={
            200: {"description": "Expired sessions cleaned up"},
        },
    )
    async def cleanup_expired_sessions():
        try:
            purged = orch.memory.cleanup_expired()
        except Exception as e:
            logger.exception("Memory cleanup error")
            raise HTTPException(status_code=500, detail=str(e))
        return {
            "status": "success",
            "sessions_purged": purged,
            "message": f"Cleaned up {purged} expired session(s)",
        }

    @router.post(
        "/cache/clear",
        responses={
            200: {"description": "All caches cleared"},
        },
    )
    async def clear_caches():
        try:
            embedding_cache.clear()
            response_cache.clear()
            token_cache.clear()
        except Exception as e:
            logger.exception("Cache clear error")
            raise HTTPException(status_code=500, detail=str(e))
        return {
            "status": "success",
            "message": "Embedding, response, and token caches cleared",
        }

    @router.get(
        "/cache/stats",
        responses={
            200: {"description": "Cache statistics"},
        },
    )
    async def cache_stats():
        return {
            "embedding_cache": embedding_cache.size,
            "response_cache": response_cache.size,
            "token_cache": token_cache.size,
        }

    # ── Ingest ─────────────────────────────────────────────────────────
    async def _ingest_rate_limit(request: Request):
        client_ip = get_client_ip(request)
        ingest_rate_limiter.check(client_ip)

    @router.post(
        "/ingest",
        dependencies=[Depends(_ingest_rate_limit)],
        response_model=IngestResponse,
        status_code=201,
        responses={
            201: {"description": "Documents ingested"},
            400: {"description": "Invalid request"},
            403: {"description": "File path outside allowed directory"},
            404: {"description": "File not found"},
            422: {"description": "Validation error"},
        },
    )
    async def ingest(request: IngestRequest):
        if request.file_path and request.text:
            raise HTTPException(
                status_code=400,
                detail="Provide either file_path or text, not both",
            )
        try:
            if request.file_path:
                validated_path = validate_file_path(request.file_path)
                result = kb_manager.ingest_file(str(validated_path))
            elif request.text:
                sanitized = sanitize_text(request.text, max_length=100000)
                result = kb_manager.ingest_text(sanitized)
            else:
                result = kb_manager.ingest_file()
            return IngestResponse(**result)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Ingest error")
            raise HTTPException(status_code=500, detail=str(e))

    # ── Knowledge Base ────────────────────────────────────────────────
    @router.post(
        "/knowledge-base/rebuild",
        response_model=RebuildResponse,
        responses={
            200: {"description": "Vector store rebuilt successfully"},
            500: {"description": "Rebuild failed"},
        },
    )
    async def rebuild_knowledge_base():
        try:
            result = kb_manager.rebuild()
            return RebuildResponse(
                status=result.get("status", "success"),
                total_chunks=result.get("total_chunks", 0),
                files_processed=result.get("files_processed", 0),
                message=result.get("message", ""),
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception("Knowledge base rebuild error")
            raise HTTPException(status_code=500, detail=str(e))

    # ── Diagnostics ───────────────────────────────────────────────────
    @router.post(
        "/diagnostics/retrieval",
        response_model=DiagnosticsResponse,
        responses={
            200: {"description": "Retrieval diagnostic results"},
            422: {"description": "Validation error"},
        },
    )
    async def retrieval_diagnostics(request: DiagnosticsRequest):
        try:
            result = orch.retrieval_diagnostics(
                query=request.query,
                k=settings.top_k_retrieval,
                threshold=0.0,
            )
        except Exception as e:
            logger.exception("Retrieval diagnostics error")
            raise HTTPException(status_code=500, detail=str(e))

        return DiagnosticsResponse(
            query=result["query"],
            total_results=result["total_results"],
            threshold=settings.similarity_threshold,
            results=[
                DiagnosticsResult(
                    content=d["content"],
                    score=d["score"],
                    source=d["source"],
                    metadata=d.get("metadata", {}),
                    chunk_index=i,
                )
                for i, d in enumerate(result["results"])
            ],
        )

    # ── Health ─────────────────────────────────────────────────────────
    @router.get(
        "/health",
        responses={
            200: {"description": "System health status"},
            503: {"description": "Service unhealthy"},
        },
    )
    async def health():
        try:
            kb_status = kb_manager.status()
            return {
                "status": "healthy",
                "app_name": settings.app_name,
                "app_version": settings.app_version,
                "knowledge_base": {
                    "initialized": kb_status.get("initialized", False),
                    "chunk_count": kb_status.get("chunk_count", 0),
                },
                "active_sessions": len(orch.list_sessions()),
                "timestamp": _now().isoformat(),
            }
        except Exception as e:
            logger.exception("Health check error")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": _now().isoformat(),
                },
            )

    return router
