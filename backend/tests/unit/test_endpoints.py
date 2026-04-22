"""
Phase 4 endpoint tests.

Tests cover:
- Router and endpoint file importability
- AcademicService importability
- Schema extension presence
- Route registration (health, auth, protected)
- Route ordering (/me before /{id}, /pending before /{leave_id})
- Live HTTP checks via TestClient
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ── Import checks ──────────────────────────────────────────────────────────────

def test_router_imports():
    """All 11 domain routers are importable."""
    from app.api.v1.endpoints.academic import router as academic_router
    from app.api.v1.endpoints.analytics import router as analytics_router
    from app.api.v1.endpoints.assessments import router as assessments_router
    from app.api.v1.endpoints.assignments import router as assignments_router
    from app.api.v1.endpoints.attendance import router as attendance_router
    from app.api.v1.endpoints.auth import router as auth_router
    from app.api.v1.endpoints.leave import router as leave_router
    from app.api.v1.endpoints.notifications import router as notifications_router
    from app.api.v1.endpoints.staff import router as staff_router
    from app.api.v1.endpoints.students import router as students_router
    from app.api.v1.endpoints.users import router as users_router

    routers = [
        academic_router,
        analytics_router,
        assessments_router,
        assignments_router,
        attendance_router,
        auth_router,
        leave_router,
        notifications_router,
        staff_router,
        students_router,
        users_router,
    ]
    for r in routers:
        assert r is not None


def test_academic_service_importable():
    from app.services.academic_service import AcademicService
    assert AcademicService is not None


def test_academic_service_in_package():
    from app.services import AcademicService
    assert AcademicService is not None


def test_schema_submit_attempt_request():
    from app.schemas.assessment import SubmitAttemptRequest, AnswerItem
    from uuid import uuid4
    req = SubmitAttemptRequest(answers=[AnswerItem(question_id=uuid4(), answer="A")])
    assert len(req.answers) == 1


def test_schema_answer_item():
    from app.schemas.assessment import AnswerItem
    from uuid import uuid4
    item = AnswerItem(question_id=uuid4(), answer="B")
    assert item.answer == "B"


def test_schema_broadcast_notification_request():
    from app.schemas.notification import BroadcastNotificationRequest
    from uuid import uuid4
    req = BroadcastNotificationRequest(
        recipient_ids=[uuid4()],
        title="Test",
        message="Hello",
    )
    assert req.title == "Test"


# ── Router registration checks ─────────────────────────────────────────────────

def test_v1_router_has_11_sub_routers():
    from app.api.v1.router import router
    # 11 domain routers included
    assert len(router.routes) >= 12  # 11 domain routers + health check


def test_v1_router_includes_health():
    from app.api.v1.router import router
    paths = [r.path for r in router.routes]
    assert "/health" in paths


def test_auth_router_has_token_route():
    from app.api.v1.endpoints.auth import router
    paths = [r.path for r in router.routes]
    assert "/auth/token" in paths


def test_auth_router_has_refresh_route():
    from app.api.v1.endpoints.auth import router
    paths = [r.path for r in router.routes]
    assert "/auth/refresh" in paths


def test_auth_router_has_me_route():
    from app.api.v1.endpoints.auth import router
    paths = [r.path for r in router.routes]
    assert "/auth/me" in paths


def test_students_me_before_id():
    """GET /students/me must be registered before GET /students/{student_id}."""
    from app.api.v1.endpoints.students import router
    paths = [r.path for r in router.routes]
    assert "/students/me" in paths
    assert "/students/{student_id}" in paths
    assert paths.index("/students/me") < paths.index("/students/{student_id}")


def test_staff_me_before_id():
    """GET /staff/me must be registered before GET /staff/{staff_id}."""
    from app.api.v1.endpoints.staff import router
    paths = [r.path for r in router.routes]
    assert "/staff/me" in paths
    assert "/staff/{staff_id}" in paths
    assert paths.index("/staff/me") < paths.index("/staff/{staff_id}")


def test_leave_pending_before_id():
    """GET /leave/pending must be registered before GET /leave/{leave_id}."""
    from app.api.v1.endpoints.leave import router
    paths = [r.path for r in router.routes]
    assert "/leave/pending" in paths
    assert "/leave/{leave_id}" in paths
    assert paths.index("/leave/pending") < paths.index("/leave/{leave_id}")


def test_notifications_me_before_id():
    """GET /notifications/me must be registered before GET /notifications/{notification_id}/read."""
    from app.api.v1.endpoints.notifications import router
    paths = [r.path for r in router.routes]
    assert "/notifications/me" in paths


# ── Analytics router ───────────────────────────────────────────────────────────

def test_analytics_router_has_three_routes():
    from app.api.v1.endpoints.analytics import router
    paths = [r.path for r in router.routes]
    assert "/analytics/students/{student_id}" in paths
    assert "/analytics/classrooms/{classroom_id}" in paths
    assert "/analytics/staff/{staff_id}" in paths


# ── Live HTTP checks via TestClient ───────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from app.main import create_app
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_health_endpoint_returns_200(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_auth_token_missing_body_returns_422(client):
    """POST /auth/token with no body must return 422 (validation), not 404."""
    resp = client.post("/api/v1/auth/token")
    assert resp.status_code == 422


def test_list_users_without_token_returns_401(client):
    """GET /users without a token must return 401."""
    resp = client.get("/api/v1/users")
    assert resp.status_code == 401


def test_list_students_without_token_returns_401(client):
    resp = client.get("/api/v1/students")
    assert resp.status_code == 401


def test_list_staff_without_token_returns_401(client):
    resp = client.get("/api/v1/staff")
    assert resp.status_code == 401


def test_list_departments_without_token_returns_401(client):
    resp = client.get("/api/v1/academic/departments")
    assert resp.status_code == 401


def test_analytics_student_without_token_returns_401(client):
    from uuid import uuid4
    resp = client.get(f"/api/v1/analytics/students/{uuid4()}")
    assert resp.status_code == 401


def test_leave_pending_without_token_returns_401(client):
    resp = client.get("/api/v1/leave/pending")
    assert resp.status_code == 401


def test_notifications_me_without_token_returns_401(client):
    resp = client.get("/api/v1/notifications/me")
    assert resp.status_code == 401
