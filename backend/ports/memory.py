from typing import Protocol, Optional
from datetime import datetime


class MessageEntry:
    def __init__(self, role: str, content: str, timestamp: str | None = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}


class SessionInfo:
    def __init__(self, session_id: str, created_at: str, last_active: str, message_count: int):
        self.session_id = session_id
        self.created_at = created_at
        self.last_active = last_active
        self.message_count = message_count

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "message_count": self.message_count,
        }


class Memory(Protocol):
    def create_session(self) -> str: ...

    def add_turn(self, session_id: str, role: str, content: str) -> None: ...

    def get_history(self, session_id: str) -> str: ...

    def get_messages(self, session_id: str) -> list[dict]: ...

    def summarize(self, session_id: str, summary: str) -> None: ...

    def get_summary(self, session_id: str) -> str: ...

    def list_sessions(self) -> list[str]: ...

    def get_session_info(self, session_id: str) -> Optional[SessionInfo]: ...

    def delete_session(self, session_id: str) -> bool: ...
