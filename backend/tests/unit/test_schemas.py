"""Unit tests — Pydantic schemas: instantiation and field presence."""

from __future__ import annotations

from uuid import uuid4

from app.models.user import UserRole
from app.schemas.academic import (
    ClassRoomCreate,
    DepartmentCreate,
    SessionYearCreate,
    SubjectCreate,
)
from app.schemas.assessment import QuizCreate
from app.schemas.assignment import AssignmentCreate
from app.schemas.attendance import AttendanceSessionCreate
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.feedback import FeedbackStaffCreate
from app.schemas.leave import LeaveRequestCreate
from app.schemas.notification import NotificationCreate
from app.schemas.staff import StaffProfileCreate
from app.schemas.student import StudentProfileCreate
from app.schemas.user import UserCreate


# ── auth ──────────────────────────────────────────────────────────────────────

def test_login_request_schema():
    s = LoginRequest(username="alice", password="secret")
    assert s.username == "alice"


def test_token_response_schema():
    s = TokenResponse(access_token="tok", refresh_token="rtok", token_type="bearer")
    assert s.token_type == "bearer"


# ── user ─────────────────────────────────────────────────────────────────────

def test_user_create_schema():
    s = UserCreate(
        username="alice",
        email="alice@example.com",
        password="pass1234",
        first_name="Alice",
        last_name="Smith",
        role=UserRole.student,
    )
    assert s.role == UserRole.student


# ── academic ──────────────────────────────────────────────────────────────────

def test_department_create_schema():
    s = DepartmentCreate(name="Computer Science")
    assert s.name == "Computer Science"


def test_session_year_create_schema():
    s = SessionYearCreate(start_year=2024, end_year=2025)
    assert s.start_year == 2024


def test_classroom_create_schema():
    s = ClassRoomCreate(name="Class A", department_id=uuid4())
    assert s.name == "Class A"


def test_subject_create_schema():
    s = SubjectCreate(name="Math", classroom_id=uuid4())
    assert s.name == "Math"


# ── staff / student ───────────────────────────────────────────────────────────

def test_staff_profile_create_schema():
    s = StaffProfileCreate(user_id=uuid4())
    assert s.user_id is not None


def test_student_profile_create_schema():
    s = StudentProfileCreate(user_id=uuid4())
    assert s.user_id is not None


# ── assessment ────────────────────────────────────────────────────────────────

def test_quiz_create_schema():
    s = QuizCreate(title="Quiz 1", subject_id=uuid4(), staff_id=uuid4())
    assert s.title == "Quiz 1"


# ── assignment ────────────────────────────────────────────────────────────────

def test_assignment_create_schema():
    s = AssignmentCreate(title="HW 1", subject_id=uuid4(), staff_id=uuid4())
    assert s.title == "HW 1"


# ── attendance ────────────────────────────────────────────────────────────────

def test_attendance_session_create_schema():
    from datetime import date
    s = AttendanceSessionCreate(classroom_id=uuid4(), subject_id=uuid4(), staff_id=uuid4(), date=date.today())
    assert s.date == date.today()


# ── feedback ──────────────────────────────────────────────────────────────────

def test_feedback_staff_create_schema():
    s = FeedbackStaffCreate(
        staff_id=uuid4(), student_id=uuid4(), feedback_text="Great teacher!"
    )
    assert s.feedback_text == "Great teacher!"


# ── leave ─────────────────────────────────────────────────────────────────────

def test_leave_request_create_schema():
    from datetime import date
    today = date.today()
    s = LeaveRequestCreate(
        user_id=uuid4(),
        leave_type="sick",
        start_date=today,
        end_date=today,
        reason="Flu",
    )
    assert s.reason == "Flu"


# ── notification ──────────────────────────────────────────────────────────────

def test_notification_create_schema():
    s = NotificationCreate(
        recipient_id=uuid4(), title="Hello", message="World"
    )
    assert s.title == "Hello"
