from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])

async def _authenticate(token: str) -> str | None:
    if not token:
        return None
    try:
        from app.services.auth.security import decode_token
        payload = decode_token(token)
        if not payload:
            return None
        user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
        return str(user_id) if user_id else None
    except Exception as exc:
        logger.debug("WS token validation failed: %s", exc)
        return None

def _close_msg(code: int, reason: str) -> str:
    return json.dumps({"type": "error", "code": code, "reason": reason})

@router.websocket("/jobs/{user_id}")
async def ws_jobs(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(default=""),
):
    caller_id = await _authenticate(token) if token else None
    
    if caller_id is None:
        await websocket.accept()
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            msg = json.loads(raw)
            if msg.get("type") == "auth" and msg.get("token"):
                caller_id = await _authenticate(msg["token"])
        except (asyncio.TimeoutError, json.JSONDecodeError, WebSocketDisconnect):
            return
        except Exception:
            pass
        
        if caller_id is None:
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_text(_close_msg(4001, "Unauthorized: invalid or missing token"))
                    await websocket.close(code=4001)
                except Exception:
                    pass
            return
        
        if caller_id != user_id:
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_text(_close_msg(4003, "Forbidden: token user_id mismatch"))
                    await websocket.close(code=4003)
                except Exception:
                    pass
            return
    else:
        if caller_id != user_id:
            await websocket.accept()
            await websocket.send_text(_close_msg(4003, "Forbidden: token user_id mismatch"))
            await websocket.close(code=4003)
            return

    if websocket.client_state != WebSocketState.CONNECTED:
        await ws_manager.connect_user(user_id, websocket)
    else:
        ws_manager._user_connections.setdefault(user_id, []).append(websocket)
    logger.info("WS /ws/jobs/%s connected", user_id)

    await websocket.send_text(json.dumps({
        "type": "connected",
        "channel": "jobs",
        "user_id": user_id,
    }))

    try:
        _PING_INTERVAL = 30
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=_PING_INTERVAL,
                )
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except asyncio.TimeoutError:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                else:
                    break

    except WebSocketDisconnect:
        logger.info("WS /ws/jobs/%s disconnected", user_id)
    except Exception as exc:
        logger.warning("WS /ws/jobs/%s error: %s", user_id, exc)
    finally:
        ws_manager.disconnect_user(user_id, websocket)

