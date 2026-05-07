"""StaffRepository."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.staff import StaffProfile
from app.repositories.base import BaseRepository


class StaffRepository(BaseRepository[StaffProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(StaffProfile, session)

    async def _fetch_with_relations(self, staff_id: UUID) -> Optional[StaffProfile]:
        """Fetch a single staff profile with user and department eagerly loaded."""
        result = await self.session.execute(
            select(StaffProfile)
            .where(StaffProfile.id == staff_id, StaffProfile.is_deleted.is_(False))
            .options(
                selectinload(StaffProfile.user),
                selectinload(StaffProfile.department),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, id: UUID) -> Optional[StaffProfile]:  # type: ignore[override]
        """Return staff profile by id with relationships eagerly loaded."""
        return await self._fetch_with_relations(id)

    async def update(self, obj: StaffProfile) -> StaffProfile:  # type: ignore[override]
        """Commit changes then re-fetch with relationships so ORM objects are accessible."""
        self.session.add(obj)
        await self.session.commit()
        return await self._fetch_with_relations(obj.id)  # type: ignore[return-value]

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[StaffProfile]:
        """Return paginated staff profiles with user and department loaded."""
        result = await self.session.execute(
            select(StaffProfile)
            .where(StaffProfile.is_deleted.is_(False))
            .options(
                selectinload(StaffProfile.user),
                selectinload(StaffProfile.department),
            )
            .offset(skip)
            .limit(limit)
            .order_by(StaffProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_id(self, user_id: UUID) -> Optional[StaffProfile]:
        result = await self.session.execute(
            select(StaffProfile)
            .where(
                StaffProfile.user_id == user_id,
                StaffProfile.is_deleted.is_(False),
            )
            .options(
                selectinload(StaffProfile.user),
                selectinload(StaffProfile.department),
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
