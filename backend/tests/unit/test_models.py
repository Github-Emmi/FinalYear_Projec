"""Unit tests — ORM models: tablenames, inheritance, 20-table count."""

from __future__ import annotations

import app.models  # noqa: F401 — side-effect: registers all tables
from app.core.database import Base
from app.models.academic import ClassRoom, Department, SessionYear, Subject
from app.models.assessment import Question, Quiz, QuizAttempt, QuizResult
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.audit import AuditLog
from app.models.base import BaseModel
from app.models.feedback import FeedbackStaff, FeedbackStudent
from app.models.leave import LeaveRequest
from app.models.notification import Notification
from app.models.staff import StaffProfile
from app.models.student import StudentProfile
from app.models.user import User


def test_user_tablename():
    assert User.__tablename__ == "users"


def test_department_tablename():
    assert Department.__tablename__ == "departments"


def test_session_year_tablename():
    assert SessionYear.__tablename__ == "session_years"


def test_classroom_tablename():
    assert ClassRoom.__tablename__ == "classrooms"


def test_subject_tablename():
    assert Subject.__tablename__ == "subjects"


def test_staff_profile_tablename():
    assert StaffProfile.__tablename__ == "staff_profiles"


def test_student_profile_tablename():
    assert StudentProfile.__tablename__ == "student_profiles"


def test_quiz_tablename():
    assert Quiz.__tablename__ == "quizzes"


def test_question_tablename():
    assert Question.__tablename__ == "questions"


def test_quiz_attempt_tablename():
    assert QuizAttempt.__tablename__ == "quiz_attempts"


def test_quiz_result_tablename():
    assert QuizResult.__tablename__ == "quiz_results"


def test_assignment_tablename():
    assert Assignment.__tablename__ == "assignments"


def test_assignment_submission_tablename():
    assert AssignmentSubmission.__tablename__ == "assignment_submissions"


def test_attendance_session_tablename():
    assert AttendanceSession.__tablename__ == "attendance_sessions"


def test_attendance_record_tablename():
    assert AttendanceRecord.__tablename__ == "attendance_records"


def test_feedback_staff_tablename():
    assert FeedbackStaff.__tablename__ == "feedback_staff"


def test_feedback_student_tablename():
    assert FeedbackStudent.__tablename__ == "feedback_students"


def test_leave_request_tablename():
    assert LeaveRequest.__tablename__ == "leave_requests"


def test_notification_tablename():
    assert Notification.__tablename__ == "notifications"


def test_audit_log_tablename():
    assert AuditLog.__tablename__ == "audit_logs"


def test_all_models_inherit_base_model():
    for model in [
        User, Department, SessionYear, ClassRoom, Subject,
        StaffProfile, StudentProfile,
        Quiz, Question, QuizAttempt, QuizResult,
        Assignment, AssignmentSubmission,
        AttendanceSession, AttendanceRecord,
        FeedbackStaff, FeedbackStudent,
        LeaveRequest, Notification, AuditLog,
    ]:
        assert issubclass(model, BaseModel), f"{model.__name__} must inherit BaseModel"


def test_total_table_count():
    assert len(Base.metadata.tables) == 20, (
        f"Expected 20 tables, found {len(Base.metadata.tables)}: "
        f"{sorted(Base.metadata.tables)}"
    )
