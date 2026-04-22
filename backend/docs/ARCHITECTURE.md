# Architecture: School Management System — FastAPI Backend

## Overview

This system is a production-grade REST API backend for a school management platform.
It replaces a legacy Django + SQLite application with a fully async FastAPI stack
backed by PostgreSQL, Redis, and RabbitMQ.

## Component Responsibilities

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| API server | FastAPI 0.104+ | HTTP routing, request validation, OpenAPI doc generation |
| ORM | SQLAlchemy 2.0 async | Database access; no raw SQL except in migrations |
| Database | PostgreSQL 15 | Primary persistent data store; all entities |
| Cache / sessions | Redis 7 | Short-lived data: rate-limit counters, session tokens, query caches |
| Message broker | RabbitMQ 3.12 | Decouples async tasks from HTTP request lifecycle |
| Task worker | Celery 5.3+ | Executes background jobs: grading, email, analytics |
| File storage | Cloudinary | Binary uploads (assignments, photos); not stored locally |
| AI grading | OpenAI GPT-4o-mini | Essay auto-grading via structured prompt + response parsing |
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
