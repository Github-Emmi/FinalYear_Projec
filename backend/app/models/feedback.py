"""Feedback models: FeedbackStaff (student→staff), FeedbackStudent (staff→student)."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class FeedbackStaff(BaseModel):
    """Feedback submitted by a student about a staff member."""

    __tablename__ = "feedback_staff"

    staff_id = Column(
        UUID(as_uuid=True), ForeignKey("staff_profiles.id"), nullable=False
    )
    student_id = Column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id"), nullable=False
    )
    feedback_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1–5

    # ── Relationships ──────────────────────────────────────────────────────────
    staff = relationship("StaffProfile", back_populates="feedback_received")
    student = relationship("StudentProfile", back_populates="feedback_given")


class FeedbackStudent(BaseModel):
    """Feedback submitted by a staff member about a student."""

    __tablename__ = "feedback_students"

    student_id = Column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id"), nullable=False
    )
    staff_id = Column(
        UUID(as_uuid=True), ForeignKey("staff_profiles.id"), nullable=False
    )
    feedback_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1–5

    # ── Relationships ──────────────────────────────────────────────────────────
    student = relationship("StudentProfile", back_populates="feedback_received")
    staff = relationship("StaffProfile", back_populates="feedback_given")
