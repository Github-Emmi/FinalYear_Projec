"""Academic repositories: Department, SessionYear, ClassRoom, Subject."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import ClassRoom, Department, SessionYear, Subject
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
