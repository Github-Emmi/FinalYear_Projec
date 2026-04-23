"""Academic entity service: Department, SessionYear, ClassRoom, Subject.

Thin CRUD wrapper over repositories — raises HTTP 404 for missing objects.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import ClassRoom, Department, SessionYear, Subject
from app.repositories.factory import RepositoryFactory
from app.schemas.academic import (
    ClassRoomCreate,
    ClassRoomUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    SessionYearCreate,
    SessionYearUpdate,
    SubjectCreate,
    SubjectUpdate,
)


class AcademicService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = RepositoryFactory(session)

    # ── Department ─────────────────────────────────────────────────────────────

    async def create_department(self, data: DepartmentCreate):
        return await self._repo.departments.create(Department(**data.model_dump()))

    async def get_department(self, dept_id: UUID):
        obj = await self._repo.departments.get_by_id(dept_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        return obj

    async def list_departments(self, skip: int = 0, limit: int = 100):
        return await self._repo.departments.get_all(skip=skip, limit=limit)

    async def update_department(self, dept_id: UUID, data: DepartmentUpdate):
        obj = await self.get_department(dept_id)
        return await self._repo.departments.update(obj, data.model_dump(exclude_none=True))

    async def delete_department(self, dept_id: UUID) -> None:
        obj = await self.get_department(dept_id)
        await self._repo.departments.delete(obj)

    # ── SessionYear ────────────────────────────────────────────────────────────

    async def create_session_year(self, data: SessionYearCreate):
        return await self._repo.session_years.create(SessionYear(**data.model_dump()))

    async def get_session_year(self, year_id: UUID):
        obj = await self._repo.session_years.get_by_id(year_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SessionYear not found")
        return obj

    async def list_session_years(self, skip: int = 0, limit: int = 100):
        return await self._repo.session_years.get_all(skip=skip, limit=limit)

    async def update_session_year(self, year_id: UUID, data: SessionYearUpdate):
        obj = await self.get_session_year(year_id)
        return await self._repo.session_years.update(obj, data.model_dump(exclude_none=True))

    async def delete_session_year(self, year_id: UUID) -> None:
        obj = await self.get_session_year(year_id)
        await self._repo.session_years.delete(obj)

    # ── ClassRoom ──────────────────────────────────────────────────────────────

    async def create_classroom(self, data: ClassRoomCreate):
        return await self._repo.classrooms.create(ClassRoom(**data.model_dump()))

    async def get_classroom(self, room_id: UUID):
        obj = await self._repo.classrooms.get_by_id(room_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClassRoom not found")
        return obj

    async def list_classrooms(self, skip: int = 0, limit: int = 100):
        return await self._repo.classrooms.get_all(skip=skip, limit=limit)

    async def update_classroom(self, room_id: UUID, data: ClassRoomUpdate):
        obj = await self.get_classroom(room_id)
        return await self._repo.classrooms.update(obj, data.model_dump(exclude_none=True))

    async def delete_classroom(self, room_id: UUID) -> None:
        obj = await self.get_classroom(room_id)
        await self._repo.classrooms.delete(obj)

    # ── Subject ────────────────────────────────────────────────────────────────

    async def create_subject(self, data: SubjectCreate):
        return await self._repo.subjects.create(Subject(**data.model_dump()))

    async def get_subject(self, subject_id: UUID):
        obj = await self._repo.subjects.get_by_id(subject_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
        return obj

    async def list_subjects(self, skip: int = 0, limit: int = 100):
        return await self._repo.subjects.get_all(skip=skip, limit=limit)

    async def update_subject(self, subject_id: UUID, data: SubjectUpdate):
        obj = await self.get_subject(subject_id)
        return await self._repo.subjects.update(obj, data.model_dump(exclude_none=True))

    async def delete_subject(self, subject_id: UUID) -> None:
        obj = await self.get_subject(subject_id)
        await self._repo.subjects.delete(obj)
