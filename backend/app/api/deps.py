"""FastAPI dependencies: current-user extraction and RBAC role guard.

Usage in a router::

    from app.api.deps import get_current_user, require_role

    @router.get("/admin-only")
    async def admin_endpoint(user: User = Depends(require_role("admin"))):
        ...

    @router.get("/staff-or-admin")
    async def staff_endpoint(user: User = Depends(require_role("admin", "staff"))):
        ...
"""

from __future__ import annotations

from typing import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.repositories.factory import RepositoryFactory

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode Bearer token and return the active User, or raise 401."""
    try:
        payload = decode_token(token)
    except JWTError:
        raise _CREDENTIALS_EXCEPTION

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise _CREDENTIALS_EXCEPTION

    # Reject refresh tokens used as access tokens
    if payload.get("type") == "refresh":
        raise _CREDENTIALS_EXCEPTION

    user = await RepositoryFactory(db).users.get_by_id(UUID(user_id))
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user


def require_role(*roles: str) -> Callable:
    """Return a FastAPI dependency that allows only users with one of *roles*.

    Raises HTTP 403 if the authenticated user's role is not in *roles*.
    """

    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access requires one of: {', '.join(roles)}",
            )
        return current_user

    return _guard


# ── Convenience pre-built dependencies ────────────────────────────────────────
# Use these in routers for readability:
#   @router.post("/...", dependencies=[Depends(AdminOnly)])

AdminOnly = require_role("admin")
StaffOrAdmin = require_role("admin", "staff")
AnyAuthenticatedUser = require_role("admin", "staff", "student")
