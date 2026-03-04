"""
Models package - imports all models for registration with SQLAlchemy Base.

This file ensures all models are imported and registered with the
DeclarativeBase metadata, so they can be discovered by Alembic for migrations.
"""

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditableMixin
from .user import CustomUser, RememberToken, ApiToken, RedisSession
from .academic import SessionYear, Department, Class, Subject, TimeTable
from .staff import Staff, AdminHOD
from .student import Student
from .assessment import Quiz, Question, QuizAttempt, StudentQuizSubmission, StudentAnswer
from .assessment import Assignment, AssignmentSubmission
from .assessment_results import Attendance, AttendanceReport, StudentResult
from .leave import LeaveReportStudent, LeaveReportStaff
from .feedback import FeedbackStudent, FeedbackStaff
from .notification import NotificationStudent, NotificationStaff, Event
from .audit import AuditLog

__all__ = [
    # Base classes
    "Base",
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditableMixin",
    # User models
    "CustomUser",
    "RememberToken",
    "ApiToken",
    "RedisSession",
    # Academic models
    "SessionYear",
    "Department",
    "Class",
    "Subject",
    "TimeTable",
    # Staff models
    "Staff",
    "AdminHOD",
    # Student models
    "Student",
    # Assessment models
    "Quiz",
    "Question",
    "QuizAttempt",
    "StudentQuizSubmission",
    "StudentAnswer",
    "Assignment",
    "AssignmentSubmission",
    # Results models
    "Attendance",
    "AttendanceReport",
    "StudentResult",
    # Leave models
    "LeaveReportStudent",
    "LeaveReportStaff",
    # Feedback models
    "FeedbackStudent",
    "FeedbackStaff",
    # Notification models
    "NotificationStudent",
    "NotificationStaff",
    "Event",
    # Audit models
    "AuditLog",
]
