"""StudentRepository."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.student import StudentProfile
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[StudentProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(StudentProfile, session)

    async def _fetch_with_relations(self, student_id: UUID) -> Optional[StudentProfile]:
        """Re-fetch a student profile with all relationships loaded."""
        result = await self.session.execute(
            select(StudentProfile)
            .where(StudentProfile.id == student_id, StudentProfile.is_deleted.is_(False))
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.classroom),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, id: UUID) -> Optional[StudentProfile]:  # type: ignore[override]
        return await self._fetch_with_relations(id)

    async def create(self, obj: StudentProfile) -> StudentProfile:  # type: ignore[override]
        self.session.add(obj)
        await self.session.commit()
        return await self._fetch_with_relations(obj.id)  # type: ignore[return-value]

    async def update(self, obj: StudentProfile) -> StudentProfile:  # type: ignore[override]
        self.session.add(obj)
        await self.session.commit()
        return await self._fetch_with_relations(obj.id)  # type: ignore[return-value]

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[StudentProfile]:
        """Return paginated student profiles with user and classroom loaded."""
        result = await self.session.execute(
            select(StudentProfile)
            .where(StudentProfile.is_deleted.is_(False))
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.classroom),
            )
            .offset(skip)
            .limit(limit)
            .order_by(StudentProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_id(self, user_id: UUID) -> Optional[StudentProfile]:
        result = await self.session.execute(
            select(StudentProfile)
            .where(
                StudentProfile.user_id == user_id,
                StudentProfile.is_deleted.is_(False),
            )
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.classroom),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_classroom(
        self, classroom_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[StudentProfile]:
        result = await self.session.execute(
            select(StudentProfile)
            .where(
                StudentProfile.classroom_id == classroom_id,
                StudentProfile.is_deleted.is_(False),
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
