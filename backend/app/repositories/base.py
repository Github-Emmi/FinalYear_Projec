"""Generic async CRUD base repository."""

from __future__ import annotations

from typing import Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """
    Generic async CRUD base for all repositories.

    Usage::

        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession) -> None:
                super().__init__(User, session)
    """

    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[ModelT]:
        """Return a single non-deleted record by primary key, or None."""
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == id,
                self.model.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelT]:
        """Return a paginated list of non-deleted records."""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.is_deleted.is_(False))
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, obj: ModelT) -> ModelT:
        """Persist a new record and return the refreshed instance."""
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: ModelT) -> ModelT:
        """Persist changes to an existing record and return the refreshed instance."""
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, id: UUID) -> bool:
        """Set is_deleted=True. Returns False if the record does not exist."""
        obj = await self.get_by_id(id)
        if obj is None:
            return False
        obj.is_deleted = True  # type: ignore[attr-defined]
        await self.session.commit()
        return True

    async def count(self) -> int:
        """Count non-deleted records."""
        result = await self.session.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.is_deleted.is_(False))
        )
        return result.scalar_one()

    async def exists(self, id: UUID) -> bool:
        """Return True if a non-deleted record with this id exists."""
        return await self.get_by_id(id) is not None
