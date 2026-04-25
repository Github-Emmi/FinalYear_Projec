# Architecture: School Management System — FastAPI Backend

## Overview

This system is a production-grade REST API backend for a school management platform.
It replaces a legacy Django + SQLite application with a fully async FastAPI stack
backed by PostgreSQL, Redis, and RabbitMQ (local/dev) or Redis-only (Render.com production).

## Component Responsibilities

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| API server | FastAPI 0.104+ | HTTP routing, request validation, OpenAPI doc generation |
| ORM | SQLAlchemy 2.0 async | Database access; no raw SQL except in migrations |
| Database | PostgreSQL 15 | Primary persistent data store; all entities |
| Cache / sessions | Redis 7 | Short-lived data: rate-limit counters, session tokens, query caches |
| Message broker | RabbitMQ 3.12 (dev) / Redis (Render) | Decouples async tasks from HTTP request lifecycle |
| Task worker | Celery 5.3+ | Executes background jobs: grading, email, analytics |
| File storage | Cloudinary | Binary uploads (assignments, photos); not stored locally |
| AI grading | OpenRouter (`openrouter/free`) | Model-agnostic proxy; zero-cost inference, swap model via `.env` |
| Auth | JWT (HS256) + OAuth2 password flow | Stateless authentication; refresh token rotation |

## Data Flow — HTTP Request

```
Client → FastAPI → Auth Middleware → Rate Limit Middleware
      → Router → Endpoint handler
      → Service layer (business logic)
      → Repository layer (SQLAlchemy query)
      → PostgreSQL
      ← Result ← Repository ← Service ← Endpoint
      → Pydantic serialization → JSON response → Client
```

## Data Flow — Background Job

```
Endpoint → Celery task.delay(payload)
         → RabbitMQ queue
         → Celery worker picks up
         → Executes task (grading, email, report)
         → Writes result back to PostgreSQL
         → (optionally) WebSocket notification to client
```

## Directory Structure

```
backend/
├── app/
│   ├── main.py           FastAPI factory + lifespan (DB connect/disconnect)
│   ├── core/             Cross-cutting: config, DB, security, exceptions, logging
│   ├── models/           SQLAlchemy 2.0 ORM models (20+), all inherit BaseModel
│   ├── schemas/          Pydantic v2 request/response schemas per entity
│   ├── repositories/     Async CRUD data-access; one class per model
│   ├── services/         Business logic; services call repositories, never models directly
│   ├── api/v1/endpoints/ FastAPI routers; endpoints call services, never repositories
│   ├── middleware/       Exception shaping, logging, auth validation, rate limiting
│   ├── websockets/       Real-time: connection manager, chat, notifications
│   └── tasks/            Celery task definitions
├── migrations/           Alembic: env.py, script.py.mako, versions/
├── tests/                conftest.py, unit/, integration/, e2e/
├── docker/               Dockerfile, Dockerfile.prod, docker-compose.yml
├── main.py               uvicorn entry point
├── requirements.txt      Pinned dependencies
└── .env.example          All required env vars with placeholder values
```

## Phase Delivery Sequence

| Phase | Deliverable | Gate |
|-------|-------------|------|
| 1 | This scaffold + arch docs + core infra | All Phase 1 tests pass |
| 2 | 20+ ORM models + Pydantic schemas + repositories | All Phase 2 tests pass |
| 3 | Service layer + auth + RBAC | All Phase 3 tests pass |
| 4 | All v1 API endpoints + OpenAPI docs complete | All Phase 4 tests pass |
| 5 | WebSockets + Celery tasks + real-time | All Phase 5 tests pass |
| 6 | Tests: unit + integration + e2e, coverage ≥ 90% | Coverage report passes |
| 7 | Docker hardening + production checklist | Docker prod build passes |

## AI & Intelligence Layer (2026+)

- **AI Grading Agent**: Modular, model-agnostic service wraps OpenRouter via openai SDK. All grading and analytics tasks use `openrouter/free` by default, ensuring zero-cost, unlimited inference with automatic model selection and fallback.
- **Model Routing**: All AI tasks (essay grading, quiz grading, analytics) are routed through `openrouter/free`, which selects the best available free model for each request. Paid models can be enabled by overriding a single config value.
- **Event-Driven**: All AI grading is performed asynchronously via Celery tasks, decoupled from HTTP requests, with results persisted to the database and real-time notifications pushed to users via WebSockets.

## Production Readiness

- **Dockerized**: Full Docker Compose setup for local and production, including Celery worker, RabbitMQ, Redis, and PostgreSQL.
- **Secrets Management**: All secrets and credentials are managed via `.env` and validated at startup. See `docs/SECURITY.md` for the production checklist.
- **Test Coverage**: 150+ tests (unit, integration, e2e) with coverage reports. All core logic is test-covered.
- **Extensible**: Model selection, grading logic, and notification flows are modular and can be extended without breaking API contracts.

## Render.com Deployment Blueprint

Production runs as a **four-service cluster** on Render.com:

| Service | Render Type | Command |
|---------|-------------|---------|
| PostgreSQL | Managed DB | — |
| Redis | Managed Redis | — (also serves as Celery broker + result backend) |
| FastAPI API | Web Service | `uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT` |
| Celery Worker | Background Worker | `celery -A app.tasks.celery_app worker --loglevel=info` |

**Build command** (Web Service): `bash scripts/render-build.sh`  
This script installs dependencies, runs `alembic upgrade head`, and exports the OpenAPI schema.

**Required environment variables** on all Render services:

| Variable | Source |
|----------|--------|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Render Internal PostgreSQL URL |
| `REDIS_URL` | Render Internal Redis URL |
| `SECRET_KEY` | Generated 64-char secret |
| `OPENROUTER_API_KEY` | OpenRouter dashboard |

> On Render, Redis handles both the Celery broker (`CELERY_BROKER_URL`) and result backend
> (`CELERY_RESULT_BACKEND`). RabbitMQ is used in local Docker Compose only.

## CI/CD Pipeline

`.github/workflows/deploy.yml` runs on every push to `main` or `phase/1-fresh-scaffold`:

1. **Test job** — spins up Postgres 15 + Redis 7 service containers, installs deps,
   runs `pytest tests/ -q` against the full suite (148+ tests).
2. **Deploy job** — runs only on `main` after all tests pass; triggers the Render
   deploy hook via `curl -X POST $RENDER_DEPLOY_HOOK`.

Add `RENDER_DEPLOY_HOOK` as a GitHub repository secret (Settings → Secrets → Actions).

## Front-End Integration Contract

| Protocol | Detail |
|----------|--------|
| AI grading response | `POST /grade-ai` → `202 Accepted` + `job_id`. **Do not poll** — wait for WebSocket push. |
| WebSocket URL | `wss://<host>/api/v1/ws/notifications?token={JWT}` |
| Heartbeat | Frontend must send `"ping"` text frame every 30 s (Render LB idle timeout). |
| Error envelope | All errors return `{"detail": ..., "code": ..., "status": ...}` — use a global interceptor. |
