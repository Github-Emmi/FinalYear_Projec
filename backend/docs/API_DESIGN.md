# API Design: School Management System

## Base URL

All v1 endpoints are prefixed: `/api/v1/`

## Versioning

URL-based versioning (`/api/v1/`, `/api/v2/`). The `v1` router is defined in
`app/api/v1/router.py` and included in `app/main.py` with prefix `/api/v1`.

## Authentication

All endpoints except `/api/v1/auth/login` and `/api/v1/auth/register` require
a Bearer JWT token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

The token is verified by `app/middleware/auth_middleware.py` (Phase 3).
The token payload contains: `sub` (user UUID as string), `role`, `exp`.

## Standard Error Contract

Every error response uses this shape:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Student with id 'abc' not found.",
    "details": {}
  }
}
```

HTTP status codes:
- `400` Bad Request — validation failure or malformed input
- `401` Unauthorized — missing or invalid token
- `403` Forbidden — valid token but insufficient role
- `404` Not Found — resource does not exist (or is soft-deleted)
- `409` Conflict — unique constraint violation (e.g. duplicate email)
- `422` Unprocessable Entity — Pydantic validation failure (FastAPI default)
- `500` Internal Server Error — unhandled exception

## Pagination

All list endpoints accept these query parameters and return this envelope:

Query params: `?page=1&page_size=20`

Response:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8
}
```

`page` is 1-indexed. Maximum `page_size` is 100.

## Planned Endpoints (Phase 4 implementation)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/login` | public | Exchange credentials for access + refresh tokens |
| POST | `/api/v1/auth/refresh` | public | Exchange refresh token for new access token |
| POST | `/api/v1/auth/logout` | user | Revoke refresh token |
| GET | `/api/v1/users/me` | user | Get own profile |
| GET/POST | `/api/v1/admin/users` | admin | List/create users |
| GET/PATCH/DELETE | `/api/v1/admin/users/{id}` | admin | Manage single user |
| GET/POST | `/api/v1/students/` | staff,admin | List/create students |
| GET/PATCH | `/api/v1/students/{id}` | staff,admin,student | Get/update student |
| GET/POST | `/api/v1/staff/` | admin | List/create staff |
| GET/POST | `/api/v1/quizzes/` | staff | List/create quizzes |
| POST | `/api/v1/quizzes/{id}/attempt` | student | Submit quiz attempt |
| GET/POST | `/api/v1/assignments/` | staff | List/create assignments |
| POST | `/api/v1/assignments/{id}/submit` | student | Submit assignment |
| GET/POST | `/api/v1/attendance/` | staff | Record/list attendance |
| GET | `/api/v1/analytics/dashboard` | admin,staff | Dashboard stats |
| GET | `/api/v1/health` | public | Health check |
