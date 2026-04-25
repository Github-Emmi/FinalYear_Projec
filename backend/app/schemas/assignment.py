"""Assignment schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.assignment import AssignmentStatus, SubmissionStatus
from app.schemas.base import BaseResponse


# ── Assignment ─────────────────────────────────────────────────────────────────

class AssignmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    subject_id: UUID
    staff_id: UUID
    status: AssignmentStatus = AssignmentStatus.draft
    due_date: Optional[datetime] = None
    max_score: float = 100.0
    file_url: Optional[str] = None
    ai_grading_enabled: bool = False


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[AssignmentStatus] = None
    due_date: Optional[datetime] = None
    max_score: Optional[float] = None
    file_url: Optional[str] = None
    ai_grading_enabled: Optional[bool] = None


class AssignmentResponse(BaseResponse):
    title: str
    description: Optional[str] = None
    subject_id: UUID
    staff_id: UUID
    status: str
    due_date: Optional[datetime] = None
    max_score: float
    file_url: Optional[str] = None
    ai_grading_enabled: bool


# ── AssignmentSubmission ───────────────────────────────────────────────────────

class SubmissionCreate(BaseModel):
    assignment_id: UUID
    student_id: UUID
    file_url: Optional[str] = None


class SubmissionUpdate(BaseModel):
    status: Optional[SubmissionStatus] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    graded_at: Optional[datetime] = None
    ai_feedback: Optional[str] = None


class SubmissionResponse(BaseResponse):
    assignment_id: UUID
    student_id: UUID
    status: str
    file_url: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    submitted_at: Optional[datetime] = None
    graded_at: Optional[datetime] = None
    ai_feedback: Optional[str] = None
