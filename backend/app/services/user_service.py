"""User CRUD service."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.factory import RepositoryFactory
from app.schemas.auth import PasswordChangeRequest
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._repos = RepositoryFactory(session)

    async def create(self, data: UserCreate) -> User:
        """Create a new user. Raises 409 if username or email is taken."""
        if await self._repos.users.get_by_username(data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already taken",
            )
        if await self._repos.users.get_by_email(str(data.email)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address is already registered",
            )

        user = User(
            username=data.username,
            email=str(data.email),
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            role=data.role if isinstance(data.role, str) else data.role.value,
            is_active=True,
        )
        return await self._repos.users.create(user)

    async def get_by_id(self, user_id: UUID) -> User:
        user = await self._repos.users.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def get_all(self, skip: int = 0, limit: int = 50) -> List[User]:
        return await self._repos.users.get_all(skip=skip, limit=limit)

    async def update(self, user_id: UUID, data: UserUpdate) -> User:
        user = await self.get_by_id(user_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        return await self._repos.users.update(user)

    async def soft_delete(self, user_id: UUID) -> None:
        await self.get_by_id(user_id)
        await self._repos.users.soft_delete(user_id)

    async def change_password(
        self, user_id: UUID, data: PasswordChangeRequest
    ) -> None:
        user = await self.get_by_id(user_id)
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        user.password_hash = hash_password(data.new_password)
        await self._repos.users.update(user)

    async def set_active(self, user_id: UUID, *, active: bool) -> User:
        """Enable or disable a user account (admin action)."""
        user = await self.get_by_id(user_id)
        user.is_active = active
        return await self._repos.users.update(user)
