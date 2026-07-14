import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from backend.auth.utils import decode_token
from backend.enterprise.websocket.manager import get_ws_manager

logger = logging.getLogger("gigacorp.websocket.routes")


def build_ws_router() -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/chat/{session_id}")
    async def chat_websocket(ws: WebSocket, session_id: str, token: Optional[str] = None):
        user_id = None
        if token:
            try:
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
            except Exception:
                pass

        manager = await get_ws_manager()
        await manager.handle_chat_ws(ws, session_id, user_id)

    @router.websocket("/ws/notifications")
    async def notification_websocket(ws: WebSocket, token: str):
        payload = decode_token(token)
        if not payload:
            await ws.close(code=4001, reason="Invalid token")
            return

        user_id = payload.get("sub")
        if not user_id:
            await ws.close(code=4001, reason="Invalid token payload")
            return

        session_id = f"notify_{user_id}"
        manager = await get_ws_manager()
        conn_manager = manager.get_connection_manager()
        await conn_manager.connect(ws, user_id, session_id)

        try:
            async for message in ws.iter_text():
                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        await ws.send_text(json.dumps({"type": "pong"}))
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning("Notification WS error for user %s: %s", user_id, e)
        finally:
            conn_manager.disconnect(ws, user_id, session_id)

    return router
