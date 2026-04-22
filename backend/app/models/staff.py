"""StaffProfile model — extends User for staff-specific data."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class StaffProfile(BaseModel):
    __tablename__ = "staff_profiles"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    department_id = Column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    designation = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    profile_picture = Column(String(500), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user = relationship("User", back_populates="staff_profile")
    department = relationship("Department", back_populates="staff_profiles")
    subjects = relationship("Subject", back_populates="staff")
    quizzes = relationship("Quiz", back_populates="staff")
    assignments = relationship("Assignment", back_populates="staff")
    attendance_sessions = relationship(
        "AttendanceSession", back_populates="staff"
    )
    feedback_received = relationship("FeedbackStaff", back_populates="staff")
    feedback_given = relationship("FeedbackStudent", back_populates="staff")
    leave_requests_reviewed = relationship(
        "LeaveRequest", back_populates="reviewed_by"
    )
