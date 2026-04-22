"""Auth schemas — login, token responses, refresh."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
