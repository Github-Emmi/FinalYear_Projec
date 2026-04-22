"""Attendance models: AttendanceSession, AttendanceRecord."""

from __future__ import annotations

import enum

from sqlalchemy import Column, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"
    excused = "excused"


class AttendanceSession(BaseModel):
    __tablename__ = "attendance_sessions"

    classroom_id = Column(
        UUID(as_uuid=True), ForeignKey("classrooms.id"), nullable=False
    )
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    staff_id = Column(
        UUID(as_uuid=True), ForeignKey("staff_profiles.id"), nullable=False
    )
    date = Column(Date, nullable=False, index=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    classroom = relationship("ClassRoom", back_populates="attendance_sessions")
    subject = relationship("Subject", back_populates="attendance_sessions")
    staff = relationship("StaffProfile", back_populates="attendance_sessions")
    records = relationship(
        "AttendanceRecord", back_populates="session", cascade="all, delete-orphan"
    )


class AttendanceRecord(BaseModel):
    __tablename__ = "attendance_records"

    session_id = Column(
        UUID(as_uuid=True), ForeignKey("attendance_sessions.id"), nullable=False
    )
    student_id = Column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id"), nullable=False
    )
    status = Column(
        String(50), default=AttendanceStatus.present.value, nullable=False
    )
    remarks = Column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("StudentProfile", back_populates="attendance_records")
