"""Student profile service."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import StudentProfile
from app.repositories.factory import RepositoryFactory
from app.schemas.student import StudentProfileCreate, StudentProfileUpdate


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self._repos = RepositoryFactory(session)

    async def create_profile(self, data: StudentProfileCreate) -> StudentProfile:
        """Create a student profile. Raises 409 if profile already exists for user."""
        existing = await self._repos.students.get_by_user_id(data.user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Student profile already exists for this user",
            )
        profile = StudentProfile(**data.model_dump())
        return await self._repos.students.create(profile)

    async def get_profile(self, profile_id: UUID) -> StudentProfile:
        profile = await self._repos.students.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found",
            )
        return profile

    async def get_by_user_id(self, user_id: UUID) -> StudentProfile:
        profile = await self._repos.students.get_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found",
            )
        return profile

    async def update_profile(
        self, profile_id: UUID, data: StudentProfileUpdate
    ) -> StudentProfile:
        profile = await self.get_profile(profile_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        return await self._repos.students.update(profile)

    async def delete_profile(self, profile_id: UUID) -> None:
        await self.get_profile(profile_id)
        await self._repos.students.soft_delete(profile_id)
