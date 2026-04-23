"""Integration tests: user management endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_list_users_as_admin(client: AsyncClient, admin_user, auth_headers: dict):
    resp = await client.get("/api/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    usernames = [u["username"] for u in users]
    assert admin_user.username in usernames


async def test_create_user_as_admin(client: AsyncClient, auth_headers: dict):
    payload = {
        "username": f"new_student_{uuid.uuid4().hex[:6]}",
        "email": f"student_{uuid.uuid4().hex[:6]}@example.com",
        "password": "SecurePass1!",
        "first_name": "Jane",
        "last_name": "Doe",
        "role": "student",
    }
    resp = await client.post("/api/v1/users", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == payload["username"]
    assert body["role"] == "student"


async def test_get_user_by_id(client: AsyncClient, admin_user, auth_headers: dict):
    resp = await client.get(f"/api/v1/users/{admin_user.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(admin_user.id)


async def test_get_user_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/users/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


async def test_list_users_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 401
