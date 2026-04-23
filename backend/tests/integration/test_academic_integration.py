"""Integration tests: academic entity CRUD (departments, session-years, classrooms, subjects)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_department(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/academic/departments",
        json={"name": f"Dept_{uuid.uuid4().hex[:6]}"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert "name" in body


async def test_list_departments(client: AsyncClient, auth_headers: dict):
    # Ensure at least one exists
    await client.post(
        "/api/v1/academic/departments",
        json={"name": f"Dept_{uuid.uuid4().hex[:6]}"},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/academic/departments", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


async def test_get_department_by_id(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/academic/departments",
        json={"name": f"Dept_{uuid.uuid4().hex[:6]}"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    dept_id = create.json()["id"]

    resp = await client.get(f"/api/v1/academic/departments/{dept_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == dept_id


async def test_department_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        f"/api/v1/academic/departments/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_department_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/academic/departments")
    assert resp.status_code == 401
