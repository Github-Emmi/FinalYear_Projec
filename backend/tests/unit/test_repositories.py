"""Unit tests — repositories: subclass checks (no DB required)."""

from __future__ import annotations

from app.repositories.academic import (
    ClassRoomRepository,
    DepartmentRepository,
    SessionYearRepository,
    SubjectRepository,
)
from app.repositories.assessment import (
    QuestionRepository,
    QuizAttemptRepository,
    QuizRepository,
    QuizResultRepository,
)
from app.repositories.assignment import AssignmentRepository, SubmissionRepository
from app.repositories.attendance import (
    AttendanceRecordRepository,
    AttendanceSessionRepository,
)
from app.repositories.audit import AuditRepository
from app.repositories.base import BaseRepository
from app.repositories.feedback import FeedbackStaffRepository, FeedbackStudentRepository
from app.repositories.leave import LeaveRepository
from app.repositories.notification import NotificationRepository
from app.repositories.staff import StaffRepository
from app.repositories.student import StudentRepository
from app.repositories.user import UserRepository


def test_user_repo_is_base():
    assert issubclass(UserRepository, BaseRepository)


def test_student_repo_is_base():
    assert issubclass(StudentRepository, BaseRepository)


def test_staff_repo_is_base():
    assert issubclass(StaffRepository, BaseRepository)


def test_department_repo_is_base():
    assert issubclass(DepartmentRepository, BaseRepository)


def test_session_year_repo_is_base():
    assert issubclass(SessionYearRepository, BaseRepository)


def test_classroom_repo_is_base():
    assert issubclass(ClassRoomRepository, BaseRepository)


def test_subject_repo_is_base():
    assert issubclass(SubjectRepository, BaseRepository)


def test_quiz_repo_is_base():
    assert issubclass(QuizRepository, BaseRepository)


def test_question_repo_is_base():
    assert issubclass(QuestionRepository, BaseRepository)


def test_quiz_attempt_repo_is_base():
    assert issubclass(QuizAttemptRepository, BaseRepository)


def test_quiz_result_repo_is_base():
    assert issubclass(QuizResultRepository, BaseRepository)


def test_assignment_repo_is_base():
    assert issubclass(AssignmentRepository, BaseRepository)


def test_submission_repo_is_base():
    assert issubclass(SubmissionRepository, BaseRepository)


def test_attendance_session_repo_is_base():
    assert issubclass(AttendanceSessionRepository, BaseRepository)


def test_attendance_record_repo_is_base():
    assert issubclass(AttendanceRecordRepository, BaseRepository)


def test_feedback_staff_repo_is_base():
    assert issubclass(FeedbackStaffRepository, BaseRepository)


def test_feedback_student_repo_is_base():
    assert issubclass(FeedbackStudentRepository, BaseRepository)


def test_leave_repo_is_base():
    assert issubclass(LeaveRepository, BaseRepository)


def test_notification_repo_is_base():
    assert issubclass(NotificationRepository, BaseRepository)


def test_audit_repo_is_base():
    assert issubclass(AuditRepository, BaseRepository)
