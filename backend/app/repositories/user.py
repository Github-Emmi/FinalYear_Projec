"""UserRepository — extends BaseRepository with email/username lookups."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email, User.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(
                User.username == username, User.is_deleted.is_(False)
            )
        )
        return result.scalar_one_or_none()

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        result = await self.session.execute(
            select(User)
            .where(User.is_deleted.is_(False), User.is_active.is_(True))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def _base_filter_query(self, role: Optional[str] = None, search: Optional[str] = None):
        q = select(User).where(User.is_deleted.is_(False))
        if role:
            q = q.where(User.role == role)
        if search:
            term = f"%{search}%"
            q = q.where(
                or_(
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.username.ilike(term),
                    User.email.ilike(term),
                )
            )
        return q

    async def get_filtered(
        self,
        role: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[User]:
        q = self._base_filter_query(role, search).offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        role: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        q = select(func.count()).select_from(
            self._base_filter_query(role, search).subquery()
        )
        result = await self.session.execute(q)
        return result.scalar_one()
