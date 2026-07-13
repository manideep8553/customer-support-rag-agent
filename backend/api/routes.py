import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Body, Request
from fastapi.responses import StreamingResponse
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
)
from backend.ports.memory import SessionInfo
from backend.orchestration.graph import SupportGraph
from backend.knowledge_base.store import KnowledgeBaseManager

logger = logging.getLogger(__name__)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def build_router(orch: SupportGraph, kb_manager: KnowledgeBaseManager) -> APIRouter:
    router = APIRouter()

    @router.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        try:
            result = orch.query(request.session_id, request.message)
            return ChatResponse(
                session_id=request.session_id,
                answer=result["answer"],
                sources=result.get("sources", []),
                timestamp=_now(),
            )
        except Exception as e:
            logger.exception("Chat error")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/chat/stream")
    async def chat_stream(request: ChatRequest):
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        async def event_generator():
            async for event in orch.query_stream_llm(request.session_id, request.message):
                yield event

        return EventSourceResponse(event_generator())

    @router.post("/sessions", response_model=SessionInfoSchema)
    async def create_session(body: SessionCreate = Body(default=None)):
        mem = orch.memory
        if body and body.session_id:
            session_id = body.session_id
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
        d = info.to_dict()
        d["created_at"] = datetime.fromisoformat(d["created_at"])
        d["last_active"] = datetime.fromisoformat(d["last_active"])
        return SessionInfoSchema(**d)

    @router.get("/sessions", response_model=list[SessionInfoSchema])
    async def list_sessions():
        mem = orch.memory
        session_ids = mem.list_sessions()
        result = []
        for sid in session_ids:
            info = mem.get_session_info(sid)
            if info:
                r = info.to_dict()
                r["created_at"] = datetime.fromisoformat(r["created_at"])
                r["last_active"] = datetime.fromisoformat(r["last_active"])
                result.append(SessionInfoSchema(**r))
        return result

    @router.get("/sessions/{session_id}", response_model=SessionInfoSchema)
    async def get_session(session_id: str):
        info = orch.memory.get_session_info(session_id)
        if not info:
            raise HTTPException(status_code=404, detail="Session not found")
        d = info.to_dict()
        d["created_at"] = datetime.fromisoformat(d["created_at"])
        d["last_active"] = datetime.fromisoformat(d["last_active"])
        return SessionInfoSchema(**d)

    @router.delete("/sessions/{session_id}")
    async def delete_session(session_id: str):
        orch.memory.delete_session(session_id)
        return {"status": "deleted"}

    @router.post("/sessions/{session_id}/history", response_model=HistoryResponse)
    async def get_history(session_id: str, body: HistoryRequest = Body(default=None)):
        if not body:
            body = HistoryRequest(session_id=session_id)
        messages = orch.get_history(session_id)
        if not messages:
            raise HTTPException(status_code=404, detail="Session not found")
        entries = [
            MessageEntry(
                role=m["role"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
            )
            for m in messages[-body.limit:]
        ]
        return HistoryResponse(session_id=session_id, messages=entries)

    @router.post("/ingest", response_model=IngestResponse)
    async def ingest(request: IngestRequest):
        try:
            if request.file_path:
                result = kb_manager.ingest_file(request.file_path)
            elif request.text:
                result = kb_manager.ingest_text(request.text)
            else:
                result = kb_manager.ingest_file()
            return IngestResponse(**result)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception("Ingest error")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/health")
    async def health():
        kb_status = kb_manager.status()
        return {
            "status": "healthy",
            "knowledge_base": kb_status,
            "timestamp": _now().isoformat(),
        }

    return router
