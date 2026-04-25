"""Attendance service: session creation and bulk attendance marking."""

from __future__ import annotations

from datetime import date
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceRecord, AttendanceSession, AttendanceStatus
from app.repositories.factory import RepositoryFactory
from app.schemas.attendance import AttendanceSessionCreate


class AttendanceService:
    def __init__(self, session: AsyncSession) -> None:
        self._repos = RepositoryFactory(session)

    async def create_session(self, data: AttendanceSessionCreate) -> AttendanceSession:
        """Open a new attendance session for a classroom."""
        obj = AttendanceSession(**data.model_dump())
        return await self._repos.attendance_sessions.create(obj)

    async def mark_attendance(
        self,
        session_id: UUID,
        records: List[dict],
    ) -> List[AttendanceRecord]:
        """Bulk-create attendance records.

        *records* is a list of ``{"student_id": UUID, "status": str, "remarks": str|None}``.
        """
        session_obj = await self._repos.attendance_sessions.get_by_id(session_id)
        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attendance session not found",
            )

        created: List[AttendanceRecord] = []
        for rec in records:
            record = AttendanceRecord(
                session_id=session_id,
                student_id=rec["student_id"],
                status=rec.get("status", AttendanceStatus.present.value),
                remarks=rec.get("remarks"),
            )
            created.append(await self._repos.attendance_records.create(record))

        return created

    async def get_student_attendance_summary(self, student_id: UUID) -> dict:
        """Return attendance counts per status for a student."""
        all_records = await self._repos.attendance_records.get_all(limit=10000)
        student_records = [r for r in all_records if r.student_id == student_id]

        summary: dict[str, int] = {s.value: 0 for s in AttendanceStatus}
        for record in student_records:
            summary[record.status] = summary.get(record.status, 0) + 1

        total = len(student_records)
        present = summary.get(AttendanceStatus.present.value, 0)
        return {
            "total": total,
            "present": present,
            "absent": summary.get(AttendanceStatus.absent.value, 0),
            "late": summary.get(AttendanceStatus.late.value, 0),
            "excused": summary.get(AttendanceStatus.excused.value, 0),
            "attendance_pct": round(present / total * 100, 1) if total else 0.0,
        }
