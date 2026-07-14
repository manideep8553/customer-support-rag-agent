import json
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

from backend.ports.memory import Memory, MessageEntry, SessionInfo
from backend.config import settings


class LangGraphMemory(Memory):
    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: dict[str, dict] = {}
        self._sessions_dir: Path = settings.vector_store_path / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._max_turns = settings.memory_max_turns
        self._checkpointer = None
        self._load_sessions()

    @property
    def checkpointer(self):
        return self._checkpointer

    def create_session(self) -> str:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()
        with self._lock:
            self._sessions[session_id] = {
                "session_id": session_id,
                "created_at": now,
                "last_active": now,
                "messages": [],
                "state": {},
                "summary": "",
            }
            self._save_session(session_id)
        return session_id

    def add_turn(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return
            entry = MessageEntry(role=role, content=content)
            session["messages"].append(entry.to_dict())
            session["last_active"] = datetime.utcnow().isoformat()
            max_messages = self._max_turns * 2
            if len(session["messages"]) > max_messages:
                session["messages"] = session["messages"][-max_messages:]
            self._save_session(session_id)

    def get_history(self, session_id: str) -> str:
        messages = self.get_messages(session_id)
        lines = []
        summary = self.get_summary(session_id)
        if summary:
            lines.append(f"[Previous conversation summary: {summary}]")
        for msg in messages:
            role = "Customer" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def summarize(self, session_id: str, summary: str) -> None:
        if not summary:
            return
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return
            session["summary"] = summary
            self._save_session(session_id)

    def get_summary(self, session_id: str) -> str:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return ""
            return session.get("summary", "")

    def get_messages(self, session_id: str) -> list[dict]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return []
            return list(session["messages"])

    def get_state(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return {}
            return dict(session.get("state", {}))

    def update_state(self, session_id: str, state: dict) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return
            session["state"].update(state)
            self._save_session(session_id)

    def list_sessions(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())

    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            return SessionInfo(
                session_id=session["session_id"],
                created_at=session["created_at"],
                last_active=session["last_active"],
                message_count=len(session["messages"]),
            )

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id not in self._sessions:
                return False
            del self._sessions[session_id]
            path = self._sessions_dir / f"{session_id}.json"
            if path.exists():
                path.unlink()
            return True

    def _save_session(self, session_id: str) -> None:
        data = self._sessions.get(session_id)
        if not data:
            return
        path = self._sessions_dir / f"{session_id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_sessions(self) -> None:
        if not self._sessions_dir.exists():
            return
        for path in self._sessions_dir.glob("session_*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                self._sessions[data["session_id"]] = data
            except (json.JSONDecodeError, KeyError):
                continue
