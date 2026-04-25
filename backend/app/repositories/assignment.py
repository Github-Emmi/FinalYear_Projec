"""Assignment repositories."""

from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment, AssignmentSubmission
from app.repositories.base import BaseRepository


class AssignmentRepository(BaseRepository[Assignment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Assignment, session)

    async def get_by_subject(self, subject_id: UUID) -> List[Assignment]:
        result = await self.session.execute(
            select(Assignment).where(
                Assignment.subject_id == subject_id,
                Assignment.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())


class SubmissionRepository(BaseRepository[AssignmentSubmission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AssignmentSubmission, session)

    async def get_by_assignment(
        self, assignment_id: UUID
    ) -> List[AssignmentSubmission]:
        result = await self.session.execute(
            select(AssignmentSubmission).where(
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())
