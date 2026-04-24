"""Celery task for sending emails asynchronously."""

from __future__ import annotations

import asyncio

from app.services.email_service import EmailService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.email_tasks.send_email_task")
def send_email_task(to: str, subject: str, body: str) -> None:
    async def _send() -> None:
        await EmailService().send_email(to, subject, body)

    asyncio.run(_send())
