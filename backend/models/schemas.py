from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timezone


class SourceCitation(BaseModel):
    content: str = Field(..., description="Retrieved text snippet")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    source: str = Field(..., description="Source document identifier")
    metadata: dict = Field(default_factory=dict, description="Chunk metadata (heading, chunk_index, etc.)")


class MessageEntry(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    stream: bool = Field(default=False, description="Enable streaming response")

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be empty or whitespace only")
        return stripped


class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    conversation_id: str = Field(..., description="Alias for session_id")
    answer: str = Field(..., description="Generated response text")
    sources: list[SourceCitation] = Field(default_factory=list, description="Retrieved source chunks")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall confidence score (avg of source scores, 0 if no sources)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: Optional[float] = Field(default=None, description="Query processing time in milliseconds")


class SessionCreate(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Optional existing session ID to resume")


class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    created_at: datetime
    last_active: datetime


class HistoryRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    limit: int = Field(default=50, ge=1, le=200, description="Max messages to return")


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageEntry] = Field(default_factory=list)


class IngestRequest(BaseModel):
    file_path: Optional[str] = Field(default=None, description="Absolute path to a file to ingest")
    text: Optional[str] = Field(default=None, min_length=1, description="Raw text to chunk and ingest")

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("text must not be empty or whitespace only")
        return v


class IngestResponse(BaseModel):
    status: str
    chunks_ingested: int
    message: str


class RebuildResponse(BaseModel):
    status: str
    total_chunks: int
    files_processed: int
    message: str


class ClearMemoryResponse(BaseModel):
    status: str
    session_id: Optional[str] = Field(default=None, description="Session ID if cleared for a single session")
    message: str


class DiagnosticsRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Test query for retrieval diagnostics")

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Query cannot be empty or whitespace only")
        return stripped


class DiagnosticsResult(BaseModel):
    content: str
    score: float
    source: str
    metadata: dict
    chunk_index: int = Field(default=0, description="Position of this chunk in the results")


class DiagnosticsResponse(BaseModel):
    query: str
    total_results: int
    threshold: float
    results: list[DiagnosticsResult]


class ErrorDetail(BaseModel):
    detail: str
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
