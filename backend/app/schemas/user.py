"""User schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole
from app.schemas.base import BaseResponse


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    role: UserRole = UserRole.student


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponse(BaseResponse):
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    last_login: Optional[datetime] = None
