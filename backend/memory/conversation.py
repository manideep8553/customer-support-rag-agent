import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from backend.config import settings


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConversationMemory:
    def __init__(self):
        self._sessions: dict[str, list[dict]] = {}
        self._session_meta: dict[str, dict] = {}
        self._lock = Lock()
        self._store_path = settings.vector_store_path / "sessions"
        self._store_path.mkdir(parents=True, exist_ok=True)
        self._load_sessions()

    def _session_file(self, session_id: str) -> Path:
        return self._store_path / f"{session_id}.json"

    def _load_sessions(self):
        if not self._store_path.exists():
            return
        for f in self._store_path.iterdir():
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    session_id = f.stem
                    self._sessions[session_id] = data.get("messages", [])
                    self._session_meta[session_id] = {
                        "created_at": datetime.fromisoformat(data.get("created_at", _now().isoformat())),
                        "last_active": datetime.fromisoformat(data.get("last_active", _now().isoformat())),
                    }
                except (json.JSONDecodeError, KeyError):
                    continue

    def _save_session(self, session_id: str):
        data = {
            "session_id": session_id,
            "created_at": self._session_meta.get(session_id, {}).get("created_at", _now()).isoformat(),
            "last_active": self._session_meta.get(session_id, {}).get("last_active", _now()).isoformat(),
            "messages": self._sessions.get(session_id, []),
        }
        self._session_file(session_id).write_text(json.dumps(data, indent=2))

    def create_session(self, session_id: Optional[str] = None) -> str:
        with self._lock:
            sid = session_id or f"session_{uuid.uuid4().hex[:12]}"
            if sid not in self._sessions:
                self._sessions[sid] = []
                now = _now()
                self._session_meta[sid] = {
                    "created_at": now,
                    "last_active": now,
                }
                self._save_session(sid)
            return sid

    def add_turn(self, session_id: str, role: str, content: str):
        with self._lock:
            if session_id not in self._sessions:
                self.create_session(session_id)

            entry = {
                "role": role,
                "content": content,
                "timestamp": _now().isoformat(),
            }
            self._sessions[session_id].append(entry)
            self._session_meta[session_id]["last_active"] = _now()
            self._prune_if_needed(session_id)
            self._save_session(session_id)

    def _prune_if_needed(self, session_id: str):
        max_turns = settings.memory_max_turns * 2
        if len(self._sessions[session_id]) > max_turns:
            n_remove = len(self._sessions[session_id]) - max_turns
            self._sessions[session_id] = self._sessions[session_id][n_remove:]

    def get_history(self, session_id: str, limit: int = 10) -> str:
        if session_id not in self._sessions:
            return ""

        messages = self._sessions[session_id][-limit:]
        formatted = []
        for msg in messages:
            role = "Customer" if msg["role"] == "user" else "GigaBot (Support Agent)"
            formatted.append(f"{role}: {msg['content']}")

        return "\n".join(formatted)

    def get_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        if session_id not in self._sessions:
            return []
        return self._sessions[session_id][-limit:]

    def list_sessions(self) -> list[dict]:
        sessions = []
        for sid in self._sessions:
            meta = self._session_meta.get(sid, {})
            sessions.append({
                "session_id": sid,
                "message_count": len(self._sessions[sid]),
                "created_at": meta.get("created_at", _now()),
                "last_active": meta.get("last_active", _now()),
            })
        return sorted(sessions, key=lambda s: s["last_active"], reverse=True)

    def get_session_info(self, session_id: str) -> Optional[dict]:
        if session_id not in self._sessions:
            return None
        meta = self._session_meta.get(session_id, {})
        return {
            "session_id": session_id,
            "message_count": len(self._sessions[session_id]),
            "created_at": meta.get("created_at", _now()),
            "last_active": meta.get("last_active", _now()),
        }

    def delete_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)
            self._session_meta.pop(session_id, None)
            path = self._session_file(session_id)
            if path.exists():
                path.unlink()

    def cleanup_stale_sessions(self):
        cutoff = _now() - timedelta(minutes=settings.session_timeout_minutes)
        stale = [
            sid for sid, meta in self._session_meta.items()
            if meta.get("last_active", _now()) < cutoff
        ]
        for sid in stale:
            self.delete_session(sid)
