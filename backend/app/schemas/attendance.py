"""Attendance schemas."""

from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.attendance import AttendanceStatus
from app.schemas.base import BaseResponse


# ── AttendanceSession ──────────────────────────────────────────────────────────

class AttendanceSessionCreate(BaseModel):
    classroom_id: UUID
    subject_id: UUID
    staff_id: UUID
    date: date


class AttendanceSessionUpdate(BaseModel):
    date: Optional[date] = None


class AttendanceSessionResponse(BaseResponse):
    classroom_id: UUID
    subject_id: UUID
    staff_id: UUID
    date: date


# ── AttendanceRecord ───────────────────────────────────────────────────────────

class AttendanceRecordCreate(BaseModel):
    session_id: UUID
    student_id: UUID
    status: AttendanceStatus = AttendanceStatus.present
    remarks: Optional[str] = None


class AttendanceRecordUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    remarks: Optional[str] = None


class AttendanceRecordResponse(BaseResponse):
    session_id: UUID
    student_id: UUID
    status: str
    remarks: Optional[str] = None
