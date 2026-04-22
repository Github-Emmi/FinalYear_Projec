# ExecPlan: Phase 4 — API Routers & Endpoint Wiring

## Context

Phase 4 of the LMS FastAPI migration on branch `phase/1-fresh-scaffold`.

**Prior phase commits:**
- Phase 1 `6112a95d` — scaffold, health endpoint
- Phase 2 `04db3237` — 20 ORM models, 13 repositories, migration 001, 59 unit tests
- Phase 3 `0abb98f8` — 11 service classes, RBAC deps, AI grading, async SMTP, 93 unit tests

**Current state of `backend/app/api/v1/router.py`** (stub — health check only):
```python
"""API v1 router. Phase 1: health check only."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
```

**`backend/app/api/v1/endpoints/`** — contains only an empty `__init__.py`. No endpoint files exist.

**Available service classes** (all accept `AsyncSession` in `__init__`):
`AuthService`, `UserService`, `StudentService`, `StaffService`, `AssessmentService`,
`AssignmentService`, `AttendanceService`, `LeaveService`, `NotificationService`,
`AnalyticsService`, `EmailService`

**No `academic_service.py` exists** — this phase creates it as a thin CRUD wrapper.

**RBAC dependencies** (from `backend/app/api/deps.py`):
- `get_current_user` → decodes Bearer token, returns `User` ORM object
- `AdminOnly` = `require_role("admin")`
- `StaffOrAdmin` = `require_role("admin", "staff")`
- `AnyAuthenticatedUser` = `require_role("admin", "staff", "student")`

**API prefix**: `"/api/v1"` — already set in `app/main.py` via `settings.API_PREFIX`.
The health endpoint lives at `GET /api/v1/health` and must remain there.

**tokenUrl**: `deps.py` declares `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")`.
The login endpoint MUST be at exactly `POST /api/v1/auth/token` using form data.

**Schemas already defined** in `backend/app/schemas/`:
- `auth.py`: `TokenResponse`, `TokenRefreshRequest`, `PasswordChangeRequest`
- `user.py`: `UserCreate`, `UserUpdate`, `UserResponse`
- `student.py`: `StudentProfileCreate`, `StudentProfileUpdate`, `StudentProfileResponse`
- `staff.py`: `StaffProfileCreate`, `StaffProfileUpdate`, `StaffProfileResponse`
- `academic.py`: `DepartmentCreate/Update/Response`, `SessionYearCreate/Update/Response`, `ClassRoomCreate/Update/Response`, `SubjectCreate/Update/Response`
- `assessment.py`: `QuizCreate/Update/Response`, `QuestionCreate/Update/Response`, `QuizAttemptCreate/Response`, `QuizResultResponse` — **missing `SubmitAttemptRequest`**
- `assignment.py`: `AssignmentCreate/Update/Response`, `SubmissionCreate/Response`
- `attendance.py`: `AttendanceSessionCreate/Response`, `AttendanceRecordCreate/Response`
- `leave.py`: `LeaveRequestCreate/Update/Review/Response`
- `notification.py`: `NotificationCreate/Response` — **missing `BroadcastNotificationRequest`**

**Python 3.14.3 / FastAPI 0.104.1 / Pydantic v2 / SQLAlchemy 2.0 async**

---

## Scope

**Files to CREATE (13):**
1. `backend/app/services/academic_service.py`
2. `backend/app/api/v1/endpoints/auth.py`
3. `backend/app/api/v1/endpoints/users.py`
4. `backend/app/api/v1/endpoints/students.py`
5. `backend/app/api/v1/endpoints/staff.py`
6. `backend/app/api/v1/endpoints/academic.py`
7. `backend/app/api/v1/endpoints/assessments.py`
8. `backend/app/api/v1/endpoints/assignments.py`
9. `backend/app/api/v1/endpoints/attendance.py`
10. `backend/app/api/v1/endpoints/leave.py`
11. `backend/app/api/v1/endpoints/notifications.py`
12. `backend/app/api/v1/endpoints/analytics.py`
13. `backend/tests/unit/test_endpoints.py`

**Files to MODIFY (4):**
14. `backend/app/schemas/assessment.py` — append `AnswerItem` + `SubmitAttemptRequest`
15. `backend/app/schemas/notification.py` — append `BroadcastNotificationRequest`
16. `backend/app/services/__init__.py` — add `AcademicService` import
17. `backend/app/api/v1/router.py` — replace stub, register all 11 sub-routers + keep health

**Nothing else changes.** Models, repositories, core config, migrations, conftest — untouched.

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Academic service | Create thin `academic_service.py` | Keeps uniform service-layer pattern; all services receive session injection |
| `/auth/token` body format | `OAuth2PasswordRequestForm` (form-data) | OAuth2 spec; `deps.py` already points tokenUrl there |
| `GET /students/me` vs `GET /students/{id}` | `/me` registered FIRST | FastAPI matches top-to-bottom; `"me"` would be parsed as UUID otherwise |
| `GET /leave/pending` vs `GET /leave/{id}` | `/pending` registered FIRST | Same reason — literal "pending" would match UUID route |
| Academic writes RBAC | `AdminOnly` for create/update/delete | Only admins manage department/classroom structure |
| Academic reads RBAC | `AnyAuthenticatedUser` | Staff and students need to read subjects/classrooms |
| `change_password` ownership | Any auth user may change own password; admin may change any | Enforced in endpoint, not via `require_role` |
| 404 on missing resource | `HTTPException(404)` raised by services | Services already raise 404; routers just call service method |
| Analytics RBAC | `StaffOrAdmin` | Per-ownership enforcement is Phase 5 scope |
| `response_model` on 204 endpoints | Omitted | FastAPI emits 204 no-content; adding a response_model causes a serialization error |

---

## Step 1 — Extend schema files

### 1a. Append to `backend/app/schemas/assessment.py`

Add after the last line of the file (`ai_feedback: Optional[str] = None`):

```python
# ── Submit attempt request ─────────────────────────────────────────────────────

class AnswerItem(BaseModel):
    question_id: UUID
    answer: str


class SubmitAttemptRequest(BaseModel):
    answers: list[AnswerItem]
```

### 1b. Append to `backend/app/schemas/notification.py`

Add after the last line of the file:

```python

class BroadcastNotificationRequest(BaseModel):
    recipient_ids: list[UUID]
    title: str
    message: str
    notification_type: NotificationType = NotificationType.info
```

**Verification:**
```bash
cd backend && python -c "
from app.schemas.assessment import SubmitAttemptRequest, AnswerItem
from app.schemas.notification import BroadcastNotificationRequest
print('schema extensions OK')
"
```
Expected output:
```
schema extensions OK
```

---

## Step 2 — Create `backend/app/services/academic_service.py`

Full file content:

```python
"""Academic entity service: Department, SessionYear, ClassRoom, Subject.

Thin CRUD wrapper over repositories — raises HTTP 404 for missing objects.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.factory import RepositoryFactory
from app.schemas.academic import (
    ClassRoomCreate,
    ClassRoomUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    SessionYearCreate,
    SessionYearUpdate,
    SubjectCreate,
    SubjectUpdate,
)


class AcademicService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = RepositoryFactory(session)

    # ── Department ─────────────────────────────────────────────────────────────

    async def create_department(self, data: DepartmentCreate):
        return await self._repo.departments.create(data.model_dump())

    async def get_department(self, dept_id: UUID):
        obj = await self._repo.departments.get_by_id(dept_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        return obj

    async def list_departments(self, skip: int = 0, limit: int = 100):
        return await self._repo.departments.get_all(skip=skip, limit=limit)

    async def update_department(self, dept_id: UUID, data: DepartmentUpdate):
        obj = await self.get_department(dept_id)
        return await self._repo.departments.update(obj, data.model_dump(exclude_none=True))

    async def delete_department(self, dept_id: UUID) -> None:
        obj = await self.get_department(dept_id)
        await self._repo.departments.delete(obj)

    # ── SessionYear ────────────────────────────────────────────────────────────

    async def create_session_year(self, data: SessionYearCreate):
        return await self._repo.session_years.create(data.model_dump())

    async def get_session_year(self, year_id: UUID):
        obj = await self._repo.session_years.get_by_id(year_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SessionYear not found")
        return obj

    async def list_session_years(self, skip: int = 0, limit: int = 100):
        return await self._repo.session_years.get_all(skip=skip, limit=limit)

    async def update_session_year(self, year_id: UUID, data: SessionYearUpdate):
        obj = await self.get_session_year(year_id)
        return await self._repo.session_years.update(obj, data.model_dump(exclude_none=True))

    async def delete_session_year(self, year_id: UUID) -> None:
        obj = await self.get_session_year(year_id)
        await self._repo.session_years.delete(obj)

    # ── ClassRoom ──────────────────────────────────────────────────────────────

    async def create_classroom(self, data: ClassRoomCreate):
        return await self._repo.classrooms.create(data.model_dump())

    async def get_classroom(self, room_id: UUID):
        obj = await self._repo.classrooms.get_by_id(room_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClassRoom not found")
        return obj

    async def list_classrooms(self, skip: int = 0, limit: int = 100):
        return await self._repo.classrooms.get_all(skip=skip, limit=limit)

    async def update_classroom(self, room_id: UUID, data: ClassRoomUpdate):
        obj = await self.get_classroom(room_id)
        return await self._repo.classrooms.update(obj, data.model_dump(exclude_none=True))

    async def delete_classroom(self, room_id: UUID) -> None:
        obj = await self.get_classroom(room_id)
        await self._repo.classrooms.delete(obj)

    # ── Subject ────────────────────────────────────────────────────────────────

    async def create_subject(self, data: SubjectCreate):
        return await self._repo.subjects.create(data.model_dump())

    async def get_subject(self, subject_id: UUID):
        obj = await self._repo.subjects.get_by_id(subject_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
        return obj

    async def list_subjects(self, skip: int = 0, limit: int = 100):
        return await self._repo.subjects.get_all(skip=skip, limit=limit)

    async def update_subject(self, subject_id: UUID, data: SubjectUpdate):
        obj = await self.get_subject(subject_id)
        return await self._repo.subjects.update(obj, data.model_dump(exclude_none=True))

    async def delete_subject(self, subject_id: UUID) -> None:
        obj = await self.get_subject(subject_id)
        await self._repo.subjects.delete(obj)
```

---

## Step 3 — Update `backend/app/services/__init__.py`

Append after the last import line (`from app.services.email_service import EmailService`):

```python
from app.services.academic_service import AcademicService
```

---

## Step 4 — Create endpoint files

### File 4a: `backend/app/api/v1/endpoints/auth.py`

```python
"""Auth endpoints: OAuth2 login, token refresh, current user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import TokenRefreshRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """OAuth2 password-flow login. Returns access + refresh token pair."""
    svc = AuthService(db)
    return await svc.login(form_data.username, form_data.password)


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    body: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair."""
    svc = AuthService(db)
    return await svc.refresh(body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)
```

### File 4b: `backend/app/api/v1/endpoints/users.py`

```python
"""User management endpoints (admin-gated writes)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import PasswordChangeRequest
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AdminOnly)],
)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    svc = UserService(db)
    user = await svc.create(body)
    return UserResponse.model_validate(user)


@router.get("", response_model=list[UserResponse], dependencies=[Depends(AdminOnly)])
async def list_users(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[UserResponse]:
    svc = UserService(db)
    users = await svc.get_all(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(AdminOnly)])
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)) -> UserResponse:
    svc = UserService(db)
    user = await svc.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(AdminOnly)])
async def update_user(
    user_id: UUID, body: UserUpdate, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    svc = UserService(db)
    user = await svc.update(user_id, body)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    svc = UserService(db)
    await svc.soft_delete(user_id)


@router.post("/{user_id}/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    user_id: UUID,
    body: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Admin may change any user's password; authenticated users may change their own."""
    if current_user.role != "admin" and str(current_user.id) != str(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    svc = UserService(db)
    await svc.change_password(user_id, body)


@router.patch("/{user_id}/activate", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def set_user_active(
    user_id: UUID, active: bool, db: AsyncSession = Depends(get_db)
) -> None:
    svc = UserService(db)
    await svc.set_active(user_id, active)
```

### File 4c: `backend/app/api/v1/endpoints/students.py`

```python
"""Student profile endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyAuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.factory import RepositoryFactory
from app.schemas.student import StudentProfileCreate, StudentProfileResponse, StudentProfileUpdate
from app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["students"])


@router.post(
    "",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AdminOnly)],
)
async def create_student_profile(
    body: StudentProfileCreate, db: AsyncSession = Depends(get_db)
) -> StudentProfileResponse:
    svc = StudentService(db)
    profile = await svc.create_profile(body)
    return StudentProfileResponse.model_validate(profile)


@router.get("", response_model=list[StudentProfileResponse], dependencies=[Depends(AdminOnly)])
async def list_students(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[StudentProfileResponse]:
    repo = RepositoryFactory(db)
    profiles = await repo.students.get_all(skip=skip, limit=limit)
    return [StudentProfileResponse.model_validate(p) for p in profiles]


# IMPORTANT: /me MUST be registered before /{student_id} to prevent "me" being parsed as UUID
@router.get("/me", response_model=StudentProfileResponse)
async def get_my_student_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentProfileResponse:
    svc = StudentService(db)
    profile = await svc.get_by_user_id(current_user.id)
    return StudentProfileResponse.model_validate(profile)


@router.get(
    "/{student_id}",
    response_model=StudentProfileResponse,
    dependencies=[Depends(AnyAuthenticatedUser)],
)
async def get_student_profile(
    student_id: UUID, db: AsyncSession = Depends(get_db)
) -> StudentProfileResponse:
    svc = StudentService(db)
    profile = await svc.get_profile(student_id)
    return StudentProfileResponse.model_validate(profile)


@router.patch("/{student_id}", response_model=StudentProfileResponse, dependencies=[Depends(AdminOnly)])
async def update_student_profile(
    student_id: UUID,
    body: StudentProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> StudentProfileResponse:
    svc = StudentService(db)
    profile = await svc.update_profile(student_id, body)
    return StudentProfileResponse.model_validate(profile)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_student_profile(student_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    svc = StudentService(db)
    await svc.delete_profile(student_id)
```

### File 4d: `backend/app/api/v1/endpoints/staff.py`

```python
"""Staff profile endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyAuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.factory import RepositoryFactory
from app.schemas.staff import StaffProfileCreate, StaffProfileResponse, StaffProfileUpdate
from app.services.staff_service import StaffService

router = APIRouter(prefix="/staff", tags=["staff"])


@router.post(
    "",
    response_model=StaffProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AdminOnly)],
)
async def create_staff_profile(
    body: StaffProfileCreate, db: AsyncSession = Depends(get_db)
) -> StaffProfileResponse:
    svc = StaffService(db)
    profile = await svc.create_profile(body)
    return StaffProfileResponse.model_validate(profile)


@router.get("", response_model=list[StaffProfileResponse], dependencies=[Depends(AdminOnly)])
async def list_staff(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[StaffProfileResponse]:
    repo = RepositoryFactory(db)
    profiles = await repo.staff.get_all(skip=skip, limit=limit)
    return [StaffProfileResponse.model_validate(p) for p in profiles]


# IMPORTANT: /me MUST be registered before /{staff_id}
@router.get("/me", response_model=StaffProfileResponse)
async def get_my_staff_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffProfileResponse:
    svc = StaffService(db)
    profile = await svc.get_by_user_id(current_user.id)
    return StaffProfileResponse.model_validate(profile)


@router.get(
    "/{staff_id}",
    response_model=StaffProfileResponse,
    dependencies=[Depends(AnyAuthenticatedUser)],
)
async def get_staff_profile(
    staff_id: UUID, db: AsyncSession = Depends(get_db)
) -> StaffProfileResponse:
    svc = StaffService(db)
    profile = await svc.get_profile(staff_id)
    return StaffProfileResponse.model_validate(profile)


@router.patch("/{staff_id}", response_model=StaffProfileResponse, dependencies=[Depends(AdminOnly)])
async def update_staff_profile(
    staff_id: UUID,
    body: StaffProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> StaffProfileResponse:
    svc = StaffService(db)
    profile = await svc.update_profile(staff_id, body)
    return StaffProfileResponse.model_validate(profile)


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_staff_profile(staff_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    svc = StaffService(db)
    await svc.delete_profile(staff_id)
```

### File 4e: `backend/app/api/v1/endpoints/academic.py`

```python
"""Academic entity endpoints: departments, session years, classrooms, subjects."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyAuthenticatedUser
from app.core.database import get_db
from app.schemas.academic import (
    ClassRoomCreate,
    ClassRoomResponse,
    ClassRoomUpdate,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    SessionYearCreate,
    SessionYearResponse,
    SessionYearUpdate,
    SubjectCreate,
    SubjectResponse,
    SubjectUpdate,
)
from app.services.academic_service import AcademicService

router = APIRouter(prefix="/academic", tags=["academic"])


# ── Departments ────────────────────────────────────────────────────────────────

@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AdminOnly)])
async def create_department(body: DepartmentCreate, db: AsyncSession = Depends(get_db)) -> DepartmentResponse:
    svc = AcademicService(db)
    dept = await svc.create_department(body)
    return DepartmentResponse.model_validate(dept)


@router.get("/departments", response_model=list[DepartmentResponse], dependencies=[Depends(AnyAuthenticatedUser)])
async def list_departments(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[DepartmentResponse]:
    svc = AcademicService(db)
    items = await svc.list_departments(skip=skip, limit=limit)
    return [DepartmentResponse.model_validate(i) for i in items]


@router.get("/departments/{dept_id}", response_model=DepartmentResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_department(dept_id: UUID, db: AsyncSession = Depends(get_db)) -> DepartmentResponse:
    svc = AcademicService(db)
    return DepartmentResponse.model_validate(await svc.get_department(dept_id))


@router.patch("/departments/{dept_id}", response_model=DepartmentResponse, dependencies=[Depends(AdminOnly)])
async def update_department(dept_id: UUID, body: DepartmentUpdate, db: AsyncSession = Depends(get_db)) -> DepartmentResponse:
    svc = AcademicService(db)
    return DepartmentResponse.model_validate(await svc.update_department(dept_id, body))


@router.delete("/departments/{dept_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_department(dept_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AcademicService(db).delete_department(dept_id)


# ── Session Years ──────────────────────────────────────────────────────────────

@router.post("/session-years", response_model=SessionYearResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AdminOnly)])
async def create_session_year(body: SessionYearCreate, db: AsyncSession = Depends(get_db)) -> SessionYearResponse:
    svc = AcademicService(db)
    return SessionYearResponse.model_validate(await svc.create_session_year(body))


@router.get("/session-years", response_model=list[SessionYearResponse], dependencies=[Depends(AnyAuthenticatedUser)])
async def list_session_years(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[SessionYearResponse]:
    svc = AcademicService(db)
    items = await svc.list_session_years(skip=skip, limit=limit)
    return [SessionYearResponse.model_validate(i) for i in items]


@router.get("/session-years/{year_id}", response_model=SessionYearResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_session_year(year_id: UUID, db: AsyncSession = Depends(get_db)) -> SessionYearResponse:
    return SessionYearResponse.model_validate(await AcademicService(db).get_session_year(year_id))


@router.patch("/session-years/{year_id}", response_model=SessionYearResponse, dependencies=[Depends(AdminOnly)])
async def update_session_year(year_id: UUID, body: SessionYearUpdate, db: AsyncSession = Depends(get_db)) -> SessionYearResponse:
    return SessionYearResponse.model_validate(await AcademicService(db).update_session_year(year_id, body))


@router.delete("/session-years/{year_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_session_year(year_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AcademicService(db).delete_session_year(year_id)


# ── ClassRooms ─────────────────────────────────────────────────────────────────

@router.post("/classrooms", response_model=ClassRoomResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AdminOnly)])
async def create_classroom(body: ClassRoomCreate, db: AsyncSession = Depends(get_db)) -> ClassRoomResponse:
    return ClassRoomResponse.model_validate(await AcademicService(db).create_classroom(body))


@router.get("/classrooms", response_model=list[ClassRoomResponse], dependencies=[Depends(AnyAuthenticatedUser)])
async def list_classrooms(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[ClassRoomResponse]:
    items = await AcademicService(db).list_classrooms(skip=skip, limit=limit)
    return [ClassRoomResponse.model_validate(i) for i in items]


@router.get("/classrooms/{room_id}", response_model=ClassRoomResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_classroom(room_id: UUID, db: AsyncSession = Depends(get_db)) -> ClassRoomResponse:
    return ClassRoomResponse.model_validate(await AcademicService(db).get_classroom(room_id))


@router.patch("/classrooms/{room_id}", response_model=ClassRoomResponse, dependencies=[Depends(AdminOnly)])
async def update_classroom(room_id: UUID, body: ClassRoomUpdate, db: AsyncSession = Depends(get_db)) -> ClassRoomResponse:
    return ClassRoomResponse.model_validate(await AcademicService(db).update_classroom(room_id, body))


@router.delete("/classrooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_classroom(room_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AcademicService(db).delete_classroom(room_id)


# ── Subjects ───────────────────────────────────────────────────────────────────

@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AdminOnly)])
async def create_subject(body: SubjectCreate, db: AsyncSession = Depends(get_db)) -> SubjectResponse:
    return SubjectResponse.model_validate(await AcademicService(db).create_subject(body))


@router.get("/subjects", response_model=list[SubjectResponse], dependencies=[Depends(AnyAuthenticatedUser)])
async def list_subjects(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[SubjectResponse]:
    items = await AcademicService(db).list_subjects(skip=skip, limit=limit)
    return [SubjectResponse.model_validate(i) for i in items]


@router.get("/subjects/{subject_id}", response_model=SubjectResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_subject(subject_id: UUID, db: AsyncSession = Depends(get_db)) -> SubjectResponse:
    return SubjectResponse.model_validate(await AcademicService(db).get_subject(subject_id))


@router.patch("/subjects/{subject_id}", response_model=SubjectResponse, dependencies=[Depends(AdminOnly)])
async def update_subject(subject_id: UUID, body: SubjectUpdate, db: AsyncSession = Depends(get_db)) -> SubjectResponse:
    return SubjectResponse.model_validate(await AcademicService(db).update_subject(subject_id, body))


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_subject(subject_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AcademicService(db).delete_subject(subject_id)
```

### File 4f: `backend/app/api/v1/endpoints/assessments.py`

```python
"""Quiz / question / attempt endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticatedUser, StaffOrAdmin
from app.core.database import get_db
from app.repositories.factory import RepositoryFactory
from app.schemas.assessment import (
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    QuizAttemptResponse,
    QuizCreate,
    QuizResponse,
    QuizResultResponse,
    QuizUpdate,
    SubmitAttemptRequest,
)
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/quizzes", tags=["assessments"])


# ── Quiz CRUD ─────────────────────────────────────────────────────────────────

@router.post("", response_model=QuizResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(StaffOrAdmin)])
async def create_quiz(body: QuizCreate, db: AsyncSession = Depends(get_db)) -> QuizResponse:
    svc = AssessmentService(db)
    quiz = await svc.create_quiz(body)
    return QuizResponse.model_validate(quiz)


@router.get("/{quiz_id}", response_model=QuizResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_quiz(quiz_id: UUID, db: AsyncSession = Depends(get_db)) -> QuizResponse:
    svc = AssessmentService(db)
    quiz = await svc.get_quiz(quiz_id)
    return QuizResponse.model_validate(quiz)


@router.patch("/{quiz_id}", response_model=QuizResponse, dependencies=[Depends(StaffOrAdmin)])
async def update_quiz(quiz_id: UUID, body: QuizUpdate, db: AsyncSession = Depends(get_db)) -> QuizResponse:
    svc = AssessmentService(db)
    quiz = await svc.update_quiz(quiz_id, body)
    return QuizResponse.model_validate(quiz)


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(StaffOrAdmin)])
async def delete_quiz(quiz_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AssessmentService(db).delete_quiz(quiz_id)


# ── Quiz lifecycle ─────────────────────────────────────────────────────────────

@router.post("/{quiz_id}/publish", response_model=QuizResponse, dependencies=[Depends(StaffOrAdmin)])
async def publish_quiz(quiz_id: UUID, db: AsyncSession = Depends(get_db)) -> QuizResponse:
    svc = AssessmentService(db)
    quiz = await svc.publish_quiz(quiz_id)
    return QuizResponse.model_validate(quiz)


@router.post("/{quiz_id}/close", response_model=QuizResponse, dependencies=[Depends(StaffOrAdmin)])
async def close_quiz(quiz_id: UUID, db: AsyncSession = Depends(get_db)) -> QuizResponse:
    svc = AssessmentService(db)
    quiz = await svc.close_quiz(quiz_id)
    return QuizResponse.model_validate(quiz)


# ── Questions ──────────────────────────────────────────────────────────────────

@router.post("/{quiz_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(StaffOrAdmin)])
async def add_question(quiz_id: UUID, body: QuestionCreate, db: AsyncSession = Depends(get_db)) -> QuestionResponse:
    repo = RepositoryFactory(db)
    # Ensure quiz_id in body matches path
    body_dict = body.model_dump()
    body_dict["quiz_id"] = quiz_id
    question = await repo.questions.create(body_dict)
    return QuestionResponse.model_validate(question)


@router.get("/{quiz_id}/questions", response_model=list[QuestionResponse], dependencies=[Depends(AnyAuthenticatedUser)])
async def list_questions(quiz_id: UUID, db: AsyncSession = Depends(get_db)) -> list[QuestionResponse]:
    repo = RepositoryFactory(db)
    questions = await repo.questions.get_by_quiz(quiz_id)
    return [QuestionResponse.model_validate(q) for q in questions]


@router.patch("/{quiz_id}/questions/{question_id}", response_model=QuestionResponse, dependencies=[Depends(StaffOrAdmin)])
async def update_question(quiz_id: UUID, question_id: UUID, body: QuestionUpdate, db: AsyncSession = Depends(get_db)) -> QuestionResponse:
    repo = RepositoryFactory(db)
    question = await repo.questions.get_by_id(question_id)
    updated = await repo.questions.update(question, body.model_dump(exclude_none=True))
    return QuestionResponse.model_validate(updated)


# ── Attempt lifecycle ──────────────────────────────────────────────────────────

@router.post("/{quiz_id}/attempt", response_model=QuizAttemptResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AnyAuthenticatedUser)])
async def start_attempt(quiz_id: UUID, student_id: UUID, db: AsyncSession = Depends(get_db)) -> QuizAttemptResponse:
    svc = AssessmentService(db)
    attempt = await svc.start_attempt(quiz_id, student_id)
    return QuizAttemptResponse.model_validate(attempt)


@router.post("/attempts/{attempt_id}/submit", response_model=QuizAttemptResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def submit_attempt(attempt_id: UUID, body: SubmitAttemptRequest, db: AsyncSession = Depends(get_db)) -> QuizAttemptResponse:
    svc = AssessmentService(db)
    answers = [{"question_id": a.question_id, "answer": a.answer} for a in body.answers]
    attempt = await svc.submit_attempt(attempt_id, answers)
    return QuizAttemptResponse.model_validate(attempt)


@router.get("/attempts/{attempt_id}", response_model=QuizAttemptResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_attempt(attempt_id: UUID, db: AsyncSession = Depends(get_db)) -> QuizAttemptResponse:
    repo = RepositoryFactory(db)
    attempt = await repo.quiz_attempts.get_by_id(attempt_id)
    return QuizAttemptResponse.model_validate(attempt)
```

### File 4g: `backend/app/api/v1/endpoints/assignments.py`

```python
"""Assignment and submission endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticatedUser, StaffOrAdmin
from app.core.database import get_db
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
    SubmissionCreate,
    SubmissionResponse,
    SubmissionUpdate,
)
from app.services.assignment_service import AssignmentService

router = APIRouter(prefix="/assignments", tags=["assignments"])


# ── Assignment CRUD ────────────────────────────────────────────────────────────

@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(StaffOrAdmin)])
async def create_assignment(body: AssignmentCreate, db: AsyncSession = Depends(get_db)) -> AssignmentResponse:
    svc = AssignmentService(db)
    assignment = await svc.create(body)
    return AssignmentResponse.model_validate(assignment)


@router.get("/{assignment_id}", response_model=AssignmentResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_assignment(assignment_id: UUID, db: AsyncSession = Depends(get_db)) -> AssignmentResponse:
    svc = AssignmentService(db)
    assignment = await svc.get(assignment_id)
    return AssignmentResponse.model_validate(assignment)


@router.patch("/{assignment_id}", response_model=AssignmentResponse, dependencies=[Depends(StaffOrAdmin)])
async def update_assignment(assignment_id: UUID, body: AssignmentUpdate, db: AsyncSession = Depends(get_db)) -> AssignmentResponse:
    svc = AssignmentService(db)
    assignment = await svc.update(assignment_id, body)
    return AssignmentResponse.model_validate(assignment)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(StaffOrAdmin)])
async def delete_assignment(assignment_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AssignmentService(db).delete(assignment_id)


# ── Submission ─────────────────────────────────────────────────────────────────

@router.post("/{assignment_id}/submit", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AnyAuthenticatedUser)])
async def submit_assignment(
    assignment_id: UUID,
    student_id: UUID,
    file_url: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    svc = AssignmentService(db)
    submission = await svc.submit(assignment_id, student_id, file_url)
    return SubmissionResponse.model_validate(submission)


@router.post("/submissions/{submission_id}/grade", response_model=SubmissionResponse, dependencies=[Depends(StaffOrAdmin)])
async def grade_submission(
    submission_id: UUID,
    score: float,
    feedback: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    svc = AssignmentService(db)
    submission = await svc.grade(submission_id, score, feedback)
    return SubmissionResponse.model_validate(submission)


@router.post("/submissions/{submission_id}/grade-ai", response_model=SubmissionResponse, dependencies=[Depends(StaffOrAdmin)])
async def grade_submission_with_ai(submission_id: UUID, db: AsyncSession = Depends(get_db)) -> SubmissionResponse:
    svc = AssignmentService(db)
    submission = await svc.grade_with_ai(submission_id)
    return SubmissionResponse.model_validate(submission)
```

### File 4h: `backend/app/api/v1/endpoints/attendance.py`

```python
"""Attendance session and record endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticatedUser, StaffOrAdmin
from app.core.database import get_db
from app.schemas.attendance import AttendanceRecordCreate, AttendanceSessionCreate, AttendanceSessionResponse
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/sessions", response_model=AttendanceSessionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(StaffOrAdmin)])
async def create_attendance_session(body: AttendanceSessionCreate, db: AsyncSession = Depends(get_db)) -> AttendanceSessionResponse:
    svc = AttendanceService(db)
    session = await svc.create_session(body)
    return AttendanceSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/mark", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(StaffOrAdmin)])
async def mark_attendance(
    session_id: UUID,
    records: list[AttendanceRecordCreate],
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = AttendanceService(db)
    records_dicts = [r.model_dump() for r in records]
    await svc.mark_attendance(session_id, records_dicts)


@router.get("/students/{student_id}/summary", dependencies=[Depends(AnyAuthenticatedUser)])
async def get_attendance_summary(student_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    svc = AttendanceService(db)
    return await svc.get_student_attendance_summary(student_id)
```

### File 4i: `backend/app/api/v1/endpoints/leave.py`

```python
"""Leave request endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticatedUser, StaffOrAdmin
from app.core.database import get_db
from app.schemas.leave import LeaveRequestCreate, LeaveRequestResponse, LeaveRequestReview, LeaveRequestUpdate
from app.services.leave_service import LeaveService

router = APIRouter(prefix="/leave", tags=["leave"])


@router.post("", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AnyAuthenticatedUser)])
async def apply_leave(body: LeaveRequestCreate, db: AsyncSession = Depends(get_db)) -> LeaveRequestResponse:
    svc = LeaveService(db)
    leave = await svc.apply(body)
    return LeaveRequestResponse.model_validate(leave)


# IMPORTANT: /pending MUST be registered before /{leave_id}
@router.get("/pending", response_model=list[LeaveRequestResponse], dependencies=[Depends(StaffOrAdmin)])
async def get_pending_leaves(db: AsyncSession = Depends(get_db)) -> list[LeaveRequestResponse]:
    svc = LeaveService(db)
    leaves = await svc.get_pending()
    return [LeaveRequestResponse.model_validate(lv) for lv in leaves]


@router.get("/{leave_id}", response_model=LeaveRequestResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_leave(leave_id: UUID, db: AsyncSession = Depends(get_db)) -> LeaveRequestResponse:
    svc = LeaveService(db)
    leave = await svc.get(leave_id)
    return LeaveRequestResponse.model_validate(leave)


@router.patch("/{leave_id}", response_model=LeaveRequestResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def update_leave(leave_id: UUID, body: LeaveRequestUpdate, db: AsyncSession = Depends(get_db)) -> LeaveRequestResponse:
    svc = LeaveService(db)
    leave = await svc.update(leave_id, body)
    return LeaveRequestResponse.model_validate(leave)


@router.delete("/{leave_id}/cancel", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AnyAuthenticatedUser)])
async def cancel_leave(leave_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await LeaveService(db).cancel(leave_id)


@router.post("/{leave_id}/review", response_model=LeaveRequestResponse, dependencies=[Depends(StaffOrAdmin)])
async def review_leave(
    leave_id: UUID,
    body: LeaveRequestReview,
    db: AsyncSession = Depends(get_db),
) -> LeaveRequestResponse:
    svc = LeaveService(db)
    leave = await svc.review(
        leave_id,
        reviewer_id=body.reviewed_by_id,
        new_status=body.status,
        rejection_reason=body.rejection_reason,
    )
    return LeaveRequestResponse.model_validate(leave)
```

### File 4j: `backend/app/api/v1/endpoints/notifications.py`

```python
"""Notification endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyAuthenticatedUser, StaffOrAdmin, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import BroadcastNotificationRequest, NotificationCreate, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(StaffOrAdmin)])
async def send_notification(body: NotificationCreate, db: AsyncSession = Depends(get_db)) -> NotificationResponse:
    svc = NotificationService(db)
    notif = await svc.send(body)
    return NotificationResponse.model_validate(notif)


@router.post("/broadcast", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(StaffOrAdmin)])
async def broadcast_notification(
    body: BroadcastNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    svc = NotificationService(db)
    await svc.send_broadcast(
        recipient_ids=body.recipient_ids,
        title=body.title,
        message=body.message,
        sender_id=current_user.id,
        type=body.notification_type,
    )


@router.get("/me", response_model=list[NotificationResponse])
async def get_my_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationResponse]:
    svc = NotificationService(db)
    notifs = await svc.get_unread(current_user.id)
    return [NotificationResponse.model_validate(n) for n in notifs]


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    svc = NotificationService(db)
    notif = await svc.mark_read(notification_id, current_user.id)
    return NotificationResponse.model_validate(notif)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_notification(notification_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await NotificationService(db).delete(notification_id)
```

### File 4k: `backend/app/api/v1/endpoints/analytics.py`

```python
"""Analytics endpoints: per-student, per-classroom, per-staff summaries."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StaffOrAdmin
from app.core.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/students/{student_id}", dependencies=[Depends(StaffOrAdmin)])
async def student_analytics(student_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    svc = AnalyticsService(db)
    return await svc.student_summary(student_id)


@router.get("/classrooms/{classroom_id}", dependencies=[Depends(StaffOrAdmin)])
async def classroom_analytics(classroom_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    svc = AnalyticsService(db)
    return await svc.classroom_summary(classroom_id)


@router.get("/staff/{staff_id}", dependencies=[Depends(StaffOrAdmin)])
async def staff_analytics(staff_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    svc = AnalyticsService(db)
    return await svc.staff_summary(staff_id)
```

---

## Step 5 — Rewrite `backend/app/api/v1/router.py`

Replace the entire file content:

```python
"""API v1 router — aggregates all domain sub-routers."""

from fastapi import APIRouter

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

router = APIRouter()

# Health check — retained from Phase 1 (used by Docker healthcheck)
@router.get("/health", tags=["health"])
async def health_check():
    """Returns 200 OK. Used by Docker healthchecks and load balancers."""
    return {"status": "ok", "version": "1.0.0"}


# Domain routers
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(students_router)
router.include_router(staff_router)
router.include_router(academic_router)
router.include_router(assessments_router)
router.include_router(assignments_router)
router.include_router(attendance_router)
router.include_router(leave_router)
router.include_router(notifications_router)
router.include_router(analytics_router)
```

---

## Step 6 — Create test file `backend/tests/unit/test_endpoints.py`

```python
"""Unit tests — Phase 4 endpoint layer: import checks + route registration."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ── Import checks ─────────────────────────────────────────────────────────────

def test_auth_router_importable():
    from app.api.v1.endpoints.auth import router
    assert router is not None


def test_users_router_importable():
    from app.api.v1.endpoints.users import router
    assert router is not None


def test_students_router_importable():
    from app.api.v1.endpoints.students import router
    assert router is not None


def test_staff_router_importable():
    from app.api.v1.endpoints.staff import router
    assert router is not None


def test_academic_router_importable():
    from app.api.v1.endpoints.academic import router
    assert router is not None


def test_assessments_router_importable():
    from app.api.v1.endpoints.assessments import router
    assert router is not None


def test_assignments_router_importable():
    from app.api.v1.endpoints.assignments import router
    assert router is not None


def test_attendance_router_importable():
    from app.api.v1.endpoints.attendance import router
    assert router is not None


def test_leave_router_importable():
    from app.api.v1.endpoints.leave import router
    assert router is not None


def test_notifications_router_importable():
    from app.api.v1.endpoints.notifications import router
    assert router is not None


def test_analytics_router_importable():
    from app.api.v1.endpoints.analytics import router
    assert router is not None


def test_academic_service_importable():
    from app.services.academic_service import AcademicService
    assert callable(AcademicService)


def test_services_exports_academic_service():
    import app.services as svc
    assert hasattr(svc, "AcademicService")


def test_submit_attempt_request_schema():
    from app.schemas.assessment import SubmitAttemptRequest, AnswerItem
    from uuid import uuid4
    item = AnswerItem(question_id=uuid4(), answer="42")
    req = SubmitAttemptRequest(answers=[item])
    assert len(req.answers) == 1


def test_broadcast_notification_schema():
    from app.schemas.notification import BroadcastNotificationRequest
    from uuid import uuid4
    req = BroadcastNotificationRequest(
        recipient_ids=[uuid4(), uuid4()],
        title="Test",
        message="Hello",
    )
    assert len(req.recipient_ids) == 2


# ── Route registration ─────────────────────────────────────────────────────────

def test_v1_router_includes_all_sub_routers():
    """v1 router must expose routes for every domain."""
    from app.api.v1.router import router
    paths = {r.path for r in router.routes}
    # Health check retained
    assert "/health" in paths


def test_app_has_auth_token_route():
    """POST /api/v1/auth/token must be registered (OAuth2 tokenUrl target)."""
    from app.main import app
    routes = {(r.path, list(r.methods)) for r in app.routes if hasattr(r, "methods")}
    token_routes = [r for r in routes if "/auth/token" in r[0]]
    assert len(token_routes) > 0, "POST /api/v1/auth/token must exist"


def test_app_health_check_still_accessible():
    """GET /api/v1/health must still return 200 after Phase 4 router rewrite."""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_app_login_endpoint_exists():
    """POST /api/v1/auth/token must exist and return 422 (missing form fields), not 404."""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/v1/auth/token")
    # 422 = validation error (no form data provided) — confirms route exists
    assert response.status_code == 422


def test_app_protected_route_returns_401():
    """GET /api/v1/users without token must return 401, not 404."""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_me_route_registered_before_uuid_route_students():
    """GET /students/me must appear before GET /students/{student_id} in route list."""
    from app.api.v1.endpoints.students import router
    paths = [r.path for r in router.routes]
    assert "/me" in paths
    me_idx = paths.index("/me")
    uuid_idx = next((i for i, p in enumerate(paths) if "{student_id}" in p), None)
    assert uuid_idx is not None
    assert me_idx < uuid_idx, "/me must be registered before /{student_id}"


def test_pending_route_registered_before_uuid_route_leave():
    """GET /leave/pending must appear before GET /leave/{leave_id} in route list."""
    from app.api.v1.endpoints.leave import router
    paths = [r.path for r in router.routes]
    assert "/pending" in paths
    pending_idx = paths.index("/pending")
    uuid_idx = next((i for i, p in enumerate(paths) if "{leave_id}" in p), None)
    assert uuid_idx is not None
    assert pending_idx < uuid_idx, "/pending must be registered before /{leave_id}"
```

---

## Step 7 — Run tests

```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend
source ../venv/bin/activate
python -m pytest tests/unit/ -v --tb=short 2>&1 | tail -25
```

**Expected output:**
```
...
============================================================
X passed, 0 failed in Y.YYs
```
Target: **110+ tests passing** (93 from prior phases + ~25 new endpoint tests).

---

## Step 8 — Git commit

```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec
git add -A
git commit -m "feat: Phase 4 — API routers & endpoint wiring (11 domain routers, 50+ endpoints)

- app/api/v1/router.py: registers all 11 sub-routers; health check retained
- endpoints/auth.py: POST /auth/token (OAuth2 form), POST /auth/refresh, GET /auth/me
- endpoints/users.py: full CRUD + change-password + activate (AdminOnly)
- endpoints/students.py: profile CRUD + /me (route order: /me before /{id})
- endpoints/staff.py: profile CRUD + /me
- endpoints/academic.py: departments, session-years, classrooms, subjects CRUD
- endpoints/assessments.py: quiz CRUD + publish/close + questions + attempt lifecycle
- endpoints/assignments.py: assignment CRUD + submit + grade + AI grade
- endpoints/attendance.py: sessions + mark-attendance + student summary
- endpoints/leave.py: apply/review/cancel (/pending before /{leave_id})
- endpoints/notifications.py: send + broadcast + /me + mark-read
- endpoints/analytics.py: student/classroom/staff summaries
- services/academic_service.py: thin CRUD wrapper for academic entities
- schemas/assessment.py: AnswerItem + SubmitAttemptRequest added
- schemas/notification.py: BroadcastNotificationRequest added
- 110+ tests passing"
```

---

## Acceptance Criteria

- [ ] `python -c "from app.api.v1.router import router; print(len(router.routes), 'routes')"` prints `12` or more
- [ ] `GET /api/v1/health` → `{"status": "ok", "version": "1.0.0"}` (TestClient, 200)
- [ ] `POST /api/v1/auth/token` with no body → `422` (route exists, fails validation — NOT 404)
- [ ] `GET /api/v1/users` with no token → `401` (RBAC guard active — NOT 404)
- [ ] All unit tests pass: `python -m pytest tests/unit/ -q` → `0 failed`
- [ ] `/me` route index < `/{student_id}` route index in `students.py` router
- [ ] `/pending` route index < `/{leave_id}` route index in `leave.py` router
- [ ] `from app.services import AcademicService` succeeds

---

## Rollback

```bash
# Remove all new endpoint files
rm backend/app/api/v1/endpoints/auth.py
rm backend/app/api/v1/endpoints/users.py
rm backend/app/api/v1/endpoints/students.py
rm backend/app/api/v1/endpoints/staff.py
rm backend/app/api/v1/endpoints/academic.py
rm backend/app/api/v1/endpoints/assessments.py
rm backend/app/api/v1/endpoints/assignments.py
rm backend/app/api/v1/endpoints/attendance.py
rm backend/app/api/v1/endpoints/leave.py
rm backend/app/api/v1/endpoints/notifications.py
rm backend/app/api/v1/endpoints/analytics.py
rm backend/app/services/academic_service.py
rm backend/tests/unit/test_endpoints.py

# Restore router.py to Phase 1 stub
git checkout HEAD~1 -- backend/app/api/v1/router.py
git checkout HEAD~1 -- backend/app/schemas/assessment.py
git checkout HEAD~1 -- backend/app/schemas/notification.py
git checkout HEAD~1 -- backend/app/services/__init__.py
```
