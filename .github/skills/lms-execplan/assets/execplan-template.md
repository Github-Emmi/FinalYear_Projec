# ExecPlan: <short title — e.g. "Phase 1 Fresh Scaffold">

> **Prior ExecPlan reference**: _None / or: see `backend/plans/<prior-plan>.md`_
> **Target phase**: Phase _N_
> **Author date**: _YYYY-MM-DD_

---

## Context

<!-- WHY this plan exists. What problem does it solve? What phase gate does it unlock? -->
<!-- LIST every assumption explicitly. State what files currently exist and their relevant content. -->
<!-- If this plan builds on a prior plan, summarise the prior plan's outcomes here. -->

This plan implements **[feature / phase]** of the School Management System FastAPI backend migration.

**Assumptions:**
- Working directory is the repository root: `<repo-root>/`
- Python `>=3.10` is available at `python3`
- `venv/` does not yet exist (or: exists at `<repo-root>/venv/`)
- Docker and Docker Compose v2 are installed
- The following files already exist: _list them_
- The following files do NOT exist yet: _list them_

---

## Scope

Files created or modified by this plan — **nothing else changes**:

| Action | Path | Notes |
|--------|------|-------|
| CREATE | `backend/app/main.py` | FastAPI factory |
| CREATE | `backend/requirements.txt` | Pinned deps |
| MODIFY | `backend/.env.example` | Add new env vars |
| DELETE | `<path>` | Reason |

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary key type | UUID v4 | Prevents enumeration attacks; matches target schema |
| ORM mode | SQLAlchemy 2.0 async | Needed for async FastAPI handlers |
| Auth tokens | JWT (HS256) with 30 min access + 7 day refresh | Stateless; refresh rotation on use |
| _Add more_ | | |

---

## Pre-conditions

Before starting, verify these pass:

```bash
python3 --version
# Expected output:
#     Python 3.10.x  (or higher)

git status
# Expected output:
#     On branch phase/1-fresh-scaffold
#     nothing to commit, working tree clean

docker compose version
# Expected output:
#     Docker Compose version v2.x.x
```

---

## Steps

### 1. <Step title>

**What**: _One sentence description of what this step does._
**Why**: _Why this step is necessary at this point in the plan._

```bash
<exact command>
```

Expected output:
    <trimmed relevant stdout/stderr>

---

### 2. Create `backend/app/main.py`

**What**: Scaffold the FastAPI application factory with lifespan management and health endpoint.
**Why**: This is the entry point every other component registers against.

Create `backend/app/main.py` with the following content:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown

app = FastAPI(
    title="School Management System API",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Verify:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 2
curl -s http://localhost:8000/health
```

Expected output:
    {"status":"ok"}

---

### 3. <Next step — continue numbering>

...

---

## Acceptance Criteria

All items must be verified by the agent after completing the steps. A plan is not done until every box can be ticked.

- [ ] `python3 -c "import fastapi; print(fastapi.__version__)"` exits 0 and prints `0.104.x` or higher
- [ ] `curl -s http://localhost:8000/health` returns `{"status":"ok"}`
- [ ] `pytest tests/ -q` collects ≥ N tests and all pass
- [ ] `pytest --cov=app --cov-report=term-missing` shows coverage ≥ X%
- [ ] `docker compose up -d` starts all 4 services without errors
- [ ] `docker compose ps` shows all containers in `running` state
- [ ] OpenAPI schema reachable: `curl -s http://localhost:8000/openapi.json | python3 -m json.tool` exits 0
- [ ] _Add feature-specific checks_

---

## Rollback

If this plan needs to be undone completely:

```bash
# 1. Stop any running services
docker compose down -v

# 2. Remove created files
rm -rf backend/app/main.py  # list all created files

# 3. Restore modified files from git
git checkout -- backend/.env.example  # list all modified files

# 4. Return to prior branch
git checkout <prior-branch>
```

---

## Permission Gate

> This plan is complete when all Acceptance Criteria pass.
>
> **Ready to execute?** Type **"Yes, execute `<filename>`"** to instruct the agent to begin.
> The agent will stop after every phase and report results before proceeding.
