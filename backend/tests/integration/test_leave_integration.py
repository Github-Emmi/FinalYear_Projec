"""Integration tests: leave request flow (apply, pending list, RBAC gates)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def student_user(db_session: AsyncSession) -> User:
    """A student-role user for leave request tests."""
    user = User(
        id=uuid.uuid4(),
        username=f"student_{uuid.uuid4().hex[:8]}",
        email=f"student_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("TestPass123!"),
        first_name="Bob",
        last_name="Smith",
        role=UserRole.student.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def student_headers(client: AsyncClient, student_user: User) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": student_user.username, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Student auth fixture failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _leave_payload(user_id: uuid.UUID) -> dict:
    today = date.today()
    return {
        "user_id": str(user_id),
        "leave_type": "sick",
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=2)).isoformat(),
        "reason": "Feeling unwell",
    }


async def test_apply_leave(client: AsyncClient, student_user: User, student_headers: dict):
    resp = await client.post(
        "/api/v1/leave",
        json=_leave_payload(student_user.id),
        headers=student_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["leave_type"] == "sick"


async def test_get_pending_leaves_as_admin(
    client: AsyncClient,
    admin_user: User,
    auth_headers: dict,
    student_user: User,
    student_headers: dict,
):
    # Student applies for leave first
    apply = await client.post(
        "/api/v1/leave",
        json=_leave_payload(student_user.id),
        headers=student_headers,
    )
    assert apply.status_code == 201

    resp = await client.get("/api/v1/leave/pending", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


async def test_get_pending_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/leave/pending")
    assert resp.status_code == 401


async def test_get_leave_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/leave/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


async def test_apply_leave_unauthenticated(client: AsyncClient, student_user: User):
    resp = await client.post(
        "/api/v1/leave",
        json=_leave_payload(student_user.id),
    )
    assert resp.status_code == 401
