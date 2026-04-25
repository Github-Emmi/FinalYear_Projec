"""Unit tests — service layer: import checks, method presence, RBAC logic."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Service import tests ───────────────────────────────────────────────────────

def test_auth_service_importable():
    from app.services.auth_service import AuthService
    assert callable(AuthService)


def test_auth_service_has_login():
    from app.services.auth_service import AuthService
    assert inspect.iscoroutinefunction(AuthService.login)


def test_auth_service_has_refresh():
    from app.services.auth_service import AuthService
    assert inspect.iscoroutinefunction(AuthService.refresh)


def test_user_service_importable():
    from app.services.user_service import UserService
    assert callable(UserService)


def test_user_service_has_crud():
    from app.services.user_service import UserService
    for method in ("create", "get_by_id", "get_all", "update", "soft_delete", "change_password"):
        assert inspect.iscoroutinefunction(getattr(UserService, method)), f"UserService.{method} must be async"


def test_student_service_importable():
    from app.services.student_service import StudentService
    assert callable(StudentService)


def test_student_service_methods():
    from app.services.student_service import StudentService
    for method in ("create_profile", "get_profile", "get_by_user_id", "update_profile"):
        assert inspect.iscoroutinefunction(getattr(StudentService, method))


def test_staff_service_importable():
    from app.services.staff_service import StaffService
    assert callable(StaffService)


def test_staff_service_methods():
    from app.services.staff_service import StaffService
    for method in ("create_profile", "get_profile", "get_by_user_id", "update_profile"):
        assert inspect.iscoroutinefunction(getattr(StaffService, method))


def test_assessment_service_importable():
    from app.services.assessment_service import AssessmentService
    assert callable(AssessmentService)


def test_assessment_service_methods():
    from app.services.assessment_service import AssessmentService
    for method in ("create_quiz", "publish_quiz", "close_quiz", "start_attempt", "submit_attempt"):
        assert inspect.iscoroutinefunction(getattr(AssessmentService, method))


def test_assessment_service_ai_grade_method():
    from app.services.assessment_service import AssessmentService
    assert inspect.iscoroutinefunction(AssessmentService._ai_grade)


def test_assignment_service_importable():
    from app.services.assignment_service import AssignmentService
    assert callable(AssignmentService)


def test_assignment_service_methods():
    from app.services.assignment_service import AssignmentService
    for method in ("create", "get", "update", "delete", "submit", "grade", "grade_with_ai"):
        assert inspect.iscoroutinefunction(getattr(AssignmentService, method))


def test_attendance_service_importable():
    from app.services.attendance_service import AttendanceService
    assert callable(AttendanceService)


def test_attendance_service_methods():
    from app.services.attendance_service import AttendanceService
    for method in ("create_session", "mark_attendance", "get_student_attendance_summary"):
        assert inspect.iscoroutinefunction(getattr(AttendanceService, method))


def test_leave_service_importable():
    from app.services.leave_service import LeaveService
    assert callable(LeaveService)


def test_leave_service_methods():
    from app.services.leave_service import LeaveService
    for method in ("apply", "get", "update", "review", "get_pending", "cancel"):
        assert inspect.iscoroutinefunction(getattr(LeaveService, method))


def test_notification_service_importable():
    from app.services.notification_service import NotificationService
    assert callable(NotificationService)


def test_notification_service_methods():
    from app.services.notification_service import NotificationService
    for method in ("send", "send_broadcast", "mark_read", "get_unread", "delete"):
        assert inspect.iscoroutinefunction(getattr(NotificationService, method))


def test_analytics_service_importable():
    from app.services.analytics_service import AnalyticsService
    assert callable(AnalyticsService)


def test_analytics_service_methods():
    from app.services.analytics_service import AnalyticsService
    for method in ("student_summary", "classroom_summary", "staff_summary"):
        assert inspect.iscoroutinefunction(getattr(AnalyticsService, method))


def test_email_service_importable():
    from app.services.email_service import EmailService
    assert callable(EmailService)


def test_email_service_methods():
    from app.services.email_service import EmailService
    for method in ("send_email", "send_welcome", "send_leave_decision"):
        assert inspect.iscoroutinefunction(getattr(EmailService, method))


@pytest.mark.asyncio
async def test_email_service_skips_when_no_smtp():
    """EmailService.send_email must return None when SMTP_USER is unset."""
    from app.services.email_service import EmailService

    svc = EmailService()
    # Force SMTP_USER to None regardless of any .env file
    svc._settings.SMTP_USER = None
    result = await svc.send_email("test@example.com", "Subject", "Body")
    assert result is None


# ── RBAC / deps tests ─────────────────────────────────────────────────────────

def test_deps_importable():
    from app.api.deps import get_current_user, require_role
    assert callable(get_current_user)
    assert callable(require_role)


def test_require_role_returns_callable():
    from app.api.deps import require_role
    guard = require_role("admin")
    assert callable(guard)


def test_require_role_creates_different_guards():
    from app.api.deps import require_role
    admin_guard = require_role("admin")
    staff_guard = require_role("admin", "staff")
    # Each call creates a distinct closure
    assert admin_guard is not staff_guard


def test_admin_only_convenience():
    from app.api.deps import AdminOnly
    assert callable(AdminOnly)


def test_staff_or_admin_convenience():
    from app.api.deps import StaffOrAdmin
    assert callable(StaffOrAdmin)


def test_services_init_exports_all():
    """services/__init__.py must export all 11 service classes."""
    import app.services as svc
    expected = [
        "AuthService", "UserService", "StudentService", "StaffService",
        "AssessmentService", "AssignmentService", "AttendanceService",
        "LeaveService", "NotificationService", "AnalyticsService", "EmailService",
    ]
    for name in expected:
        assert hasattr(svc, name), f"app.services must export {name}"


# ── AI grading fallback test ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_grade_fallback_when_openai_unavailable():
    """_ai_grade must return (False, 0.0, fallback msg) when ai_agent raises."""
    from app.services.assessment_service import AssessmentService
    from unittest.mock import AsyncMock, MagicMock

    svc = AssessmentService.__new__(AssessmentService)  # skip __init__

    # Mock question
    question = MagicMock()
    question.text = "Describe photosynthesis."
    question.correct_answer = "Process of converting light to energy."
    question.marks = 5.0

    # Patch ai_agent.grade_short_answer to raise, simulating total failure
    with patch("app.services.assessment_service.__builtins__"):
        pass  # no-op; the real patch is below

    from unittest.mock import patch as _patch
    with _patch("app.services.ai_agent.ai_agent") as mock_agent:
        mock_agent.grade_short_answer = AsyncMock(side_effect=Exception("OpenAI down"))
        is_correct, marks, feedback = await svc._ai_grade(question, "Some answer")

    assert is_correct is False
    assert marks == 0.0
    assert "unavailable" in feedback.lower()


# ── Config extensions test ───────────────────────────────────────────────────

def test_config_has_openai_settings():
    from app.core.config import get_settings
    settings = get_settings()
    assert hasattr(settings, "OPENAI_API_KEY")
    assert hasattr(settings, "OPENAI_MODEL")
    # Default model is the OpenRouter free pool; override via .env for specific models
    assert settings.OPENAI_MODEL  # non-empty string is all we require


def test_config_has_smtp_settings():
    from app.core.config import get_settings
    settings = get_settings()
    for attr in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_FROM", "SMTP_TLS"):
        assert hasattr(settings, attr), f"Settings must have {attr}"
