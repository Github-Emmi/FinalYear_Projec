# ExecPlan: Phase 6 — WebSockets + Celery Tasks + Real-time Notifications

## Context

Phase 6 of the LMS FastAPI migration on branch `phase/1-fresh-scaffold`.

**Prior phases (committed):**
- Phase 1 `6112a95d` — scaffold, health endpoint
- Phase 2 `04db3237` — 20 ORM models, 13 repositories, migration 001
- Phase 3 `0abb98f8` — 11 service classes, RBAC, auth
- Phase 4 `7f54b44e` — 79 API endpoints
- Phase 5 `af58f0d0` — 139 tests passing, Docker validated, OpenAPI exported

**Current state of Phase 6 directories:**
- `backend/app/websockets/` — exists, contains only `__init__.py` (empty)
- `backend/app/tasks/` — exists, contains only `__init__.py` (empty)
- `backend/app/services/notification_service.py` — saves to DB only; no WebSocket push
- `backend/app/services/email_service.py` — async SMTP, called inline from HTTP request
- Docker containers running: `lms_postgres`, `lms_redis`; RabbitMQ container NOT set up
- `backend/.env` has `REDIS_HOST=localhost`, `REDIS_PORT=6379`

**Architecture goal (per ARCHITECTURE.md Phase 5):**
> WebSockets + Celery tasks + real-time notifications

---

## Scope

**Files to CREATE:**

| File | Purpose |
|---|---|
| `backend/app/websockets/manager.py` | In-memory `ConnectionManager` — connect, disconnect, push to user, broadcast |
| `backend/app/websockets/router.py` | `WS /ws/notifications?token=<jwt>` endpoint |
| `backend/app/tasks/celery_app.py` | Celery app init, Redis broker + result backend |
| `backend/app/tasks/email_tasks.py` | `send_email_task` — wraps `EmailService` as background task |
| `backend/app/tasks/notification_tasks.py` | `push_ws_notification_task` — pushes to connected WebSocket |
| `backend/app/tasks/grading_tasks.py` | `grade_submission_task`, `grade_attempt_task` — triggers AI grading async |
| `backend/tests/unit/test_websocket_manager.py` | Unit tests for ConnectionManager |
| `backend/tests/unit/test_celery_tasks.py` | Unit tests for task signatures (mocked) |
| `backend/scripts/start_worker.sh` | One-liner to start Celery worker locally |

**Files to MODIFY:**

| File | Change |
|---|---|
| `backend/app/main.py` | Include WebSocket router in `create_app()` |
| `backend/app/services/notification_service.py` | After DB save, push WS notification via `ConnectionManager` |
| `backend/app/api/v1/endpoints/assignments.py` | `grade-ai` endpoint enqueues `grade_submission_task` instead of calling inline |
| `backend/app/api/v1/endpoints/assessments.py` | `submit-attempt` enqueues `grade_attempt_task` |
| `backend/requirements.txt` | Add `celery[redis]==5.3.6`, `kombu==5.3.4` |

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Celery broker** | Redis (not RabbitMQ) | RabbitMQ Docker container is not set up locally; Redis is already running. RabbitMQ added in Phase 7 docker-compose. |
| **Celery result backend** | Redis | Same instance, `redis://localhost:6379/1` (DB 1 to separate from app cache on DB 0) |
| **WebSocket auth** | JWT as `?token=<jwt>` query param | Browsers cannot set custom headers on WebSocket connections; query param is the standard pattern |
| **ConnectionManager** | In-memory dict `{user_id: set[WebSocket]}` | Sufficient for single-process dev; Redis pub/sub deferred to Phase 7 multi-process |
| **WS push from notification_service** | Fire-and-forget via `asyncio.create_task` | Keeps notification_service synchronous with DB; WS failure never breaks HTTP response |
| **AI grading tasks** | Enqueue to Celery, return `202 Accepted` from endpoint | Decouples slow OpenAI call from HTTP request lifecycle; endpoint returns immediately |

---

## Steps

### Step 1 — Install Celery

```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend
source ../venv/bin/activate
pip install "celery[redis]==5.3.6" "kombu==5.3.4"
```

Add to `requirements.txt`:
```
celery[redis]==5.3.6
kombu==5.3.4
```

Expected output:
    Successfully installed celery-5.3.6 kombu-5.3.4 ...

---

### Step 2 — Create `app/tasks/celery_app.py`

Celery app using Redis broker (`redis://localhost:6379/0`) and Redis result backend
(`redis://localhost:6379/1`). Auto-discovers tasks in `app.tasks.*`.

Expected output (worker start):
    [config]
    .> app:         lms_worker
    .> transport:   redis://localhost:6379/0
    .> results:     redis://localhost:6379/1
    .> concurrency: 4 (prefork)

---

### Step 3 — Create `app/tasks/email_tasks.py`

`send_email_task(to, subject, body)` — Celery task that runs `EmailService.send_email()`
in a new asyncio event loop (using `asyncio.run()`).

---

### Step 4 — Create `app/tasks/notification_tasks.py`

`push_ws_notification_task(user_id_str, title, message)` — looks up global
`ConnectionManager` singleton and pushes JSON payload to connected socket if present.

---

### Step 5 — Create `app/tasks/grading_tasks.py`

- `grade_submission_task(submission_id_str)` — creates async DB session, calls
  `AssignmentService.grade_with_ai(submission_id)`
- `grade_attempt_task(attempt_id_str)` — creates async DB session, calls
  `AssessmentService` AI grading logic for the quiz attempt

---

### Step 6 — Create `app/websockets/manager.py`

`ConnectionManager` class:
- `active: dict[str, set[WebSocket]]` (keyed by `user_id` string)
- `async connect(user_id, ws)` — accept + register
- `disconnect(user_id, ws)` — deregister; remove empty key
- `async send_to_user(user_id, data: dict)` — JSON push; silently drops if not connected
- `async broadcast(data: dict)` — push to all connected sockets

Global singleton at module level: `manager = ConnectionManager()`

---

### Step 7 — Create `app/websockets/router.py`

Single endpoint: `WS /ws/notifications?token=<jwt>`

Logic:
1. Read `?token=` query param; call `decode_token()` from `app/core/security.py`
2. On invalid/expired token: `await websocket.close(code=1008)` and return
3. On success: `await manager.connect(user_id, websocket)`
4. Enter receive loop; handle `WebSocketDisconnect` to call `manager.disconnect()`
5. Echo any `ping` text frame with `pong` (heartbeat support)

---

### Step 8 — Modify `app/main.py`

Add after existing router include:

```python
from app.websockets.router import ws_router
app.include_router(ws_router)
```

Expected output (`GET /openapi.json`):
    ... "/ws/notifications": { "get": { ... } } ...

---

### Step 9 — Modify `notification_service.py`

After `await self._repos.notifications.create(notification)` in `send()`:

```python
from app.websockets.manager import manager
import asyncio
asyncio.create_task(
    manager.send_to_user(
        str(notification.recipient_id),
        {"type": "notification", "title": data.title, "message": data.message}
    )
)
```

Same pattern applied in `send_broadcast()` for each recipient.

---

### Step 10 — Modify AI grading endpoints

**`assignments.py` — `grade-ai` route:**
- Remove inline `await ai_grader.grade(...)` call
- Replace with: `grade_submission_task.delay(str(submission_id))`
- Change response from `200 OK` to `202 Accepted`

**`assessments.py` — submit attempt route:**
- After saving attempt to DB, fire: `grade_attempt_task.delay(str(attempt.id))`
- Response remains `201 Created` (attempt is created; grading is async)

---

### Step 11 — Write unit tests

**`tests/unit/test_websocket_manager.py`** — 5 tests:
1. `test_connect_registers_websocket` — after connect, user_id in `active`
2. `test_disconnect_removes_websocket` — after disconnect, user_id removed
3. `test_send_to_user_when_connected` — sends JSON to mock WebSocket
4. `test_send_to_user_when_not_connected` — no error raised, returns silently
5. `test_broadcast_sends_to_all` — two connected users both receive message

**`tests/unit/test_celery_tasks.py`** — 4 tests:
1. `test_task_names_registered` — all 4 task names in `celery_app.tasks`
2. `test_send_email_task_signature` — task is callable with `(to, subject, body)`
3. `test_grade_submission_task_signature` — callable with `(submission_id_str,)`
4. `test_grade_attempt_task_signature` — callable with `(attempt_id_str,)`

Expected output:
    collected 9 items
    .........
    9 passed in 0.31s

---

### Step 12 — Create `scripts/start_worker.sh`

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
source ../venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info -Q default
```

Make executable: `chmod +x scripts/start_worker.sh`

---

### Step 13 — Run full test suite + commit

```bash
cd /Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend
source ../venv/bin/activate
pytest tests/ -v --tb=short
```

Expected output:
    collected 148+ items
    ....................................
    148 passed in X.XXs

```bash
git add -A
git commit -m "feat: Phase 6 — WebSockets, Celery tasks, real-time notifications"
```

---

## Acceptance Criteria

- [ ] `GET /docs` shows WebSocket route `WS /ws/notifications`
- [ ] Connecting to `ws://localhost:8000/ws/notifications?token=<valid_jwt>` succeeds (HTTP 101)
- [ ] Connecting with an invalid/expired token closes with code 1008
- [ ] `POST /api/v1/notifications` delivers a JSON push to any open WebSocket for that recipient
- [ ] `POST /api/v1/assignments/submissions/{id}/grade-ai` returns `202 Accepted`
- [ ] `celery -A app.tasks.celery_app inspect registered` lists all task names
- [ ] `pytest tests/unit/test_websocket_manager.py` — 5 passed
- [ ] `pytest tests/unit/test_celery_tasks.py` — 4 passed
- [ ] `pytest tests/ -v` — all prior 139 tests + 9 new tests pass, 0 failures

---

## Rollback

```bash
# Full rollback to Phase 5 HEAD
git reset --hard af58f0d0

# Remove installed packages
pip uninstall celery kombu -y
```
