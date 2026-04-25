"""Staff profile service."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import StaffProfile
from app.repositories.factory import RepositoryFactory
from app.schemas.staff import StaffProfileCreate, StaffProfileUpdate


class StaffService:
    def __init__(self, session: AsyncSession) -> None:
        self._repos = RepositoryFactory(session)

    async def create_profile(self, data: StaffProfileCreate) -> StaffProfile:
        """Create a staff profile. Raises 409 if profile already exists for user."""
        existing = await self._repos.staff.get_by_user_id(data.user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Staff profile already exists for this user",
            )
        profile = StaffProfile(**data.model_dump())
        return await self._repos.staff.create(profile)

    async def get_profile(self, profile_id: UUID) -> StaffProfile:
        profile = await self._repos.staff.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff profile not found",
            )
        return profile

    async def get_by_user_id(self, user_id: UUID) -> StaffProfile:
        profile = await self._repos.staff.get_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff profile not found",
            )
        return profile

    async def update_profile(
        self, profile_id: UUID, data: StaffProfileUpdate
    ) -> StaffProfile:
        profile = await self.get_profile(profile_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        return await self._repos.staff.update(profile)

    async def delete_profile(self, profile_id: UUID) -> None:
        await self.get_profile(profile_id)
        await self._repos.staff.soft_delete(profile_id)
