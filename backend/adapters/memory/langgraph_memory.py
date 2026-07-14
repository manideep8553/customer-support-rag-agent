import json
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from backend.cache import WriteCoalescer
from backend.config import settings
from backend.ports.memory import Memory, MessageEntry, SessionInfo


class LangGraphMemory(Memory):
    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: dict[str, dict] = {}
        self._sessions_dir: Path = settings.vector_store_path / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._max_turns = settings.memory_max_turns
        self._timeout_minutes = settings.session_timeout_minutes
        self._max_sessions = 1000
        self._checkpointer = None
        self._coalescer = WriteCoalescer(flush_interval=2.0, batch_threshold=10)
        self._coalescer.set_save_fn(self._save_session)
        self._load_sessions()

    @property
    def checkpointer(self):
        return self._checkpointer

    def _is_expired(self, session: dict) -> bool:
        if self._timeout_minutes <= 0:
            return False
        last_active = datetime.fromisoformat(session["last_active"])
        return datetime.utcnow() - last_active > timedelta(minutes=self._timeout_minutes)

    def _ensure_active(self, session_id: str) -> Optional[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        if self._is_expired(session):
            self.delete_session(session_id)
            return None
        return session

    def create_session(self, session_id: Optional[str] = None) -> str:
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()
        with self._lock:
            if session_id in self._sessions:
                return session_id
            if len(self._sessions) >= self._max_sessions:
                self._evict_oldest()
            self._sessions[session_id] = {
                "session_id": session_id,
                "created_at": now,
                "last_active": now,
                "messages": [],
                "state": {},
                "summary": "",
            }
            self._coalescer.mark_dirty(session_id)
        return session_id

    def _evict_oldest(self):
        oldest = min(
            self._sessions.items(),
            key=lambda kv: kv[1].get("last_active", kv[1]["created_at"]),
        )
        self.delete_session(oldest[0])

    def add_turn(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            session = self._ensure_active(session_id)
            if not session:
                if session_id not in self._sessions:
                    if len(self._sessions) >= self._max_sessions:
                        self._evict_oldest()
                    self._sessions[session_id] = {
                        "session_id": session_id,
                        "created_at": datetime.utcnow().isoformat(),
                        "last_active": datetime.utcnow().isoformat(),
                        "messages": [],
                        "state": {},
                        "summary": "",
                    }
                session = self._sessions[session_id]
            entry = MessageEntry(role=role, content=content)
            session["messages"].append(entry.to_dict())
            session["last_active"] = datetime.utcnow().isoformat()
            max_messages = self._max_turns * 2
            if len(session["messages"]) > max_messages:
                session["messages"] = session["messages"][-max_messages:]
            self._coalescer.mark_dirty(session_id)

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
            session = self._ensure_active(session_id)
            if not session:
                return
            session["summary"] = summary
            self._coalescer.mark_dirty(session_id)

    def get_summary(self, session_id: str) -> str:
        with self._lock:
            session = self._ensure_active(session_id)
            if not session:
                return ""
            return session.get("summary", "")

    def get_messages(self, session_id: str) -> list[dict]:
        with self._lock:
            session = self._ensure_active(session_id)
            if not session:
                return []
            return list(session["messages"])

    def get_state(self, session_id: str) -> dict:
        with self._lock:
            session = self._ensure_active(session_id)
            if not session:
                return {}
            return dict(session.get("state", {}))

    def update_state(self, session_id: str, state: dict) -> None:
        with self._lock:
            session = self._ensure_active(session_id)
            if not session:
                return
            session["state"].update(state)
            self._coalescer.mark_dirty(session_id)

    def list_sessions(self) -> list[str]:
        with self._lock:
            self._purge_expired()
            return list(self._sessions.keys())

    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        with self._lock:
            session = self._ensure_active(session_id)
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

    def clear_history(self, session_id: str) -> bool:
        with self._lock:
            session = self._ensure_active(session_id)
            if not session:
                return False
            session["messages"] = []
            session["summary"] = ""
            session["last_active"] = datetime.utcnow().isoformat()
            self._coalescer.mark_dirty(session_id)
            return True

    def cleanup_expired(self) -> int:
        with self._lock:
            count = 0
            expired = [
                sid for sid, s in self._sessions.items()
                if self._is_expired(s)
            ]
            for sid in expired:
                self.delete_session(sid)
                count += 1
            return count

    def _purge_expired(self):
        expired = [sid for sid, s in self._sessions.items() if self._is_expired(s)]
        for sid in expired:
            del self._sessions[sid]
            path = self._sessions_dir / f"{sid}.json"
            if path.exists():
                path.unlink()

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
