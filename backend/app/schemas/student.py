"""StudentProfile schemas."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, model_validator

from app.schemas.base import BaseResponse

if TYPE_CHECKING:
    pass


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


class StudentCreateWithUser(BaseModel):
    """Combined schema for creating a user + student profile in one call."""
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    roll_number: Optional[str] = None
    classroom_id: Optional[UUID] = None
    session_year_id: Optional[UUID] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


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
    # Relationship fields (populated when eagerly loaded)
    user: Optional[Dict[str, Any]] = None
    classroom: Optional[Dict[str, Any]] = None
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def _extract_relations(cls, data: Any) -> Any:
        """When building from ORM object, pull nested user/classroom dicts."""
        if not isinstance(data, dict):
            # ORM model
            obj = data
            result: Dict[str, Any] = {
                field: getattr(obj, field, None)
                for field in (
                    "id", "created_at", "updated_at", "is_deleted",
                    "user_id", "classroom_id", "session_year_id",
                    "roll_number", "date_of_birth", "gender",
                    "address", "phone", "profile_picture",
                )
            }
            # Nested user
            user_obj = getattr(obj, "user", None)
            if user_obj is not None:
                result["user"] = {
                    "id": str(user_obj.id),
                    "username": user_obj.username,
                    "email": user_obj.email,
                    "first_name": user_obj.first_name,
                    "last_name": user_obj.last_name,
                    "role": user_obj.role,
                    "is_active": user_obj.is_active,
                }
                result["is_active"] = user_obj.is_active
            # Nested classroom
            classroom_obj = getattr(obj, "classroom", None)
            if classroom_obj is not None:
                result["classroom"] = {
                    "id": str(classroom_obj.id),
                    "name": classroom_obj.name,
                    "grade_level": getattr(classroom_obj, "grade_level", None),
                    "section": getattr(classroom_obj, "section", None),
                }
            return result
        return data
