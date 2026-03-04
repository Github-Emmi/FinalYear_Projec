"""
Attendance models: Attendance, AttendanceReport
Results model: StudentResult
"""

from sqlalchemy import Integer, Float, Column, String, DateTime, ForeignKey, Float, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Attendance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Attendance session for a subject on a specific date.
    One attendance record per subject per date per session.
    """
    __tablename__ = "attendance"

    # Links
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subject.id"), nullable=False, index=True)
    session_year_id = Column(UUID(as_uuid=True), ForeignKey("session_year.id"), nullable=False, index=True)
    
    # Date
    attendance_date = Column(DateTime, nullable=False, index=True)
    
    # Relationships
    subject = relationship("Subject")
    session_year = relationship("SessionYear")
    reports = relationship("AttendanceReport", back_populates="attendance", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("subject_id", "attendance_date", name="uq_attendance_subject_date"),
        Index("ix_attendance_subject_session", "subject_id", "session_year_id"),
    )

    def __str__(self):
        return f"{self.subject.subject_name} - {self.attendance_date.date()}"


class AttendanceReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Per-student attendance record for a specific attendance session.
    Tracks whether a student was present or absent.
    """
    __tablename__ = "attendance_report"

    # Links
    student_id = Column(UUID(as_uuid=True), ForeignKey("student.id"), nullable=False, index=True)
    attendance_id = Column(UUID(as_uuid=True), ForeignKey("attendance.id"), nullable=False, index=True)
    
    # Status
    status: Boolean = Column(Boolean, default=True, nullable=False)  # True = Present, False = Absent
    remarks = Column(String(255), nullable=True)  # e.g., "Medical leave", "Late"
    
    # Relationships
    student = relationship("Student", backref="attendance_records")
    attendance = relationship("Attendance", back_populates="reports")

    __table_args__ = (
        UniqueConstraint("student_id", "attendance_id", name="uq_attendance_report_student_attendance"),
        Index("ix_attendance_report_student", "student_id"),
        Index("ix_attendance_report_status", "status"),
    )

    def __str__(self):
        status_str = "Present" if self.status else "Absent"
        return f"{self.student.user.username} - {status_str} on {self.attendance.attendance_date.date()}"


class StudentResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Academic result for a student in a subject.
    Aggregates exam score, assignment score, and total score.
    """
    __tablename__ = "student_result"

    # Links
    student_id = Column(UUID(as_uuid=True), ForeignKey("student.id"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subject.id"), nullable=False, index=True)
    session_year_id = Column(UUID(as_uuid=True), ForeignKey("session_year.id"), nullable=False, index=True)
    
    # Scores
    exam_score = Column(Float, default=0.0, nullable=False)  # Out of 100
    assignment_score = Column(Float, default=0.0, nullable=False)  # Out of 100
    quiz_score = Column(Float, default=0.0, nullable=False)  # Out of 100
    participation_score = Column(Float, default=0.0, nullable=False)  # Out of 100
    
    # Weights (customizable per institution)
    exam_weight = Column(Float, default=40.0, nullable=False)  # %
    assignment_weight = Column(Float, default=30.0, nullable=False)  # %
    quiz_weight = Column(Float, default=20.0, nullable=False)  # %
    participation_weight = Column(Float, default=10.0, nullable=False)  # %
    
    # Derived scores
    total_score = Column(Float, default=0.0, nullable=False)
    percentage = Column(Float, nullable=True)
    grade = Column(String(2), nullable=True)  # A, B, C, D, F
    
    # Comments
    remark = Column(String(255), nullable=True)  # Pass, Fail, Pass with distinction, etc.
    admin_comment = Column(String(500), nullable=True)
    
    # Relationships
    student = relationship("Student", backref="results")
    subject = relationship("Subject")
    session_year = relationship("SessionYear")

    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "session_year_id", name="uq_student_result"),
        Index("ix_student_result_subject_session", "subject_id", "session_year_id"),
        Index("ix_student_result_grade", "grade"),
    )

    def __str__(self):
        return f"{self.student.user.username} - {self.subject.subject_name}: {self.percentage}%"
    
    def calculate_total(self) -> float:
        """Calculate weighted total score"""
        total = (
            (self.exam_score * self.exam_weight / 100) +
            (self.assignment_score * self.assignment_weight / 100) +
            (self.quiz_score * self.quiz_weight / 100) +
            (self.participation_score * self.participation_weight / 100)
        )
        return round(total, 2)
