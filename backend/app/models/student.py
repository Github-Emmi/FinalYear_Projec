"""StudentProfile model — extends User for student-specific data."""

from __future__ import annotations

from sqlalchemy import Column, Date, ForeignKey, String, Text
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class StudentProfile(BaseModel):
    __tablename__ = "student_profiles"

    user_id = Column(
        Uuid, ForeignKey("users.id"), unique=True, nullable=False
    )
    classroom_id = Column(
        Uuid, ForeignKey("classrooms.id"), nullable=True
    )
    session_year_id = Column(
        Uuid, ForeignKey("session_years.id"), nullable=True
    )
    roll_number = Column(String(50), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    profile_picture = Column(String(500), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user = relationship("User", back_populates="student_profile")
    classroom = relationship("ClassRoom", back_populates="students")
    session_year = relationship("SessionYear", back_populates="student_profiles")
    quiz_attempts = relationship("QuizAttempt", back_populates="student")
    submissions = relationship("AssignmentSubmission", back_populates="student")
    attendance_records = relationship(
        "AttendanceRecord", back_populates="student"
    )
    feedback_given = relationship("FeedbackStaff", back_populates="student")
    feedback_received = relationship("FeedbackStudent", back_populates="student")
