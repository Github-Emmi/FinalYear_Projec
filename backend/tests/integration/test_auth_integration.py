"""Integration tests: authentication flow (login, refresh, /auth/me)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User

pytestmark = pytest.mark.asyncio


async def test_login_success(client: AsyncClient, admin_user: User):
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": admin_user.username, "password": "TestPass123!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, admin_user: User):
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": admin_user.username, "password": "WrongPassword!"},
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": "ghost_user_xyz", "password": "any"},
    )
    assert resp.status_code == 401


async def test_get_me_with_valid_token(client: AsyncClient, admin_user: User, auth_headers: dict):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == admin_user.username
    assert body["role"] == "admin"


async def test_get_me_without_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_refresh_token(client: AsyncClient, admin_user: User):
    login = await client.post(
        "/api/v1/auth/token",
        data={"username": admin_user.username, "password": "TestPass123!"},
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
