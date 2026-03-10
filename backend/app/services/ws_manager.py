from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any, Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:

    MAX_CONNECTIONS_PER_USER = 10

    def __init__(self) -> None:
        self._user_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect_user(self, user_id: str, ws: WebSocket) -> None:
        current_count = len(self._user_connections.get(user_id, []))
        if current_count >= self.MAX_CONNECTIONS_PER_USER:
            await ws.accept()
            await ws.send_text('{"type":"error","reason":"Too many connections"}')
            await ws.close(code=4008)
            logger.warning(
                "WS rejected: user=%s exceeded max connections (%d)",
                user_id, self.MAX_CONNECTIONS_PER_USER,
            )
            return
        await ws.accept()
        self._user_connections[user_id].append(ws)
        logger.info(
            "WS connect: user=%s  total_user_conns=%d",
            user_id, len(self._user_connections[user_id]),
        )

    def disconnect_user(self, user_id: str, ws: WebSocket) -> None:
        conns = self._user_connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._user_connections.pop(user_id, None)
        logger.info(
            "WS disconnect: user=%s  remaining=%d",
            user_id, len(self._user_connections.get(user_id, [])),
        )

    async def send_to_user(self, user_id: str, payload: Dict[str, Any]) -> int:
        return await self._send_to_connections(
            self._user_connections.get(user_id, []),
            payload,
            prune_key=("user", user_id),
        )

    async def broadcast(self, payload: Dict[str, Any]) -> int:
        text = json.dumps(payload)
        total = 0
        for uid, conns in list(self._user_connections.items()):
            for ws in list(conns):
                try:
                    await ws.send_text(text)
                    total += 1
                except Exception:
                    self.disconnect_user(uid, ws)
        return total

    def user_is_connected(self, user_id: str) -> bool:
        return bool(self._user_connections.get(user_id))

    def stats(self) -> Dict[str, int]:
        return {
            "user_connections": sum(len(v) for v in self._user_connections.values()),
            "unique_users": len(self._user_connections),
        }

    async def _send_to_connections(
        self,
        conns: List[WebSocket],
        payload: Dict[str, Any],
        prune_key: tuple,
    ) -> int:
        if not conns:
            return 0

        text = json.dumps(payload)
        sent = 0
        dead: List[WebSocket] = []

        for ws in list(conns):
            try:
                await ws.send_text(text)
                sent += 1
            except Exception as exc:
                logger.debug(
                    "WS send failed (%s=%s): %s — pruning connection",
                    prune_key[0], prune_key[1], exc,
                )
                dead.append(ws)

        for ws in dead:
            scope, key = prune_key
            if scope == "user":
                self.disconnect_user(key, ws)

        return sent

ws_manager = ConnectionManager()
