"""LeaveRequest model."""

from __future__ import annotations

import enum

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class LeaveType(str, enum.Enum):
    sick = "sick"
    casual = "casual"
    emergency = "emergency"
    maternity = "maternity"
    other = "other"


class LeaveStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class LeaveRequest(BaseModel):
    __tablename__ = "leave_requests"

    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    leave_type = Column(
        String(50), default=LeaveType.casual.value, nullable=False
    )
    status = Column(String(50), default=LeaveStatus.pending.value, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    reviewed_by_id = Column(
        Uuid, ForeignKey("staff_profiles.id"), nullable=True
    )
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user = relationship("User", back_populates="leave_requests")
    reviewed_by = relationship("StaffProfile", back_populates="leave_requests_reviewed")
