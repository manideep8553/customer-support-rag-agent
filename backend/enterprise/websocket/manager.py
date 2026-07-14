import json
import logging
import asyncio
from typing import Optional
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

from backend.config import settings

logger = logging.getLogger("gigacorp.websocket")


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._user_sessions: dict[str, set[str]] = defaultdict(set)

    async def connect(self, ws: WebSocket, user_id: str, session_id: str):
        await ws.accept()
        self._connections[user_id].add(ws)
        self._user_sessions[user_id].add(session_id)
        logger.debug("WebSocket connected: user=%s session=%s", user_id, session_id)

    def disconnect(self, ws: WebSocket, user_id: str, session_id: str):
        self._connections[user_id].discard(ws)
        self._user_sessions[user_id].discard(session_id)
        if not self._connections[user_id]:
            del self._connections[user_id]
        if not self._user_sessions[user_id]:
            del self._user_sessions[user_id]
        logger.debug("WebSocket disconnected: user=%s session=%s", user_id, session_id)

    async def send_to_user(self, user_id: str, event_type: str, data: dict):
        message = json.dumps({"type": event_type, "data": data, "timestamp": __import__("datetime").datetime.utcnow().isoformat()})
        connections = self._connections.get(user_id, set()).copy()
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning("Failed to send WS message to user %s: %s", user_id, e)
                self._connections[user_id].discard(ws)

    async def broadcast(self, event_type: str, data: dict, exclude_user: Optional[str] = None):
        message = json.dumps({"type": event_type, "data": data})
        for user_id, connections in list(self._connections.items()):
            if user_id == exclude_user:
                continue
            for ws in connections.copy():
                try:
                    await ws.send_text(message)
                except Exception:
                    self._connections[user_id].discard(ws)

    def get_connected_users(self) -> list[str]:
        return list(self._connections.keys())

    def is_user_connected(self, user_id: str) -> bool:
        return user_id in self._connections and bool(self._connections[user_id])


class WebSocketManager:
    def __init__(self):
        self._conn_manager = ConnectionManager()
        self._chat_connections: dict[str, set[WebSocket]] = defaultdict(set)

    def get_connection_manager(self) -> ConnectionManager:
        return self._conn_manager

    async def handle_chat_ws(self, ws: WebSocket, session_id: str, user_id: Optional[str] = None):
        await ws.accept()
        conn_key = session_id
        self._chat_connections[conn_key].add(ws)
        logger.debug("Chat WebSocket connected: session=%s user=%s", session_id, user_id or "anonymous")

        try:
            async for message in ws.iter_text():
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "")
                    if msg_type == "ping":
                        await ws.send_text(json.dumps({"type": "pong"}))
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning("Chat WebSocket error: %s", e)
        finally:
            self._chat_connections[conn_key].discard(ws)
            if not self._chat_connections[conn_key]:
                del self._chat_connections[conn_key]

    async def send_to_user(self, user_id: str, event_type: str, data: dict):
        await self._conn_manager.send_to_user(user_id, event_type, data)

    async def broadcast_to_chat(self, session_id: str, data: dict):
        message = json.dumps(data)
        for ws in self._chat_connections.get(session_id, set()).copy():
            try:
                await ws.send_text(message)
            except Exception:
                self._chat_connections[session_id].discard(ws)

    async def send_chat_token(self, session_id: str, token: str):
        await self.broadcast_to_chat(session_id, {"type": "token", "content": token})

    async def send_chat_sources(self, session_id: str, sources: list):
        await self.broadcast_to_chat(session_id, {"type": "sources", "sources": sources})

    async def send_chat_done(self, session_id: str):
        await self.broadcast_to_chat(session_id, {"type": "done"})


_ws_manager: Optional[WebSocketManager] = None


async def get_ws_manager() -> WebSocketManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
