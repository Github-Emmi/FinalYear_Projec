"""Assignment models: Assignment, AssignmentSubmission."""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AssignmentStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    closed = "closed"


class SubmissionStatus(str, enum.Enum):
    submitted = "submitted"
    graded = "graded"
    returned = "returned"


class Assignment(BaseModel):
    __tablename__ = "assignments"

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    subject_id = Column(Uuid, ForeignKey("subjects.id"), nullable=False)
    staff_id = Column(
        Uuid, ForeignKey("staff_profiles.id"), nullable=False
    )
    status = Column(
        String(50), default=AssignmentStatus.draft.value, nullable=False
    )
    due_date = Column(DateTime, nullable=True)
    max_score = Column(Float, default=100.0, nullable=False)
    file_url = Column(String(500), nullable=True)
    ai_grading_enabled = Column(
        Boolean, default=False, nullable=False, server_default="false"
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    subject = relationship("Subject", back_populates="assignments")
    staff = relationship("StaffProfile", back_populates="assignments")
    submissions = relationship(
        "AssignmentSubmission",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class AssignmentSubmission(BaseModel):
    __tablename__ = "assignment_submissions"

    assignment_id = Column(
        Uuid, ForeignKey("assignments.id"), nullable=False
    )
    student_id = Column(
        Uuid, ForeignKey("student_profiles.id"), nullable=False
    )
    status = Column(
        String(50), default=SubmissionStatus.submitted.value, nullable=False
    )
    file_url = Column(String(500), nullable=True)
    score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    graded_at = Column(DateTime, nullable=True)
    ai_feedback = Column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("StudentProfile", back_populates="submissions")
