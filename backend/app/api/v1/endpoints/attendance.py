"""Attendance session and record endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticatedUser, StaffOrAdmin
from app.core.database import get_db
from app.schemas.attendance import AttendanceRecordCreate, AttendanceSessionCreate, AttendanceSessionResponse
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/sessions", response_model=AttendanceSessionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(StaffOrAdmin)])
async def create_attendance_session(body: AttendanceSessionCreate, db: AsyncSession = Depends(get_db)) -> AttendanceSessionResponse:
    svc = AttendanceService(db)
    session = await svc.create_session(body)
    return AttendanceSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/mark", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(StaffOrAdmin)])
async def mark_attendance(
    session_id: UUID,
    records: list[AttendanceRecordCreate],
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = AttendanceService(db)
    records_dicts = [r.model_dump() for r in records]
    await svc.mark_attendance(session_id, records_dicts)


@router.get("/students/{student_id}/summary", dependencies=[Depends(AnyAuthenticatedUser)])
async def get_attendance_summary(student_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    svc = AttendanceService(db)
    return await svc.get_student_attendance_summary(student_id)
