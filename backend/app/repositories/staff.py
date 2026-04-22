"""StaffRepository."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import StaffProfile
from app.repositories.base import BaseRepository


class StaffRepository(BaseRepository[StaffProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(StaffProfile, session)

    async def get_by_user_id(self, user_id: UUID) -> Optional[StaffProfile]:
        result = await self.session.execute(
            select(StaffProfile).where(
                StaffProfile.user_id == user_id,
                StaffProfile.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_department(
        self, department_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[StaffProfile]:
        result = await self.session.execute(
            select(StaffProfile)
            .where(
                StaffProfile.department_id == department_id,
                StaffProfile.is_deleted.is_(False),
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
