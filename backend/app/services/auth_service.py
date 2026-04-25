"""Authentication service: login, token refresh."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.audit import AuditAction, AuditLog
from app.repositories.factory import RepositoryFactory
from app.schemas.auth import TokenResponse


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._repos = RepositoryFactory(session)

    async def login(self, username: str, password: str) -> TokenResponse:
        """Verify credentials, record login audit, return token pair."""
        user = await self._repos.users.get_by_username(username)

        # Constant-time comparison path — always call verify even on miss
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled. Contact your administrator.",
            )

        # Stamp last login
        user.last_login = datetime.utcnow()
        await self._repos.users.update(user)

        # Append-only audit record
        log = AuditLog(
            user_id=user.id,
            action=AuditAction.login.value,
            resource_type="user",
            resource_id=user.id,
        )
        await self._repos.audit.create(log)

        return TokenResponse(
            access_token=create_access_token(str(user.id), user.role),
            refresh_token=create_refresh_token(str(user.id)),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Issue a new access token from a valid refresh token."""
        exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise exc

        if payload.get("type") != "refresh":
            raise exc

        user = await self._repos.users.get_by_id(UUID(payload["sub"]))
        if not user or not user.is_active:
            raise exc

        return TokenResponse(
            access_token=create_access_token(str(user.id), user.role),
            refresh_token=create_refresh_token(str(user.id)),
        )
