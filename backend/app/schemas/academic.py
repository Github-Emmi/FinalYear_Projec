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


class SubjectStaffInfo(BaseModel):
    """Minimal staff info embedded in SubjectResponse."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None


class SubjectClassroomInfo(BaseModel):
    """Minimal classroom info embedded in SubjectResponse."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class SubjectResponse(BaseResponse):
    name: str
    classroom_id: UUID
    staff_id: Optional[UUID] = None
    staff: Optional[SubjectStaffInfo] = None
    classroom: Optional[SubjectClassroomInfo] = None

    @classmethod
    def _build_staff(cls, obj: object) -> Optional[dict]:
        staff_rel = getattr(obj, "staff", None)
        if staff_rel is None:
            return None
        user = getattr(staff_rel, "user", None)
        return {
            "id": staff_rel.id,
            "first_name": getattr(user, "first_name", None) if user else None,
            "last_name": getattr(user, "last_name", None) if user else None,
            "email": getattr(user, "email", None) if user else None,
        }

    @classmethod
    def _build_classroom(cls, obj: object) -> Optional[dict]:
        classroom_rel = getattr(obj, "classroom", None)
        if classroom_rel is None:
            return None
        return {
            "id": classroom_rel.id,
            "name": classroom_rel.name,
        }

    @classmethod
    def from_orm_obj(cls, obj: object) -> "SubjectResponse":
        """Build response from ORM object with relationships loaded."""
        data = {
            "id": obj.id,  # type: ignore[attr-defined]
            "created_at": obj.created_at,  # type: ignore[attr-defined]
            "updated_at": getattr(obj, "updated_at", None),
            "is_deleted": getattr(obj, "is_deleted", False),
            "name": obj.name,  # type: ignore[attr-defined]
            "classroom_id": obj.classroom_id,  # type: ignore[attr-defined]
            "staff_id": obj.staff_id,  # type: ignore[attr-defined]
            "staff": cls._build_staff(obj),
            "classroom": cls._build_classroom(obj),
        }
        return cls.model_validate(data)
