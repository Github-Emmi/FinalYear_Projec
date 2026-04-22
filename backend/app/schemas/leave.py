"""Leave request schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.leave import LeaveStatus, LeaveType
from app.schemas.base import BaseResponse


class LeaveRequestCreate(BaseModel):
    user_id: UUID
    leave_type: LeaveType = LeaveType.casual
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveRequestUpdate(BaseModel):
    leave_type: Optional[LeaveType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None


class LeaveRequestReview(BaseModel):
    """Staff action: approve or reject a leave request."""

    status: LeaveStatus
    reviewed_by_id: UUID
    rejection_reason: Optional[str] = None


class LeaveRequestResponse(BaseResponse):
    user_id: UUID
    leave_type: str
    status: str
    start_date: date
    end_date: date
    reason: Optional[str] = None
    reviewed_by_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
