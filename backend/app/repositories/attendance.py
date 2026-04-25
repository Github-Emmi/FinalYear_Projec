"""Attendance repositories."""

from __future__ import annotations

from datetime import date
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceRecord, AttendanceSession
from app.repositories.base import BaseRepository


class AttendanceSessionRepository(BaseRepository[AttendanceSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AttendanceSession, session)

    async def get_by_classroom_and_date(
        self, classroom_id: UUID, session_date: date
    ) -> List[AttendanceSession]:
        result = await self.session.execute(
            select(AttendanceSession).where(
                AttendanceSession.classroom_id == classroom_id,
                AttendanceSession.date == session_date,
                AttendanceSession.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())


class AttendanceRecordRepository(BaseRepository[AttendanceRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AttendanceRecord, session)

    async def get_by_session(self, session_id: UUID) -> List[AttendanceRecord]:
        result = await self.session.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())
