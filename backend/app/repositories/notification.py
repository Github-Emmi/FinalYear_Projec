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

    async def get_for_user_paginated(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        is_read: bool | None = None,
    ) -> tuple[List[Notification], int]:
        from sqlalchemy import func
        base = (
            select(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.is_deleted.is_(False),
            )
        )
        count_q = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.is_deleted.is_(False),
            )
        )
        if is_read is not None:
            base = base.where(Notification.is_read.is_(is_read))
            count_q = count_q.where(Notification.is_read.is_(is_read))
        total = (await self.session.execute(count_q)).scalar_one()
        items = list(
            (
                await self.session.execute(
                    base.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
                )
            ).scalars().all()
        )
        return items, total

    async def mark_all_read_for_user(self, user_id: UUID) -> int:
        from sqlalchemy import update
        from datetime import datetime
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.is_read.is_(False),
                Notification.is_deleted.is_(False),
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount
