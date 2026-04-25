# Migration Plan: Django → FastAPI

## Source

Legacy Django 4.2 application with SQLite database at `db.sqlite3` (read-only source).
Legacy Django code preserved in `legacy_django/` for reference only — never imported.

## Target

FastAPI + PostgreSQL backend delivered in 7 phases (see ARCHITECTURE.md).

## Phase Delivery Checklist

### Phase 1 — Fresh scaffold (this plan)
- [x] New git branch `phase/1-fresh-scaffold` from `origin/main`
- [x] All tracked files deleted except `.github/`
- [x] 6 architecture docs created
- [x] `backend/` canonical structure scaffolded
- [x] Core infrastructure: config, database, security, exceptions, logging
- [x] `venv/` created with pinned dependencies installed
- [x] Health endpoint responds 200
- [x] `pytest tests/` passes

### Phase 2 — Data models
- [ ] 20+ SQLAlchemy ORM models created in `app/models/`
- [ ] Pydantic schemas (Create, Update, Response) for each model
- [ ] Repository base class + per-model repositories
- [ ] Alembic migration `001_initial_schema.py` created and runs clean
- [ ] All Phase 2 unit tests pass

### Phase 3 — Service layer
- [ ] All services implemented in `app/services/`
- [ ] Auth service: login, register, refresh, logout
- [ ] RBAC dependency helpers in `app/api/v1/dependencies.py`
- [ ] All Phase 3 tests pass

### Phase 4 — API endpoints
- [ ] All v1 routers registered in `app/api/v1/router.py`
- [ ] OpenAPI schema has 0 errors
- [ ] All Phase 4 integration tests pass

### Phase 5 — Real-time + async
- [ ] WebSocket connection manager implemented
- [ ] Celery app configured with RabbitMQ broker
- [ ] Quiz grading task, email task, analytics task
- [ ] All Phase 5 tests pass

### Phase 6 — Test coverage
- [ ] `pytest --cov=app --cov-report=term-missing` shows ≥ 90%
- [ ] e2e test: full quiz submission + grading flow passes

### Phase 7 — Production hardening
- [ ] `docker compose -f docker/docker-compose.yml up -d` starts all services clean
- [ ] Production secrets checklist complete (see SECURITY.md)
- [ ] `Dockerfile.prod` builds successfully

## Data Migration (Legacy SQLite → PostgreSQL)

Covered in a separate ExecPlan to be authored in Phase 2.

Key facts about the legacy data:
- SQLite file: `db.sqlite3` (preserved as read-only, never deleted)
- Legacy integer PKs must be remapped to UUID v4
- Typo field names in legacy schema: `father_postion`, `Attendence`, `FeedBackStaffs`
  — must be normalized during transform
- Legacy tables have no soft-delete — all rows are live records
- Migration is one-way: no write-back to Django/SQLite

## Rollback Strategy

If a phase introduces a breaking change:

1. Stop docker services: `docker compose down`
2. Return to prior branch: `git checkout <prior-branch>`
3. Drop and recreate the database volume: `docker compose down -v && docker compose up -d`
4. Re-run migrations on the prior branch

Schema rollback: Each Alembic revision has a `downgrade()` function.
Run `alembic downgrade -1` to revert the most recent migration.
