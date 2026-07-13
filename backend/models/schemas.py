from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class SourceCitation(BaseModel):
    content: str = Field(..., description="Retrieved text snippet")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    source: str = Field(..., description="Source document identifier")


class MessageEntry(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    stream: bool = Field(default=False, description="Enable streaming response")


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceCitation] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))


class SessionCreate(BaseModel):
    session_id: Optional[str] = None


class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    created_at: datetime
    last_active: datetime


class HistoryRequest(BaseModel):
    session_id: str
    limit: int = Field(default=50, ge=1, le=200)


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageEntry] = Field(default_factory=list)


class IngestRequest(BaseModel):
    file_path: Optional[str] = None
    text: Optional[str] = None


class IngestResponse(BaseModel):
    status: str
    chunks_ingested: int
    message: str


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
