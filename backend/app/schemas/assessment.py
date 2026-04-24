"""Assessment schemas: Quiz, Question, QuizAttempt, QuizResult."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.assessment import AttemptStatus, QuestionType, QuizStatus
from app.schemas.base import BaseResponse


# ── Quiz ───────────────────────────────────────────────────────────────────────

class QuizCreate(BaseModel):
    title: str
    description: Optional[str] = None
    subject_id: UUID
    staff_id: UUID
    status: QuizStatus = QuizStatus.draft
    time_limit_minutes: Optional[int] = None
    max_attempts: int = 1
    pass_score: float = 50.0
    due_date: Optional[datetime] = None
    ai_grading_enabled: bool = False


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[QuizStatus] = None
    time_limit_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    pass_score: Optional[float] = None
    due_date: Optional[datetime] = None
    ai_grading_enabled: Optional[bool] = None


class QuizResponse(BaseResponse):
    title: str
    description: Optional[str] = None
    subject_id: UUID
    staff_id: UUID
    status: str
    time_limit_minutes: Optional[int] = None
    max_attempts: int
    pass_score: float
    due_date: Optional[datetime] = None
    ai_grading_enabled: bool


# ── Question ───────────────────────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    quiz_id: Optional[UUID] = None
    text: str
    question_type: QuestionType = QuestionType.multiple_choice
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_answer: Optional[str] = None
    marks: float = 1.0
    order: int = 0


class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    question_type: Optional[QuestionType] = None
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_answer: Optional[str] = None
    marks: Optional[float] = None
    order: Optional[int] = None


class QuestionResponse(BaseResponse):
    quiz_id: UUID
    text: str
    question_type: str
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_answer: Optional[str] = None
    marks: float
    order: int


# ── QuizAttempt ────────────────────────────────────────────────────────────────

class QuizAttemptCreate(BaseModel):
    quiz_id: UUID
    student_id: UUID


class QuizAttemptUpdate(BaseModel):
    status: Optional[AttemptStatus] = None
    score: Optional[float] = None
    submitted_at: Optional[datetime] = None
    graded_at: Optional[datetime] = None
    ai_feedback: Optional[str] = None


class QuizAttemptResponse(BaseResponse):
    quiz_id: UUID
    student_id: UUID
    status: str
    score: Optional[float] = None
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    graded_at: Optional[datetime] = None
    ai_feedback: Optional[str] = None


# ── QuizResult ─────────────────────────────────────────────────────────────────

class QuizResultCreate(BaseModel):
    attempt_id: UUID
    question_id: UUID
    student_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    marks_earned: float = 0.0
    ai_feedback: Optional[str] = None


class QuizResultResponse(BaseResponse):
    attempt_id: UUID
    question_id: UUID
    student_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    marks_earned: float
    ai_feedback: Optional[str] = None


# ── Submit attempt request ─────────────────────────────────────────────────────

class AnswerItem(BaseModel):
    question_id: UUID
    answer: str


class SubmitAttemptRequest(BaseModel):
    answers: list[AnswerItem]
