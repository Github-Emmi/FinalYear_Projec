"""In-memory WebSocket connection manager for real-time notifications.

Note: This is process-local state. It works for single-process FastAPI dev.
In production with multiple API workers, use a shared transport (e.g. Redis
pub/sub) to fan-out notifications across processes.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    def _discard_connection(self, user_id: str, websocket: WebSocket) -> None:
        conns = self.active.get(user_id)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            self.active.pop(user_id, None)

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active.setdefault(user_id, set()).add(websocket)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._discard_connection(user_id, websocket)

    async def send_to_user(self, user_id: str, data: dict) -> None:
        async with self._lock:
            conns = list(self.active.get(user_id, set()))

        if not conns:
            return

        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                stale.append(ws)

        if not stale:
            return

        async with self._lock:
            for ws in stale:
                self._discard_connection(user_id, ws)

    async def broadcast(self, data: dict) -> None:
        async with self._lock:
            snapshot = [(uid, list(conns)) for uid, conns in self.active.items()]

        stale: list[tuple[str, WebSocket]] = []
        for user_id, conns in snapshot:
            for ws in conns:
                try:
                    await ws.send_json(data)
                except Exception:
                    stale.append((user_id, ws))

        if not stale:
            return

        async with self._lock:
            for user_id, ws in stale:
                self._discard_connection(user_id, ws)


manager = ConnectionManager()
