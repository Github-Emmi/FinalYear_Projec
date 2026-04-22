"""StaffProfile schemas."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import BaseResponse


class StaffProfileCreate(BaseModel):
    user_id: UUID
    department_id: Optional[UUID] = None
    designation: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None


class StaffProfileUpdate(BaseModel):
    department_id: Optional[UUID] = None
    designation: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None


class StaffProfileResponse(BaseResponse):
    user_id: UUID
    department_id: Optional[UUID] = None
    designation: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
