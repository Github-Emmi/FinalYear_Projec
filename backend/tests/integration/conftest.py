"""Shared fixtures for integration tests using an in-memory SQLite database.

All integration tests run against SQLite+aiosqlite. This requires that all
SQLAlchemy column types use generic (non-dialect-specific) types — enforced by
the Phase 5 UUID type fix in backend/app/models/.

Fixture scoping:
  test_engine    — session scope: one engine / one set of tables per test run
  session_factory— session scope: bound to test_engine
  db_session     — function scope: fresh transaction per test, rolled back after
  client         — function scope: AsyncClient with get_db overridden
  admin_user     — function scope: real User row in the test DB (admin role)
  auth_headers   — function scope: Bearer token for the admin user
"""

from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers all models with Base.metadata
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import create_app
from app.models.user import User, UserRole

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# ── Engine + tables (session-scoped) ─────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def test_engine(event_loop):
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="session")
def session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)


# ── DB session (function-scoped, rolled back after each test) ─────────────────

@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
        await session.rollback()


# ── HTTP client (function-scoped, get_db overridden) ─────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, event_loop) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Admin user (function-scoped) ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        username=f"admin_{uuid.uuid4().hex[:8]}",
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("TestPass123!"),
        first_name="Admin",
        last_name="User",
        role=UserRole.admin.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, admin_user: User) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": admin_user.username, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Auth fixture failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
