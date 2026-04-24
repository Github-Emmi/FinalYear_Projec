"""Celery task for pushing notifications via WebSocket.

Important: WebSocket connections live in the FastAPI process. This task runs in a
Celery worker process and therefore cannot see in-memory connections in
`app.websockets.manager` unless the worker shares the same process (dev-only).
"""

from __future__ import annotations

import asyncio

from app.tasks.celery_app import celery_app
from app.websockets.manager import manager


@celery_app.task(name="app.tasks.notification_tasks.push_ws_notification_task")
def push_ws_notification_task(user_id: str, title: str, message: str) -> None:
    async def _push() -> None:
        await manager.send_to_user(
            user_id,
            {"type": "notification", "title": title, "message": message},
        )

    asyncio.run(_push())
