"""Assessment models: Quiz, Question, QuizAttempt, QuizResult."""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class QuizStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    closed = "closed"
 

class QuestionType(str, enum.Enum):
    multiple_choice = "multiple_choice"
    true_false = "true_false"
    short_answer = "short_answer"


class AttemptStatus(str, enum.Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    graded = "graded"


class Quiz(BaseModel):
    __tablename__ = "quizzes"

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    staff_id = Column(
        UUID(as_uuid=True), ForeignKey("staff_profiles.id"), nullable=False
    )
    status = Column(String(50), default=QuizStatus.draft.value, nullable=False)
    time_limit_minutes = Column(Integer, nullable=True)
    max_attempts = Column(Integer, default=1, nullable=False)
    pass_score = Column(Float, default=50.0, nullable=False)
    due_date = Column(DateTime, nullable=True)
    ai_grading_enabled = Column(
        Boolean, default=False, nullable=False, server_default="false"
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    subject = relationship("Subject", back_populates="quizzes")
    staff = relationship("StaffProfile", back_populates="quizzes")
    questions = relationship(
        "Question", back_populates="quiz", cascade="all, delete-orphan"
    )
    attempts = relationship("QuizAttempt", back_populates="quiz")


class Question(BaseModel):
    __tablename__ = "questions"

    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False)
    text = Column(Text, nullable=False)
    question_type = Column(
        String(50),
        default=QuestionType.multiple_choice.value,
        nullable=False,
    )
    option_a = Column(Text, nullable=True)
    option_b = Column(Text, nullable=True)
    option_c = Column(Text, nullable=True)
    option_d = Column(Text, nullable=True)
    # "a", "b", "c", "d", "true", "false", or free-text for short_answer
    correct_answer = Column(String(50), nullable=True)
    marks = Column(Float, default=1.0, nullable=False)
    order = Column(Integer, default=0, nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────────
    quiz = relationship("Quiz", back_populates="questions")
    results = relationship("QuizResult", back_populates="question")


class QuizAttempt(BaseModel):
    __tablename__ = "quiz_attempts"

    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id"), nullable=False
    )
    status = Column(
        String(50), default=AttemptStatus.in_progress.value, nullable=False
    )
    score = Column(Float, nullable=True)
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    graded_at = Column(DateTime, nullable=True)
    ai_feedback = Column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("StudentProfile", back_populates="quiz_attempts")
    results = relationship(
        "QuizResult", back_populates="attempt", cascade="all, delete-orphan"
    )


class QuizResult(BaseModel):
    __tablename__ = "quiz_results"

    attempt_id = Column(
        UUID(as_uuid=True), ForeignKey("quiz_attempts.id"), nullable=False
    )
    question_id = Column(
        UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False
    )
    student_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    marks_earned = Column(Float, default=0.0, nullable=False)
    ai_feedback = Column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    attempt = relationship("QuizAttempt", back_populates="results")
    question = relationship("Question", back_populates="results")
