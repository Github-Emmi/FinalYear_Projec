"""Academic repositories: Department, SessionYear, ClassRoom, Subject."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from typing import List

from sqlalchemy.orm import selectinload

from app.models.academic import ClassRoom, Department, SessionYear, Subject
from app.models.staff import StaffProfile
from app.models.user import User
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Department, session)

    async def get_by_name(self, name: str) -> Optional[Department]:
        result = await self.session.execute(
            select(Department).where(
                Department.name == name, Department.is_deleted.is_(False)
            )
        )
        return result.scalar_one_or_none()


class SessionYearRepository(BaseRepository[SessionYear]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SessionYear, session)

    async def get_current(self) -> Optional[SessionYear]:
        result = await self.session.execute(
            select(SessionYear).where(
                SessionYear.is_current.is_(True),
                SessionYear.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class ClassRoomRepository(BaseRepository[ClassRoom]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ClassRoom, session)


class SubjectRepository(BaseRepository[Subject]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Subject, session)

    async def _fetch_with_staff(self, subject_id) -> Optional[Subject]:
        from uuid import UUID
        result = await self.session.execute(
            select(Subject)
            .where(Subject.id == subject_id, Subject.is_deleted.is_(False))
            .options(
                selectinload(Subject.staff).selectinload(StaffProfile.user),
                selectinload(Subject.classroom),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, id) -> Optional[Subject]:  # type: ignore[override]
        return await self._fetch_with_staff(id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Subject]:  # type: ignore[override]
        result = await self.session.execute(
            select(Subject)
            .where(Subject.is_deleted.is_(False))
            .options(
                selectinload(Subject.staff).selectinload(StaffProfile.user),
                selectinload(Subject.classroom),
            )
            .offset(skip)
            .limit(limit)
            .order_by(Subject.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, obj: Subject) -> Subject:  # type: ignore[override]
        self.session.add(obj)
        await self.session.commit()
        return await self._fetch_with_staff(obj.id)  # type: ignore[return-value]
