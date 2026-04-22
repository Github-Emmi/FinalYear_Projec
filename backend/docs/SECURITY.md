# Security Design: School Management System

## Authentication Flow

1. Client POSTs credentials to `POST /api/v1/auth/login`
2. Server verifies password against bcrypt hash (cost 12)
3. Server issues: `access_token` (JWT, 30 min TTL) + `refresh_token` (JWT, 7 day TTL)
4. Client stores tokens (access in memory, refresh in HttpOnly cookie)
5. Client attaches `Authorization: Bearer <access_token>` to every request
6. On 401, client exchanges refresh token at `POST /api/v1/auth/refresh`
7. Server rotates refresh token (old token invalidated, new token issued)
8. On logout, refresh token is revoked (stored in Redis blacklist)

## JWT Claims

```json
{
  "sub": "<user UUID as string>",
  "role": "admin | staff | student",
  "exp": "<unix timestamp>",
  "iat": "<unix timestamp>",
  "jti": "<token UUID — used for blacklisting>"
}
```

`jti` (JWT ID) is used to blacklist refresh tokens in Redis after logout or rotation.
Key format in Redis: `blacklist:jti:<jti>` with TTL equal to remaining token lifetime.

## RBAC Matrix

| Role | Capability |
|------|-----------|
| `admin` | Full CRUD on all entities; user management; analytics |
| `staff` | CRUD on own classes, assignments, quizzes, attendance; read students |
| `student` | Read own data; submit assignments and quizzes; view own grades |

Enforcement: FastAPI `Depends()` on each endpoint calling `require_role(["admin"])`.
The role is read from the JWT `role` claim — no database lookup on each request.

## Password Policy

- Minimum 8 characters
- bcrypt cost factor 12 (≈250ms hash time — slow enough to resist brute force)
- No plaintext passwords stored anywhere
- Password reset flow: time-limited (15 min) signed token sent by email

## OWASP Top 10 Mitigations

| Risk | Mitigation |
|------|-----------|
| A01 Broken Access Control | RBAC on every endpoint via `Depends(require_role(...))` |
| A02 Cryptographic Failures | bcrypt(12) passwords; HS256 JWT; HTTPS required in production |
| A03 Injection | SQLAlchemy parameterised queries only; no f-string SQL |
| A05 Security Misconfiguration | `DEBUG=false`, specific CORS origins, no wildcard in production |
| A07 Auth Failures | Short access token TTL; refresh rotation; blacklist on logout |
| A09 Security Logging | Audit log table; auth events logged with user ID + IP |

## Production Secrets Checklist

- [ ] `SECRET_KEY` replaced with 64-byte random value: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- [ ] `DEBUG=false`
- [ ] Database password is not `school_password`
- [ ] `CORS_ORIGINS` set to specific frontend domain(s), not `*`
- [ ] Redis protected with `REDIS_PASSWORD`
- [ ] RabbitMQ `RABBITMQ_DEFAULT_USER`/`PASS` changed from `guest/guest`
- [ ] HTTPS/TLS termination at reverse proxy (nginx or Traefik)
