"""Academic schemas: Department, SessionYear, ClassRoom, Subject."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.base import BaseResponse


# ── Department ─────────────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None


class DepartmentResponse(BaseResponse):
    name: str


# ── SessionYear ────────────────────────────────────────────────────────────────

class SessionYearCreate(BaseModel):
    start_year: int
    end_year: int
    is_current: bool = False


class SessionYearUpdate(BaseModel):
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_current: Optional[bool] = None


class SessionYearResponse(BaseResponse):
    start_year: int
    end_year: int
    is_current: bool


# ── ClassRoom ──────────────────────────────────────────────────────────────────

class ClassRoomCreate(BaseModel):
    name: str
    department_id: UUID


class ClassRoomUpdate(BaseModel):
    name: Optional[str] = None
    department_id: Optional[UUID] = None


class ClassRoomResponse(BaseResponse):
    name: str
    department_id: UUID


# ── Subject ────────────────────────────────────────────────────────────────────

class SubjectCreate(BaseModel):
    name: str
    classroom_id: UUID
    staff_id: Optional[UUID] = None


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    classroom_id: Optional[UUID] = None
    staff_id: Optional[UUID] = None


class SubjectResponse(BaseResponse):
    name: str
    classroom_id: UUID
    staff_id: Optional[UUID] = None
