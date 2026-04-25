# ExecPlan: Phase 5 — Integration Tests, Docker Validation & OpenAPI Export

## Context

Phase 5 of the LMS FastAPI migration on branch `phase/1-fresh-scaffold`.

**Prior phase commits:**
- Phase 1 `6112a95d` — scaffold, health endpoint
- Phase 2 `04db3237` — 20 ORM models, 13 repositories, migration 001, 59 unit tests
- Phase 3 `0abb98f8` — 11 service classes, RBAC deps, AI grading, async SMTP, 93 unit tests
- Phase 4 `7f54b44e` — 11 domain routers, 50+ endpoints, 118 tests passing

**What exists right now:**
- `backend/tests/integration/__init__.py` — empty stub (created by scaffold)
- `backend/tests/e2e/__init__.py` — empty stub
- `backend/tests/unit/` — 6 test files, 118 passing tests
- `backend/tests/conftest.py` — session-scoped `event_loop`, `AsyncClient` fixture pointing at the live app
- `backend/app/core/security.py` — `hash_password(plain) -> str`, `verify_password(plain, hashed) -> bool`
- `backend/app/models/user.py` — `User` model; password field is `password_hash`; role field is `role` (string)
- `backend/app/core/database.py` — `Base`, `get_db`, `create_async_engine` with PostgreSQL+asyncpg URL
- `backend/app/main.py` — `create_app() -> FastAPI` factory; used by tests
- `backend/app/api/deps.py` — `get_db` re-exported; RBAC guards defined
- `backend/scripts/` — directory exists (empty)
- `backend/docs/` — contains ADR.md, API_DESIGN.md, ARCHITECTURE.md, DATA_MODEL.md, MIGRATION_PLAN.md, SECURITY.md
- `backend/requirements.txt` — `fastapi==0.115.14`, no `aiosqlite`
- `backend/.env.example` — has DB, Redis, RabbitMQ, Security settings; missing explicit OPENAI and SMTP sections

**Critical blocker identified:** All 10 model files use
`from sqlalchemy.dialects.postgresql import UUID` and `UUID(as_uuid=True)` for both
primary keys (via `UUIDPrimaryKeyMixin` in `base.py`) and all FK columns.
This PostgreSQL-dialect type **fails on SQLite** (`create_all` raises `CompileError`).
SQLAlchemy 2.0 provides a dialect-agnostic `sqlalchemy.Uuid` type that renders as
native UUID on PostgreSQL and CHAR(36) on SQLite. Replacing the import is a
correct, non-breaking improvement to the codebase.

**Runtime (Python 3.14.3, FastAPI 0.115.14, Pydantic v2, SQLAlchemy 2.0.49)**

---

## Scope

**Files to MODIFY:**
- `backend/app/models/base.py` — replace `postgresql.UUID` import → `sqlalchemy.Uuid`
- `backend/app/models/academic.py` — same
- `backend/app/models/student.py` — same
- `backend/app/models/staff.py` — same
- `backend/app/models/assessment.py` — same
- `backend/app/models/assignment.py` — same
- `backend/app/models/attendance.py` — same
- `backend/app/models/feedback.py` — same
- `backend/app/models/leave.py` — same
- `backend/app/models/notification.py` — same
- `backend/app/models/audit.py` — same  *(11 model files total, sed bulk operation)*
- `backend/requirements.txt` — add `aiosqlite>=2.0.0`
- `backend/.env.example` — add OPENAI and SMTP sections with documentation comments

**Files to CREATE:**
- `backend/tests/integration/conftest.py` — SQLite in-memory test fixtures
- `backend/tests/integration/test_auth_integration.py` — 6 tests
- `backend/tests/integration/test_users_integration.py` — 5 tests
- `backend/tests/integration/test_academic_integration.py` — 5 tests
- `backend/tests/integration/test_leave_integration.py` — 5 tests
- `backend/scripts/export_openapi.py` — export OpenAPI schema to `docs/openapi.json`

**No other files change.**

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Test DB backend | `aiosqlite` in-memory SQLite | No Docker required for unit+integration; fast; sufficient for HTTP/service layer coverage |
| UUID fix strategy | Replace with `sqlalchemy.Uuid` (not `TypeDecorator`) | Non-breaking, idiomatic SQLAlchemy 2.0; works on both PostgreSQL and SQLite natively |
| Test isolation | Rollback-per-test via nested `savepoint` / session rollback | Eliminates test ordering dependencies; tables created once per session |
| Integration test scope | Auth, Users, Academic, Leave | These 4 flows cover all RBAC paths and repository patterns; other domains follow identical patterns |
| server_default booleans | Keep as-is; Python-side `default=False` is used by ORM | Server defaults only apply to raw SQL — all ORM inserts use Python defaults; SQLite DDL with `DEFAULT false` compiles without error |
| OpenAPI export | Script reads from live app + TestClient | No real DB needed; schema is static metadata; stored in `docs/openapi.json` |
| Docker validation | YAML parse + required service key check (Python stdlib only) | Validates structural correctness without running containers |

---

## Steps

### Step 1 — Install `aiosqlite`

```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend
source ../venv/bin/activate
pip install "aiosqlite>=2.0.0" --quiet
```

Add to `backend/requirements.txt` (after `asyncpg` line):
```
aiosqlite>=2.0.0
```

Expected output from pip: silent (quiet mode). Verify:
```bash
python -c "import aiosqlite; print('aiosqlite', aiosqlite.__version__)"
```
Expected output:
```
aiosqlite 0.21.0   # (any version ≥ 2.0.0 acceptable)
```

---

### Step 2 — Fix PostgreSQL-specific UUID type in all model files

Run this **single sed command** from the repo root. It replaces the PostgreSQL dialect
import with the generic `sqlalchemy.Uuid` across all 11 affected model files.

```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec
# Step 2a: Replace the import line
sed -i '' \
  's/from sqlalchemy\.dialects\.postgresql import UUID/from sqlalchemy import Uuid/g' \
  backend/app/models/base.py \
  backend/app/models/academic.py \
  backend/app/models/student.py \
  backend/app/models/staff.py \
  backend/app/models/assessment.py \
  backend/app/models/assignment.py \
  backend/app/models/attendance.py \
  backend/app/models/feedback.py \
  backend/app/models/leave.py \
  backend/app/models/notification.py \
  backend/app/models/audit.py

# Step 2b: Replace all column usages UUID(as_uuid=True) → Uuid
sed -i '' \
  's/UUID(as_uuid=True)/Uuid/g' \
  backend/app/models/base.py \
  backend/app/models/academic.py \
  backend/app/models/student.py \
  backend/app/models/staff.py \
  backend/app/models/assessment.py \
  backend/app/models/assignment.py \
  backend/app/models/attendance.py \
  backend/app/models/feedback.py \
  backend/app/models/leave.py \
  backend/app/models/notification.py \
  backend/app/models/audit.py
```

Verify no leftover occurrences:
```bash
grep -rn "dialects.postgresql.*UUID\|UUID(as_uuid" backend/app/models/ | grep -v __pycache__
```
Expected output: *(empty — zero matches)*

---

### Step 3 — Pre-flight: verify SQLite table creation

```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend
source ../venv/bin/activate
python - <<'EOF'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
import app.models  # noqa: registers all models with Base.metadata
from app.core.database import Base

async def check():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("SUCCESS — all tables created on SQLite")

asyncio.run(check())
EOF
```

Expected output:
```
SUCCESS — all tables created on SQLite
```

If this step fails with a `CompileError`, stop and investigate — it means a model still
references `UUID(as_uuid=True)` or another PostgreSQL-specific type. Fix before continuing.

---

### Step 4 — Create integration test conftest

Create `backend/tests/integration/conftest.py` with this exact content:

```python
"""Shared fixtures for integration tests using an in-memory SQLite database.

All integration tests run against SQLite+aiosqlite. This requires that all
SQLAlchemy column types use generic (non-dialect-specific) types — enforced by
the Phase 5 UUID type fix in backend/app/models/.

Fixture scoping:
  test_engine  — session scope:  one engine / one set of tables per test run
  db_session   — function scope: fresh transaction per test, rolled back after
  client       — function scope: AsyncClient with get_db overridden
  admin_user   — function scope: real User row in the test DB (admin role)
  auth_headers — function scope: Bearer token for the admin user
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


# ── Engine (session-scoped: one DB for the whole test run) ────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Override the session event loop from the root conftest."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
def session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)


# ── Session (function-scoped: rollback after each test) ───────────────────────

@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
        await session.rollback()


# ── HTTP client (function-scoped: overrides get_db with the test session) ─────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Admin user (function-scoped: created fresh per test) ─────────────────────

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        username=f"admin_{uuid.uuid4().hex[:8]}",
        email=f"admin_{uuid.uuid4().hex[:8]}@test.local",
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
```

---

### Step 5 — Create auth integration tests

Create `backend/tests/integration/test_auth_integration.py`:

```python
"""Integration tests: authentication flow."""

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
        data={"username": admin_user.username, "password": "WrongPass!"},
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": "ghost_user", "password": "any"},
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
```

---

### Step 6 — Create users integration tests

Create `backend/tests/integration/test_users_integration.py`:

```python
"""Integration tests: user management endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_list_users_as_admin(client: AsyncClient, admin_user, auth_headers: dict):
    resp = await client.get("/api/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    # Admin user we created in the fixture must appear
    usernames = [u["username"] for u in users]
    assert admin_user.username in usernames


async def test_create_user_as_admin(client: AsyncClient, auth_headers: dict):
    payload = {
        "username": "new_student_001",
        "email": "student001@test.local",
        "password": "SecurePass1!",
        "first_name": "Jane",
        "last_name": "Doe",
        "role": "student",
    }
    resp = await client.post("/api/v1/users", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "new_student_001"
    assert body["role"] == "student"


async def test_get_user_by_id(client: AsyncClient, admin_user, auth_headers: dict):
    resp = await client.get(f"/api/v1/users/{admin_user.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(admin_user.id)


async def test_get_user_not_found(client: AsyncClient, auth_headers: dict):
    import uuid
    resp = await client.get(f"/api/v1/users/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


async def test_list_users_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 401
```

---

### Step 7 — Create academic integration tests

Create `backend/tests/integration/test_academic_integration.py`:

```python
"""Integration tests: academic entity CRUD."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_create_department(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/academic/departments",
        json={"name": "Computer Science"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Computer Science"


async def test_list_departments(client: AsyncClient, auth_headers: dict):
    # Create one first
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
```

---

### Step 8 — Create leave integration tests

Create `backend/tests/integration/test_leave_integration.py`:

```python
"""Integration tests: leave request flow."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def student_user(db_session: AsyncSession) -> User:
    """A student user for leave request tests."""
    import pytest_asyncio  # noqa — import inside fixture body for clarity
    user = User(
        id=uuid.uuid4(),
        username=f"student_{uuid.uuid4().hex[:8]}",
        email=f"student_{uuid.uuid4().hex[:8]}@test.local",
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
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_apply_leave(client: AsyncClient, student_headers: dict):
    from datetime import date, timedelta
    today = date.today()
    payload = {
        "leave_type": "sick",
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=2)).isoformat(),
        "reason": "Feeling unwell",
    }
    resp = await client.post("/api/v1/leave", json=payload, headers=student_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"


async def test_get_pending_leaves_as_admin(
    client: AsyncClient,
    auth_headers: dict,
    student_headers: dict,
):
    from datetime import date, timedelta
    today = date.today()
    # Student applies for leave
    await client.post(
        "/api/v1/leave",
        json={
            "leave_type": "sick",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
            "reason": "Test leave",
        },
        headers=student_headers,
    )
    resp = await client.get("/api/v1/leave/pending", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_get_pending_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/leave/pending")
    assert resp.status_code == 401


async def test_get_leave_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/leave/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


async def test_apply_leave_unauthenticated(client: AsyncClient):
    from datetime import date
    resp = await client.post(
        "/api/v1/leave",
        json={
            "leave_type": "sick",
            "start_date": date.today().isoformat(),
            "end_date": date.today().isoformat(),
            "reason": "No token",
        },
    )
    assert resp.status_code == 401
```

> **Note on the leave test fixture**: `pytest_asyncio.fixture` must be imported at
> module level in the leave test file — add `import pytest_asyncio` at the top.

---

### Step 9 — Create OpenAPI export script

Create `backend/scripts/export_openapi.py`:

```python
"""Export the FastAPI OpenAPI schema to docs/openapi.json.

Usage (from backend/):
    python scripts/export_openapi.py

Output: backend/docs/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    # Ensure backend/ is on the path
    backend_root = Path(__file__).parent.parent
    sys.path.insert(0, str(backend_root))

    from app.main import create_app

    app = create_app()
    schema = app.openapi()

    output_path = backend_root / "docs" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2))

    endpoints = sum(len(methods) for methods in schema.get("paths", {}).values())
    print(f"OpenAPI schema exported → {output_path}")
    print(f"  paths:     {len(schema.get('paths', {}))}")
    print(f"  endpoints: {endpoints}")
    print(f"  schemas:   {len(schema.get('components', {}).get('schemas', {}))}")


if __name__ == "__main__":
    main()
```

Run it:
```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend
source ../venv/bin/activate
python scripts/export_openapi.py
```

Expected output:
```
OpenAPI schema exported → .../backend/docs/openapi.json
  paths:     45+
  endpoints: 55+
  schemas:   40+
```

---

### Step 10 — Update `.env.example`

Append these two sections to `backend/.env.example`:

```bash
# ── OpenAI (optional — enables AI quiz grading) ────────────────────────────────
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# ── SMTP (optional — enables email notifications) ──────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@school.edu
SMTP_TLS=true

# ── CORS ───────────────────────────────────────────────────────────────────────
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

---

### Step 11 — Docker file syntax validation

Run this Python snippet to validate `docker-compose.yml` and the `Dockerfile` parse
correctly without starting any containers:

```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend
python - <<'EOF'
import yaml, sys
from pathlib import Path

errors = []

# Validate docker-compose.yml
for compose_path in [
    Path("docker-compose.yml"),
    Path("docker-compose.prod.yml"),
]:
    if not compose_path.exists():
        errors.append(f"NOT FOUND: {compose_path}")
        continue
    try:
        doc = yaml.safe_load(compose_path.read_text())
        services = list(doc.get("services", {}).keys())
        print(f"OK  {compose_path} — services: {services}")
    except yaml.YAMLError as exc:
        errors.append(f"YAML ERROR in {compose_path}: {exc}")

# Validate Dockerfile exists and contains FROM
for df_path in [Path("Dockerfile"), Path("docker/Dockerfile"), Path("docker/Dockerfile.prod")]:
    if not df_path.exists():
        print(f"SKIP {df_path} — not found")
        continue
    content = df_path.read_text()
    if "FROM" in content:
        print(f"OK  {df_path} — contains FROM instruction")
    else:
        errors.append(f"WARN: {df_path} missing FROM instruction")

if errors:
    print("\nERRORS:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("\nAll Docker files validated successfully.")
EOF
```

Expected output example:
```
OK  docker-compose.yml — services: ['db', 'redis', 'api']
OK  docker-compose.prod.yml — ...
OK  docker/Dockerfile — contains FROM instruction
OK  docker/Dockerfile.prod — contains FROM instruction

All Docker files validated successfully.
```

If `docker-compose.yml` is not found, the step notes it but does NOT fail the plan —
it means Docker Compose setup is deferred to a later phase.

---

### Step 12 — Run the full test suite

```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend
source ../venv/bin/activate
python -m pytest tests/unit/ tests/integration/ -v --tb=short 2>&1 | tail -30
```

Expected summary:
```
============ N passed, 0 failed in X.XXs ============
```
where N ≥ 138 (118 unit + ~20 integration).

If any integration test fails, check:
1. Fixture `admin_user` — confirm `db_session` rollback doesn't wipe the row before the test
2. `client` fixture — confirm `dependency_overrides` are applied before the request
3. SQLite bool `server_default` — if DDL error, add `server_default=None` to affected columns

---

### Step 13 — Git commit Phase 5

```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec
git add -A
git commit -m "feat: Phase 5 — integration tests, OpenAPI export, Docker validation

- models/*: replace sqlalchemy.dialects.postgresql.UUID → sqlalchemy.Uuid
  (non-breaking; enables cross-DB compatibility for integration tests)
- tests/integration/conftest.py: SQLite in-memory fixtures (engine, session, client,
  admin_user, auth_headers); rollback-per-test isolation
- tests/integration/test_auth_integration.py: 6 tests (login, wrong-pw, unknown,
  /auth/me, /auth/me unauth, refresh)
- tests/integration/test_users_integration.py: 5 tests (list, create, get-by-id,
  404, unauth)
- tests/integration/test_academic_integration.py: 5 tests (create dept, list,
  get-by-id, 404, unauth)
- tests/integration/test_leave_integration.py: 5 tests (apply, pending as admin,
  pending unauth, leave not found, apply unauth)
- scripts/export_openapi.py: exports OpenAPI schema → docs/openapi.json
- docs/openapi.json: generated schema (45+ paths, 55+ endpoints)
- requirements.txt: add aiosqlite>=2.0.0
- .env.example: add OPENAI and SMTP sections with documentation comments
- 138+ tests passing"
```

---

## Acceptance Criteria

All items must be verifiable by running the command shown.

- [ ] **UUID fix applied:** `grep -rn "dialects.postgresql.*UUID" backend/app/models/ | grep -v __pycache__` → empty
- [ ] **aiosqlite installed:** `python -c "import aiosqlite"` → no error
- [ ] **SQLite tables created:** pre-flight script (Step 3) prints `SUCCESS — all tables created on SQLite`
- [ ] **Integration conftest exists:** `[ -f backend/tests/integration/conftest.py ] && echo ok`
- [ ] **4 integration test files exist:** all 4 `test_*_integration.py` files present
- [ ] **Unit tests still pass:** `python -m pytest tests/unit/ -q` → `118 passed`
- [ ] **Integration tests pass:** `python -m pytest tests/integration/ -q` → `20 passed, 0 failed`
- [ ] **Total tests:** `python -m pytest tests/unit/ tests/integration/ -q` → `138+ passed, 0 failed`
- [ ] **OpenAPI exported:** `[ -f backend/docs/openapi.json ] && python -c "import json; d=json.load(open('backend/docs/openapi.json')); print(len(d['paths']), 'paths')"` → `45+ paths`
- [ ] **Docker validation:** Step 11 script exits 0
- [ ] **Git commit:** `git log --oneline -1` shows Phase 5 commit

---

## Rollback

To undo Phase 5 completely:
```bash
git revert HEAD --no-edit
# OR (hard reset — discards commit entirely):
git reset --hard HEAD~1
pip uninstall aiosqlite -y
```

The UUID type change is backwards-compatible with PostgreSQL — no rollback needed
for that alone. However, the git revert covers all changes atomically.
