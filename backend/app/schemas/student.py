"""StudentProfile schemas."""

from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import BaseResponse


class StudentProfileCreate(BaseModel):
    user_id: UUID
    classroom_id: Optional[UUID] = None
    session_year_id: Optional[UUID] = None
    roll_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None


class StudentProfileUpdate(BaseModel):
    classroom_id: Optional[UUID] = None
    session_year_id: Optional[UUID] = None
    roll_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None


class StudentProfileResponse(BaseResponse):
    user_id: UUID
    classroom_id: Optional[UUID] = None
    session_year_id: Optional[UUID] = None
    roll_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
