"""Feedback repositories."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import FeedbackStaff, FeedbackStudent
from app.repositories.base import BaseRepository


class FeedbackStaffRepository(BaseRepository[FeedbackStaff]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FeedbackStaff, session)


class FeedbackStudentRepository(BaseRepository[FeedbackStudent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FeedbackStudent, session)
