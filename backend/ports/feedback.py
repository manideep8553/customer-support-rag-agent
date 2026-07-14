from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class FeedbackEntry:
    session_id: str
    message_index: int
    rating: int
    comment: str | None = None
    category: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EscalationRequest:
    session_id: str
    user_id: str
    reason: str
    priority: str = "normal"
    created_at: datetime = field(default_factory=datetime.utcnow)


class FeedbackStore(Protocol):
    async def submit(self, feedback: FeedbackEntry) -> str: ...

    async def get_by_session(self, session_id: str) -> list[FeedbackEntry]: ...

    async def get_aggregate(self, start: datetime, end: datetime) -> dict: ...


class EscalationHandler(Protocol):
    async def request_escalation(self, request: EscalationRequest) -> str: ...

    async def get_status(self, escalation_id: str) -> str: ...

    async def resolve(self, escalation_id: str) -> None: ...
