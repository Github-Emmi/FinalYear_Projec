"""Leave request repository."""

from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leave import LeaveRequest, LeaveStatus
from app.repositories.base import BaseRepository


class LeaveRepository(BaseRepository[LeaveRequest]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(LeaveRequest, session)

    async def get_pending(self) -> List[LeaveRequest]:
        result = await self.session.execute(
            select(LeaveRequest).where(
                LeaveRequest.status == LeaveStatus.pending.value,
                LeaveRequest.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def get_by_user(self, user_id: UUID) -> List[LeaveRequest]:
        result = await self.session.execute(
            select(LeaveRequest).where(
                LeaveRequest.user_id == user_id,
                LeaveRequest.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())
