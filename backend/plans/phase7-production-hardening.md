# ExecPlan: Phase 7 — Production Hardening & Deployment Checklist

## Context

This repo is a fully async FastAPI backend for a School Management System, using:
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 async + asyncpg
- PostgreSQL + Redis + RabbitMQ
- Celery workers for background jobs
- WebSockets for realtime notifications

Phase 6 delivered WebSockets + Celery tasks and stabilized the test harness. Phase 7 hardens the
deployment story: production-safe database engine configuration, a Docker Compose topology that
includes a Celery worker, and a verifiable production checklist aligned with `docs/SECURITY.md`
and `docs/MIGRATION_PLAN.md`.

Key Phase 7 gates from `docs/ARCHITECTURE.md` and `docs/MIGRATION_PLAN.md`:
- `docker compose -f docker/docker-compose.yml up -d` starts all services clean.
- Production secrets checklist complete (`docs/SECURITY.md`).
- `docker/Dockerfile.prod` builds successfully.

Critical discovery (must fix in this phase):
- Setting `ENVIRONMENT=production` currently breaks app import because `app/core/database.py`
  passes `pool_size`/`max_overflow` while also forcing `NullPool`, which SQLAlchemy rejects:
  - `TypeError: Invalid argument(s) 'pool_size','max_overflow' ... PGDialect_asyncpg/NullPool/Engine`

---

## Progress

- [x] Author Phase 7 ExecPlan (this file): align with existing docs and current repo state.
- [x] Fix production DB engine configuration (`ENVIRONMENT=production` import must succeed).
- [ ] Add a Celery worker service to Docker Compose.
- [ ] Add production-oriented Compose file (or harden existing) and document the operational commands.
- [ ] Run smoke validations (non-network): config import checks; compose file structure sanity; unit/integration tests still green.

---

## Scope

**Files to MODIFY:**

| File | Change |
|---|---|
| `backend/app/core/database.py` | Fix production engine configuration (remove invalid `NullPool` + pooling args combination; keep behavior aligned with `.env.example`) |
| `backend/docker/docker-compose.yml` | Add a `worker` service to run Celery; ensure broker/backend env aligns with `app/core/config.py` |
| `backend/docs/SECURITY.md` | Update checklist notes if needed to reflect actual env var names used by compose/services |

**Files to CREATE:**

| File | Purpose |
|---|---|
| `backend/docker/docker-compose.prod.yml` | Production compose (no Adminer/Redis Commander; uses `Dockerfile.prod`; includes `worker`) |

**Out of scope (explicitly not done in Phase 7):**
- Redis pub/sub fan-out for multi-process WebSockets (not required for single-host production; track as future work).
- Data migration automation from legacy Django/SQLite (separate spec).

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Production SQLAlchemy pool | Use the default async pool (no `NullPool`) | Production should pool DB connections; `.env.example` already exposes pool size settings. Also fixes the current import-time crash. |
| Celery topology | Run Celery worker as a separate container | Matches the architecture (HTTP API decoupled from background jobs) and enables horizontal scaling later. |
| Compose files | Keep `docker-compose.yml` as dev; add `docker-compose.prod.yml` | Keeps local developer UX (Adminer, Redis Commander) while giving a minimal production footprint. |
| Secrets management | Use `.env` (not committed) + `docs/SECURITY.md` checklist | Keeps the repo portable; follows existing documentation. |

---

## Steps

### Step 1 — Fix production DB engine configuration

Goal: `ENVIRONMENT=production` must not crash at import time.

Implementation:
- Update `backend/app/core/database.py` to remove the conditional `NullPool` usage (or remove pooling args when using `NullPool`).
- Keep `pool_size`, `max_overflow`, and `pool_pre_ping` configurable via env vars.

Verification:
```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend
ENVIRONMENT=production ../venv/bin/python -c "from app.core.database import engine; print('ok')"
```

Expected output:
    ok

---

### Step 2 — Add a Celery worker service to dev compose

Update `backend/docker/docker-compose.yml`:
- Add `worker` service built from the same context as `app`.
- Set the same DB/Redis/RabbitMQ env vars as `app`.
- Run the worker command:
  - `celery -A app.tasks.celery_app worker --loglevel=info -Q grading,email,notifications,celery`
- Add `depends_on` for `postgres`, `redis`, and `rabbitmq`.

Expected outcome:
- `docker compose -f docker/docker-compose.yml up -d` brings up `worker` alongside `app`.

---

### Step 3 — Add production compose file

Create `backend/docker/docker-compose.prod.yml`:
- Use `docker/Dockerfile.prod` for `app` and `worker`.
- Remove development-only services (`adminer`, `redis-commander`).
- Set `ENVIRONMENT=production`, `DEBUG=false`, `RELOAD=false`.
- Keep health checks where appropriate.

Verification (structure only, no image pulls required):
- `docker/docker-compose.prod.yml` exists and contains `services: app, worker, postgres, redis, rabbitmq`.

---

### Step 4 — Update docs/SECURITY checklist if needed

Ensure `docs/SECURITY.md` references match actual env vars used by:
- `app/core/config.py`
- `docker/docker-compose.yml`
- `docker/docker-compose.prod.yml`

---

### Step 5 — Final validations and frequent commits

Run:
```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend
../venv/bin/python -m pytest tests -q
```

Expected output:
    148 passed

Commit at each milestone:
- After Step 1.
- After Step 2–3.
- After Step 4–5.

---

## Acceptance Criteria

- [ ] `ENVIRONMENT=production` import check passes (Step 1 verification prints `ok`).
- [ ] `backend/docker/docker-compose.yml` includes a `worker` service running Celery.
- [ ] `backend/docker/docker-compose.prod.yml` exists and includes `app` + `worker` using `Dockerfile.prod`.
- [ ] Full test suite remains green: `../venv/bin/python -m pytest tests -q`.

---

## Rollback

```bash
git revert HEAD --no-edit
```

If multiple commits were made for Phase 7, revert them in reverse order.

---

## Surprises & Discoveries

- 2026-04-24: `ENVIRONMENT=production` crashed at import time due to invalid engine args with `NullPool`:
  - `TypeError: Invalid argument(s) 'pool_size','max_overflow' ... PGDialect_asyncpg/NullPool/Engine`
  - Fixed by removing `NullPool` forcing and skipping `create_all` in production (`backend/app/core/database.py`).

---

## Decision Log

- 2026-04-24: Prefer a pooled production DB engine (default async pool) over `NullPool` to align with `.env.example` settings and avoid import-time crashes.
- 2026-04-24: Enforce the existing contract “use Alembic in production” by skipping `Base.metadata.create_all` when `ENVIRONMENT=production`.

---

## Outcomes & Retrospective

- 2026-04-24: Unblocked production imports by fixing SQLAlchemy engine configuration and preventing accidental `create_all` in production.
