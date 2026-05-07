"""Timetable schemas."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.schemas.base import BaseResponse


class TimetableEntryCreate(BaseModel):
    classroom_id: UUID
    subject_id: UUID
    staff_id: UUID
    session_year_id: UUID
    day_of_week: int  # 0=Mon … 6=Sun
    start_time: str  # "08:00"
    end_time: str    # "09:00"
    period_number: Optional[int] = None
    notes: Optional[str] = None


class TimetableEntryUpdate(BaseModel):
    day_of_week: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    period_number: Optional[int] = None
    notes: Optional[str] = None


class TimetableEntryResponse(BaseResponse):
    classroom_id: UUID
    subject_id: UUID
    staff_id: UUID
    session_year_id: UUID
    day_of_week: int
    start_time: str
    end_time: str
    period_number: Optional[int] = None
    notes: Optional[str] = None
    # Nested
    classroom: Optional[Dict[str, Any]] = None
    subject: Optional[Dict[str, Any]] = None
    staff: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def _extract_relations(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            obj = data
            result: Dict[str, Any] = {
                field: getattr(obj, field, None)
                for field in (
                    "id", "created_at", "updated_at", "is_deleted",
                    "classroom_id", "subject_id", "staff_id",
                    "session_year_id", "day_of_week", "start_time",
                    "end_time", "period_number", "notes",
                )
            }
            cr = getattr(obj, "classroom", None)
            if cr:
                result["classroom"] = {"id": str(cr.id), "name": cr.name}
            sub = getattr(obj, "subject", None)
            if sub:
                result["subject"] = {"id": str(sub.id), "name": sub.name}
            st = getattr(obj, "staff", None)
            if st:
                user = getattr(st, "user", None)
                result["staff"] = {
                    "id": str(st.id),
                    "name": f"{user.first_name} {user.last_name}" if user else str(st.id),
                }
            return result
        return data
