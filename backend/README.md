# Phase 1: School Management System - FastAPI Backend Migration

## 🎯 Project Overview

This is **Phase 1** of the School Management System architecture migration:
- **Current**: Django 4.2.23 + SQLite/MySQL
- **Target**: FastAPI + PostgreSQL + Redis + RabbitMQ
- **Focus**: Backend API only (NO frontend changes)
- **Status**: Project Initialization Complete ✅

---

## 📊 Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | FastAPI 0.104+ | Async HTTP server |
| **Language** | Python 3.10+ | Type-safe backend |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **Database** | PostgreSQL 15 | Primary data store |
| **Cache** | Redis 7 | Sessions, caching, rate limiting |
| **Task Queue** | RabbitMQ 3.12 | Async job processing |
| **Task Worker** | Celery 5.3+ | Background job execution |
| **Async Driver** | asyncpg | PostgreSQL async connector |
| **Validation** | Pydantic 2.5+ | Request/response validation |
| **Auth** | JWT + OAuth2.0 | Stateless authentication |
| **File Storage** | Cloudinary | Cloud file hosting (maintained) |
| **OpenAI** | GPT-4o-mini | Auto-grading essays |

---

## 📁 Project Structure

```
backend/
│
├── app/                              # Main application package
│   ├── __init__.py
│   ├── main.py                       # FastAPI application factory
│   │
│   ├── core/                         # Core application modules
│   │   ├── __init__.py
│   │   ├── config.py                 # Settings (env-based)
│   │   ├── database.py               # SQLAlchemy setup, session management
│   │   ├── security.py               # JWT, password hashing, encryption
│   │   ├── exceptions.py             # Custom exception classes
│   │   └── logging_config.py         # Logging configuration
│   │
│   ├── models/                       # SQLAlchemy ORM models
│   │   ├── __init__.py               # Base classes & mixins
│   │   ├── user.py                   # ⏳ Phase 2
│   │   ├── student.py                # ⏳ Phase 2
│   │   ├── staff.py                  # ⏳ Phase 2
│   │   ├── quiz.py                   # ⏳ Phase 2
│   │   ├── assignment.py             # ⏳ Phase 2
│   │   ├── attendance.py             # ⏳ Phase 2
│   │   └── ...
│   │
│   ├── schemas/                      # Pydantic request/response models
│   │   ├── __init__.py               # Base schemas
│   │   ├── user.py                   # ⏳ Phase 2
│   │   ├── student.py                # ⏳ Phase 2
│   │   ├── quiz.py                   # ⏳ Phase 2
│   │   ├── assignment.py             # ⏳ Phase 2
│   │   └── ...
│   │
│   ├── repositories/                 # Data access layer (replaces Django ORM)
│   │   ├── __init__.py
│   │   ├── base.py                   # ⏳ Phase 2 - Generic CRUD
│   │   ├── user_repository.py        # ⏳ Phase 2
│   │   ├── student_repository.py     # ⏳ Phase 2
│   │   └── ...
│   │
│   ├── services/                     # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py           # ⏳ Phase 2 - JWT, passwords
│   │   ├── user_service.py           # ⏳ Phase 2
│   │   ├── student_service.py        # ⏳ Phase 2
│   │   ├── quiz_service.py           # ⏳ Phase 2
│   │   ├── assessment_service.py     # ⏳ Phase 2 - AI grading
│   │   └── ...
│   │
│   ├── api/                          # Route handlers (REST endpoints)
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py             # ⏳ Phase 2
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── auth.py           # ⏳ Phase 2 - /api/v1/auth
│   │           ├── admin.py          # ⏳ Phase 2 - /api/v1/admin
│   │           ├── staff.py          # ⏳ Phase 2 - /api/v1/staff
│   │           ├── students.py       # ⏳ Phase 2 - /api/v1/students
│   │           ├── quizzes.py        # ⏳ Phase 2 - /api/v1/quizzes
│   │           ├── assignments.py    # ⏳ Phase 2 - /api/v1/assignments
│   │           └── ...
│   │
│   ├── websockets/                   # WebSocket handlers (real-time)
│   │   ├── __init__.py
│   │   ├── chat_handler.py           # ⏳ Phase 2 - Messages
│   │   ├── notifications_handler.py  # ⏳ Phase 2 - Alerts
│   │   ├── manager.py                # ⏳ Phase 2 - Connection management
│   │   └── router.py                 # ⏳ Phase 2
│   │
│   ├── tasks/                        # Celery async tasks
│   │   ├── __init__.py
│   │   ├── quiz_grading.py           # ⏳ Phase 2 - Auto-grade essays
│   │   ├── email_tasks.py            # ⏳ Phase 2 - Send emails
│   │   ├── analytics_tasks.py        # ⏳ Phase 2 - Reports
│   │   └── celery_app.py             # ⏳ Phase 2 - Celery config
│   │
│   └── middleware/                   # Request/response middleware
│       ├── __init__.py               # LoggingMiddleware (✅ created)
│       ├── exception_handler.py      # ✅ Exception handlers (created)
│       ├── auth_middleware.py        # ⏳ Phase 2 - JWT validation
│       └── rate_limit_middleware.py  # ⏳ Phase 2 - Rate limiting
│
├── migrations/                       # Alembic database migrations
│   ├── alembic.ini                   # ⏳ Phase 2
│   ├── env.py                        # ⏳ Phase 2
│   ├── script.py.mako                # ⏳ Phase 2
│   └── versions/                     # ⏳ Phase 2
│       ├── 001_initial_schema.py     # Create all tables
│       └── ...
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # ⏳ Phase 2 - Pytest fixtures
│   ├── unit/                         # Unit tests
│   │   ├── test_repositories.py      # ⏳ Phase 2
│   │   ├── test_services.py          # ⏳ Phase 2
│   │   └── ...
│   ├── integration/                  # Integration tests
│   │   ├── test_auth_endpoints.py    # ⏳ Phase 2
│   │   ├── test_student_endpoints.py # ⏳ Phase 2
│   │   └── ...
│   └── e2e/                          # End-to-end workflows
│       ├── test_quiz_flow.py         # ⏳ Phase 2
│       └── ...
│
├── docker/                           # Docker configuration
│   ├── Dockerfile                    # ✅ Multi-stage build (created)
│   └── docker-compose.yml            # ⏳ Development compose (created)
│
├── requirements.txt                  # ✅ Dependencies (created)
├── pyproject.toml                    # ✅ Project config (created)
├── main.py                           # ✅ Entry point (created)
├── .env.example                      # ✅ Environment template (created)
├── .gitignore                        # ✅ Git ignore (created)
├── README.md                         # ✅ This file (created)
└── ARCHITECTURE.md                   # ⏳ Phase 2 - Detailed architecture docs
```

**Legend**: ✅ = Complete | ⏳ = Next Phase | 🔄 = In Progress

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git

### 1. Copy Environment Variables

```bash
cd backend
cp .env.example .env
```

Edit `.env` with your local/development values.

### 2. Start Services with Docker Compose

```bash
docker-compose up -d
```

This starts:
- ✅ FastAPI (port 8000)
- ✅ PostgreSQL (port 5432)
- ✅ Redis (port 6379)
- ✅ RabbitMQ (port 5672, UI: 15672)
- ✅ Adminer (PostgreSQL UI: port 8080)
- ✅ Redis Commander (Redis UI: port 8081)

### 3. Create Virtual Environment (Local Development)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 4. Run Application (Local)

```bash
python main.py
```

Or with auto-reload:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access Application

- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **PostgreSQL UI**: http://localhost:8080
- **Redis UI**: http://localhost:8081
- **RabbitMQ UI**: http://localhost:15672 (guest/guest)

---

## 📝 Configuration

### Environment Variables (.env)

Copy `.env.example` to `.env` and configure:

```bash
# Development
ENVIRONMENT=development
DEBUG=true

# Database
DB_USER=school_user
DB_PASSWORD=school_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=school_management

# Security (CHANGE IN PRODUCTION)
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256

# External Services
OPENAI_API_KEY=sk-...
CLOUDINARY_API_KEY=your-key
CLOUDINARY_API_SECRET=your-secret
```

---

## ✨ Key Features (Phase 1)

### ✅ Completed

- [x] FastAPI application factory with lifespan management
- [x] PostgreSQL connection pooling with asyncpg
- [x] Redis client setup
- [x] JWT security: password hashing (bcrypt), token creation/verification
- [x] Custom exception handling with structured error responses
- [x] Request logging with request ID tracking
- [x] CORS middleware configuration
- [x] Environment-based configuration (Pydantic Settings)
- [x] Comprehensive logging (JSON + file output)
- [x] Base ORM models with mixins (Timestamps, SoftDelete, UUIDs)
- [x] Docker & Docker Compose setup
- [x] Alembic migration framework structure
- [x] pytest test framework structure

### ⏳ Phase 2 (SQLAlchemy Models)

- [ ] All 20+ SQLAlchemy ORM models
- [ ] Pydantic schemas for all endpoints
- [ ] Repository pattern (data access layer)
- [ ] Service layer (business logic)
- [ ] API endpoints (auth, admin, staff, student)
- [ ] Authentication & authorization
- [ ] WebSocket handlers
- [ ] Celery tasks

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/unit/test_something.py

# Verbose output
pytest -v
```

### Test Structure

```
tests/
├── unit/          # Service, repository unit tests
├── integration/   # API endpoint tests
└── e2e/          # Full workflow tests (quiz submission, grading, etc.)
```

---

## 📦 Docker Commands

### Build Image

```bash
docker build -f docker/Dockerfile -t school-ms:latest .
```

### Run Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Reset database
docker-compose down -v
```

### Access Container Shell

```bash
docker-compose exec app bash
```

---

## 🔐 Security Notes

### Production Checklist

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Set `DEBUG=false`
- [ ] Use strong database passwords
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS to specific origins (not *)
- [ ] Set up API rate limiting
- [ ] Enable JWT token refresh rotation
- [ ] Use environment secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)
- [ ] Enable database SSL connections
- [ ] Configure WAF (Web Application Firewall)

---

## 📚 API Documentation

### Swagger UI
Interactive API explorer at `/docs`

### ReDoc
Beautiful API documentation at `/redoc`

### OpenAPI Schema
Machine-readable spec at `/openapi.json`

---

## 🔄 Deployment

### Production Usage

1. Add environment variables to deployment platform (AWS, GCP, Azure, etc.)
2. Build Docker image
3. Push to container registry
4. Deploy with orchestration (Kubernetes, Docker Swarm, etc.)

Example Kubernetes deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: school-ms-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: school-ms-api
  template:
    metadata:
      labels:
        app: school-ms-api
    spec:
      containers:
      - name: api
        image: school-ms:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: connection-string
```

---

## 📞 Support & Contribution

### File Structure Issues?

Check the directory structure:
```bash
find phase1_migration -type f -name "*.py" | head -20
```

### Database Issues?

```bash
# Check PostgreSQL status
docker-compose logs postgres

# Connect directly
psql -h localhost -U school_user -d school_management
```

### Redis Issues?

```bash
# Check Redis
docker-compose logs redis

# Connect with redis-cli
redis-cli -h localhost ping
```

---

## 🗓️ Phase Timeline

| Phase | Focus | Duration | Status |
|-------|-------|----------|--------|
| **1** | Project setup, core infrastructure | Week 1 ✅ | ✅ Complete |
| **2** | Models, schemas, repositories, services | Weeks 2-3 | ⏳ Next |
| **3** | API endpoints, auth, RBAC | Weeks 4-5 | ⏳ Future |
| **4** | WebSockets, Celery tasks, real-time | Weeks 6-7 | ⏳ Future |
| **5** | Testing, documentation, deployment | Week 8 | ⏳ Future |

---

## 📖 References

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/20/)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
- [pytest Documentation](https://docs.pytest.org/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/docs/)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/getstarted.html)
- [Celery Documentation](https://docs.celeryproject.io/)

---

**Last Updated**: March 3, 2026  
**Version**: 1.0.0  
**Phase**: 1 - Project Initialization ✅
