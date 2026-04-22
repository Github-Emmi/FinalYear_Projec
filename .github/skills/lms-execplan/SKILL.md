---
name: lms-execplan
description: "Author a self-contained executable specification (ExecPlan) for the LMS FastAPI migration project. Use when writing phase implementation plans, scaffolding backend features, generating architecture docs, or specifying data-model or API changes. Trigger phrases: write execplan, author spec, create implementation plan, spec out phase, draft architecture docs, plan migration step."
argument-hint: "Describe what needs to be specified (e.g. 'Phase 1 fresh scaffold with core infrastructure', 'Data model for User and Student entities', 'Auth service spec')."
user-invocable: true
---

# LMS ExecPlan Authoring Skill

You are a Professional Modern Software Web Application and DS/AIML Engineer. You author executable specifications ("ExecPlans") that a stateless coding agent can follow without any prior context.

## When to Use

- Writing phase-level implementation plans for the LMS FastAPI migration
- Specifying a new feature, service, or model in `backend/`
- Producing architecture design documents (ARCHITECTURE.md, ADR.md, DATA_MODEL.md, etc.)
- Handing off implementation work to the **LMS Modernization Architectural Design Pattern Planner** agent

## Core Contract

An ExecPlan must be:
- **Self-contained** — no external blog links or docs. Embed all required knowledge in your own words.
- **Unambiguous** — resolve every fork in the plan yourself. Do not say "choose one"; say which one and why.
- **Evidence-capturing** — include expected terminal output, short diffs, or log excerpts that prove each step succeeded.
- **Beginner-safe** — treat the executing agent as having only the working tree and this single file. Repeat every assumption.

## Procedure

### Step 1 — Read Before Writing

Before drafting a single word of the plan:

1. Read `README.md` and every `PHASE*_TODO.md` in the workspace root.
2. Read `SERVICES_AUDIT_REPORT.md` and any `*_AUDIT*.md` files.
3. If a prior ExecPlan file is checked in (e.g. `backend/ARCHITECTURE.md`, `backend/ADR.md`), read it in full and incorporate it by reference. If it is not checked in, reproduce all relevant context inline.
4. Read the full [agent file](./../agents/lms-modernization-planner.agent.md) to confirm the canonical phase sequence and architecture targets.
5. Inventory the real directory tree for the scope of the plan (never assume a file exists).

### Step 2 — Choose the Right ExecPlan Type

| Type | When to use | Required sections |
|------|-------------|-------------------|
| **Phase Plan** | Delivering a numbered phase end-to-end | Goal, Pre-conditions, Steps, Acceptance Tests, Permission Gate |
| **Feature Spec** | Adding a single service / endpoint / model | Context, Design Decisions, Implementation Steps, Tests |
| **Architecture Doc** | One of the 6 canonical arch docs | Purpose, Scope, Content Outline, Writing Instructions |
| **Data Migration Spec** | Moving data from legacy Django/SQLite | Source mapping, Transform rules, Load order, Verification |

### Step 3 — Draft the Skeleton

Use [execplan-template.md](./assets/execplan-template.md) as the starting skeleton. Fill every section — do not leave placeholders.

Required top-level sections for **all** ExecPlan types:

```
# ExecPlan: <short title>

## Context
<Why this plan exists, what problem it solves, what phase it belongs to.>
<List every assumption. State what files exist and what their current state is.>

## Scope
<Exact list of files to create, modify, or delete. Nothing else changes.>

## Design Decisions
<For each non-obvious choice, state the option chosen and a one-sentence rationale.>

## Steps
<Numbered, sequential, shell-runnable or file-edit steps.>
<Each step ends with: "Expected output:" followed by an indented example.>

## Acceptance Criteria
<Checklist of observable outcomes. Every item must be verifiable by running a command or reading a file.>

## Rollback
<How to undo this plan completely if something goes wrong.>
```

### Step 4 — Flesh Out Steps

For each step:

- Write the **exact command** or **exact file edit** (not "edit config.py" — write the diff or the full replacement block).
- For file creation, include the complete file content, not a summary.
- For shell commands, include the expected stdout/stderr, trimmed to the relevant lines:

  ```
  Expected output:
      INFO:     Uvicorn running on http://0.0.0.0:8000
      INFO:     Application startup complete.
  ```

- For test steps, write the pytest invocation and the expected pass summary:

  ```
  Expected output:
      collected 12 items
      ...........
      12 passed in 0.42s
  ```

### Step 5 — Apply Quality Checks

Run every item in [quality-checklist.md](./references/quality-checklist.md) before saving the plan. Do not deliver an ExecPlan that fails any Critical or High item.

### Step 6 — Save and Announce

- Save the plan to `backend/plans/<phase-or-feature-slug>.md` (create `plans/` if absent).
- Summarize: what the plan does, what the executing agent needs before starting, and what will be true when the plan is complete.
- Ask the user: "Ready to execute this plan? Type **Yes, execute `<filename>`** to proceed."

---

## Failure Modes to Avoid

| Anti-pattern | Fix |
|---|---|
| "See the FastAPI docs for details" | Embed the relevant behavior in the plan itself |
| "Choose between option A and B" | Choose one. State why. |
| Step says "update config.py" with no diff | Write the exact field name, value, and surrounding context |
| Plan references a file that may not exist | Verify first; if uncertain, add a guard step: `[ -f path ] && ...` |
| Expected output omitted | Add a concise, realistic example |
| Acceptance criteria says "it works" | Replace with a specific command and its expected exit code |
| Plan assumes context from a prior conversation | Inline all required context |

---

## Architecture Target (embedded — do not fetch externally)

The canonical backend structure this project migrates toward:

```
backend/
├── app/
│   ├── main.py              # FastAPI factory + lifespan
│   ├── core/                # config, database, security, exceptions, logging
│   ├── models/              # 20+ SQLAlchemy 2.0 async ORM models (UUID PKs)
│   ├── schemas/             # Pydantic v2 request/response schemas
│   ├── repositories/        # Async CRUD data-access layer (base + per-model)
│   ├── services/            # Business logic (auth, student, assessment/AI, email)
│   ├── api/v1/endpoints/    # FastAPI routers (auth, admin, staff, students, quizzes, assignments)
│   ├── websockets/          # Real-time (manager, chat, notifications)
│   ├── tasks/               # Celery (celery_app, quiz_grading, email, analytics)
│   └── middleware/          # exception_handler, auth_middleware, rate_limit
├── migrations/              # Alembic (env.py, script.py.mako, versions/)
├── tests/                   # conftest.py, unit/, integration/, e2e/
├── docker/                  # Dockerfile, Dockerfile.prod, docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── main.py
└── .env.example
```

**Tech stack pinned versions:**
- FastAPI `>=0.104`
- Python `>=3.10`
- SQLAlchemy `2.0` (async, `asyncpg` driver)
- PostgreSQL `15`
- Redis `7`
- RabbitMQ `3.12`
- Celery `>=5.3`
- Pydantic `>=2.5`
- JWT / OAuth2 (python-jose + passlib[bcrypt])
- Cloudinary (file storage)
- OpenAI `GPT-4o-mini` (essay auto-grading)

**Docker-compose service ports:**
| Service | Port | UI |
|---------|------|-----|
| FastAPI | 8000 | `/docs`, `/redoc` |
| PostgreSQL 15 | 5432 | Adminer `:8080` |
| Redis 7 | 6379 | Redis Commander `:8081` |
| RabbitMQ 3.12 | 5672 | Management `:15672` |

**Phase sequence (never skip or merge phases without explicit user approval):**

| Phase | Deliverable |
|-------|-------------|
| 1 | Git branch, clean scaffold, arch docs, venv, core infra |
| 2 | 20+ ORM models, Pydantic schemas, repository layer |
| 3 | Service layer, auth, RBAC |
| 4 | All v1 API endpoints, OpenAPI docs |
| 5 | WebSockets, Celery tasks, real-time |
| 6 | Tests — unit + integration + e2e, coverage ≥ 90 % |
| 7 | Docker hardening, production checklist, deployment |

**Six mandatory architecture docs (Phase 1 deliverables):**
1. `ARCHITECTURE.md` — stack overview, component responsibilities, data-flow diagram
2. `ADR.md` — Architecture Decision Records (FastAPI vs Django, async SQLAlchemy, UUID PKs, etc.)
3. `DATA_MODEL.md` — 20+ entity overview, field conventions, relationship diagram
4. `API_DESIGN.md` — REST conventions, versioning (`/api/v1/`), error contract, pagination
5. `SECURITY.md` — auth flow, RBAC matrix, JWT lifecycle, secrets policy
6. `MIGRATION_PLAN.md` — phased checklist, rollback strategy, legacy data migration steps
