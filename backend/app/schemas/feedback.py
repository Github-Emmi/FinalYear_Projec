"""Feedback schemas."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class FeedbackStaffCreate(BaseModel):
    """Student submits feedback about a staff member."""

    staff_id: UUID
    student_id: UUID
    feedback_text: str
    rating: Optional[int] = Field(None, ge=1, le=5)


class FeedbackStaffUpdate(BaseModel):
    feedback_text: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)


class FeedbackStaffResponse(BaseResponse):
    staff_id: UUID
    student_id: UUID
    feedback_text: str
    rating: Optional[int] = None


class FeedbackStudentCreate(BaseModel):
    """Staff submits feedback about a student."""

    student_id: UUID
    staff_id: UUID
    feedback_text: str
    rating: Optional[int] = Field(None, ge=1, le=5)


class FeedbackStudentUpdate(BaseModel):
    feedback_text: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)


class FeedbackStudentResponse(BaseResponse):
    student_id: UUID
    staff_id: UUID
    feedback_text: str
    rating: Optional[int] = None
