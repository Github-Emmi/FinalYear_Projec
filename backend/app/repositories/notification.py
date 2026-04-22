"""Notification repository."""

from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Notification, session)

    async def get_unread_for_user(self, user_id: UUID) -> List[Notification]:
        result = await self.session.execute(
            select(Notification).where(
                Notification.recipient_id == user_id,
                Notification.is_read.is_(False),
                Notification.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())
