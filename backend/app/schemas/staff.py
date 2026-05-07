"""StaffProfile schemas."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, model_validator

from app.schemas.base import BaseResponse


class StaffProfileCreate(BaseModel):
    user_id: UUID
    department_id: Optional[UUID] = None
    designation: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None


class StaffCreateWithUser(BaseModel):
    """Combined schema for creating a user + staff profile in one call."""
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    department_id: Optional[UUID] = None
    designation: Optional[str] = None
    phone: Optional[str] = None


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
    # Relationship fields (populated when eagerly loaded)
    user: Optional[Dict[str, Any]] = None
    department: Optional[Dict[str, Any]] = None
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def _extract_relations(cls, data: Any) -> Any:
        """When building from ORM object, pull nested user/department dicts."""
        if not isinstance(data, dict):
            obj = data
            result: Dict[str, Any] = {
                field: getattr(obj, field, None)
                for field in (
                    "id", "created_at", "updated_at", "is_deleted",
                    "user_id", "department_id", "designation",
                    "phone", "profile_picture",
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
            # Nested department
            dept_obj = getattr(obj, "department", None)
            if dept_obj is not None:
                result["department"] = {
                    "id": str(dept_obj.id),
                    "name": dept_obj.name,
                    "code": getattr(dept_obj, "code", None),
                }
            return result
        return data
