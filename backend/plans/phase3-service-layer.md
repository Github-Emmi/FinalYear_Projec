# ExecPlan: Phase 3 — Service Layer

## Context

Phase 2 delivered 20 ORM models, 11 Pydantic schema files, 13 repositories, and
Alembic migration 001. All 59 unit tests pass on branch `phase/1-fresh-scaffold`.

Phase 3 adds the complete service layer: 10 domain service classes, async SMTP email,
OpenAI GPT-4o-mini AI grading, and an RBAC FastAPI dependency (`require_role`).
No API endpoints or routers are wired in this phase (Phase 4).

## Scope

**New files:**
- `backend/app/api/deps.py` — OAuth2 bearer extraction, `get_current_user`, `require_role`
- `backend/app/services/auth_service.py`
- `backend/app/services/user_service.py`
- `backend/app/services/student_service.py`
- `backend/app/services/staff_service.py`
- `backend/app/services/assessment_service.py`
- `backend/app/services/assignment_service.py`
- `backend/app/services/attendance_service.py`
- `backend/app/services/leave_service.py`
- `backend/app/services/notification_service.py`
- `backend/app/services/analytics_service.py`
- `backend/app/services/email_service.py`
- `backend/tests/unit/test_services.py`

**Modified files:**
- `backend/requirements.txt` — add `aiosmtplib>=2.0.2`, `openai>=1.50.0`
- `backend/app/core/config.py` — add OPENAI and SMTP settings
- `backend/app/services/__init__.py` — export all service classes

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| AI grading | OpenAI GPT-4o-mini async client, lazy import | Fast, cheap, degrades gracefully when no API key |
| SMTP | `aiosmtplib.send()` helper | Simplest async send; skips silently when SMTP_USER unset |
| RBAC | Closure-based `require_role(*roles)` FastAPI dependency | Composable, zero extra middleware |
| Password hashing | Reuse `app.core.security` (bcrypt, cost=12) | Already hardened in Phase 1 |
| AI grading fallback | `(False, 0.0, "AI grading unavailable")` | Never crashes; manual review handles the rest |
| Token type check | Reject access tokens on refresh endpoint via `payload["type"] == "refresh"` | Prevents token confusion attacks |

## Steps

### 1. Add dependencies to requirements.txt
Add after the pydantic section:
```
aiosmtplib>=2.0.2
openai>=1.50.0
```

### 2. Add OPENAI + SMTP settings to config.py
Add after the CORS section:
```python
# ── OpenAI ─────────────────────────────────────────────────────────────────
OPENAI_API_KEY: Optional[str] = Field(default=None)
OPENAI_MODEL: str = Field(default="gpt-4o-mini")

# ── SMTP ───────────────────────────────────────────────────────────────────
SMTP_HOST: str = Field(default="localhost")
SMTP_PORT: int = Field(default=587)
SMTP_USER: Optional[str] = Field(default=None)
SMTP_PASSWORD: Optional[str] = Field(default=None)
SMTP_FROM: str = Field(default="noreply@school.edu")
SMTP_TLS: bool = Field(default=True)
```

### 3. Create `app/api/deps.py`
OAuth2 password bearer scheme, `get_current_user` async dependency, `require_role` closure.

### 4–13. Create all 10 service files
Sequential classes, one per file. Each takes `AsyncSession` and wraps `RepositoryFactory`.

### 14. Update `services/__init__.py`
Export all 10 service classes.

### 15. Create `tests/unit/test_services.py`
Import + isinstance checks (no DB required). 40+ test functions.

### 16. Install new packages & run tests
```bash
pip install aiosmtplib openai
python -m pytest tests/unit/ -v
```
Expected: `75+ passed`

### 17. Git commit
```
feat: Phase 3 — service layer (10 services, RBAC deps, AI grading, async email)
```

## Acceptance Criteria

- [ ] `python -c "from app.services import AuthService, UserService"` exits 0
- [ ] `python -c "from app.api.deps import get_current_user, require_role"` exits 0
- [ ] `python -m pytest tests/unit/ -v` → 75+ passed, 0 failed
- [ ] `require_role("admin")` returns a callable FastAPI dependency
- [ ] `AssessmentService._ai_grade` falls back gracefully when OPENAI_API_KEY is None

## Rollback

```bash
git checkout HEAD -- backend/app/services/__init__.py backend/app/core/config.py backend/requirements.txt
git rm backend/app/api/deps.py backend/app/services/{auth,user,student,staff,assessment,assignment,attendance,leave,notification,analytics,email}_service.py backend/tests/unit/test_services.py
```
