# ExecPlan: Phase 2 — ORM Models, Pydantic Schemas, Repository Layer

## Context

Phase 1 delivered a clean FastAPI scaffold on `phase/1-fresh-scaffold` with:
- `backend/app/core/` (config, database, security, exceptions, logging)
- `backend/app/models/base.py` — `BaseModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base)`
- `backend/app/middleware/`, `backend/app/api/v1/router.py` (health endpoint)
- `backend/migrations/env.py` — async Alembic environment
- `backend/tests/unit/test_health.py` — 2 tests passing

Installed stack (Python 3.14.3 compatible):
- SQLAlchemy 2.0.49, asyncpg 0.31.0, pydantic 2.13.3, pydantic-settings 2.14.0

This plan delivers **Phase 2**: 20 ORM entities (11 model files), 11 Pydantic schema files,
13 repository files, 1 Alembic migration (`001_initial_schema.py`), and 3 acceptance test files.

## Scope — Files Created / Modified

### New files — `backend/app/models/`
- `user.py`        → User (role enum)
- `academic.py`    → Department, SessionYear, ClassRoom, Subject
- `student.py`     → StudentProfile
- `staff.py`       → StaffProfile
- `assessment.py`  → Quiz, Question, QuizAttempt, QuizResult (4 entities)
- `assignment.py`  → Assignment, AssignmentSubmission
- `attendance.py`  → AttendanceSession, AttendanceRecord
- `feedback.py`    → FeedbackStaff, FeedbackStudent
- `leave.py`       → LeaveRequest
- `notification.py`→ Notification
- `audit.py`       → AuditLog

### Updated — `backend/app/models/__init__.py`
Imports all 20 model classes so `Base.metadata` is populated.

### New files — `backend/app/schemas/`
- `user.py`, `academic.py`, `student.py`, `staff.py`, `assessment.py`,
  `assignment.py`, `attendance.py`, `feedback.py`, `leave.py`,
  `notification.py`, `auth.py`

### Updated — `backend/app/schemas/__init__.py`

### New files — `backend/app/repositories/`
- `base.py`        → `BaseRepository[ModelT]` generic async CRUD
- `user.py`        → UserRepository (+ get_by_email, get_by_username)
- `student.py`     → StudentRepository (+ get_by_user_id, get_by_classroom)
- `staff.py`       → StaffRepository (+ get_by_user_id, get_by_department)
- `academic.py`    → Department/ClassRoom/Subject/SessionYear repositories
- `assessment.py`  → Quiz/Question/QuizAttempt/QuizResult repositories
- `assignment.py`  → Assignment/Submission repositories
- `attendance.py`  → Session/Record repositories
- `feedback.py`    → FeedbackStaff/FeedbackStudent repositories
- `leave.py`       → LeaveRequest repository
- `notification.py`→ Notification repository
- `audit.py`       → AuditLog repository
- `factory.py`     → RepositoryFactory (single entry point)

### Updated — `backend/app/repositories/__init__.py`

### Updated — `backend/migrations/env.py`
Adds `import app.models` after Base import so autogenerate sees all tables.

### New file — `backend/migrations/versions/001_initial_schema.py`
Manually written Alembic migration: creates all 20 tables, drops in reverse on downgrade.

### New files — `backend/tests/unit/`
- `test_models.py`       → imports all models, checks `__tablename__` (20 assertions)
- `test_schemas.py`      → instantiates Create/Response schemas (11 assertions)
- `test_repositories.py` → imports all repository classes (13 assertions)

## Design Decisions

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Enum columns | Python `enum.Enum` → `String(50)` | Avoids pg ENUM ALTER complexity across migrations |
| Relationships | All bi-directional via `back_populates` | Explicit > magic; avoids stale references |
| QuizResult location | In `assessment.py` alongside QuizAttempt | Same domain; avoids extra file for 1 entity |
| FK UUID type | `UUID(as_uuid=True)` from `sqlalchemy.dialects.postgresql` | Consistent with PK definition in base.py |
| Repository injection | `BaseRepository.__init__(model, session)` | Simple DI; no metaclass magic |
| Factory pattern | `RepositoryFactory(session)` with properties | Single import, easy to extend |
| Migration style | Manual (not autogenerate) | No live Postgres in CI; fully reproducible |

## Acceptance Criteria

- [ ] `python -c "import app.models; print(len(app.models.Base.metadata.tables))"` → `20`
- [ ] `python -m pytest tests/unit/test_models.py -v` → 20 passed
- [ ] `python -m pytest tests/unit/test_schemas.py -v` → 11 passed
- [ ] `python -m pytest tests/unit/test_repositories.py -v` → 13 passed
- [ ] `python -m pytest tests/unit/ -v` → 35+ passed (includes Phase 1 health tests)
- [ ] `python -m alembic check` exits without `ERROR` (migration detected as pending, not broken)
- [ ] `git log --oneline -1` shows Phase 2 commit on `phase/1-fresh-scaffold`

## Rollback

```bash
git revert HEAD --no-edit
# or
git reset --hard HEAD~1
```

All new files are in `app/models/`, `app/schemas/`, `app/repositories/`, and
`migrations/versions/` — no existing core infrastructure is broken by revert.
