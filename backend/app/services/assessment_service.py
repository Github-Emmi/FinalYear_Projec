"""Assessment service: quiz lifecycle, MCQ auto-grading, AI short-answer grading."""

from __future__ import annotations

import json
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.assessment import (
    AttemptStatus,
    Question,
    QuestionType,
    Quiz,
    QuizAttempt,
    QuizResult,
    QuizStatus,
)
from app.repositories.factory import RepositoryFactory
from app.schemas.assessment import QuizCreate, QuizUpdate

_settings = get_settings()


class AssessmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._repos = RepositoryFactory(session)

    # ── Quiz CRUD ──────────────────────────────────────────────────────────────

    async def create_quiz(self, data: QuizCreate) -> Quiz:
        quiz = Quiz(**data.model_dump())
        return await self._repos.quizzes.create(quiz)

    async def get_quiz(self, quiz_id: UUID) -> Quiz:
        return await self._require_quiz(quiz_id)

    async def update_quiz(self, quiz_id: UUID, data: QuizUpdate) -> Quiz:
        quiz = await self._require_quiz(quiz_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(quiz, field, value)
        return await self._repos.quizzes.update(quiz)

    async def publish_quiz(self, quiz_id: UUID) -> Quiz:
        quiz = await self._require_quiz(quiz_id)
        quiz.status = QuizStatus.published.value
        return await self._repos.quizzes.update(quiz)

    async def close_quiz(self, quiz_id: UUID) -> Quiz:
        quiz = await self._require_quiz(quiz_id)
        quiz.status = QuizStatus.closed.value
        return await self._repos.quizzes.update(quiz)

    async def delete_quiz(self, quiz_id: UUID) -> None:
        await self._require_quiz(quiz_id)
        await self._repos.quizzes.soft_delete(quiz_id)

    # ── Attempt lifecycle ─────────────────────────────────────────────────────

    async def start_attempt(self, quiz_id: UUID, student_id: UUID) -> QuizAttempt:
        quiz = await self._require_quiz(quiz_id)

        if quiz.status != QuizStatus.published.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz is not open for attempts",
            )

        existing = await self._repos.quiz_attempts.get_by_student_and_quiz(
            student_id, quiz_id
        )
        completed = [
            a for a in existing if a.status != AttemptStatus.in_progress.value
        ]
        if len(completed) >= quiz.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum number of attempts reached",
            )

        attempt = QuizAttempt(
            quiz_id=quiz_id,
            student_id=student_id,
            status=AttemptStatus.in_progress.value,
            started_at=datetime.utcnow(),
        )
        return await self._repos.quiz_attempts.create(attempt)

    async def submit_attempt(
        self, attempt_id: UUID, answers: List[dict]
    ) -> QuizAttempt:
        """Grade all answers and finalise the attempt.

        *answers* is a list of ``{"question_id": str|UUID, "student_answer": str}``.
        MCQ/True-False are auto-graded; short-answer uses GPT-4o-mini when enabled.
        """
        attempt = await self._require_attempt(attempt_id)

        if attempt.status != AttemptStatus.in_progress.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attempt is already submitted or graded",
            )

        questions = await self._repos.questions.get_by_quiz(attempt.quiz_id)
        q_map = {q.id: q for q in questions}
        total_marks = sum(q.marks for q in questions) or 1.0  # guard div-by-zero

        earned_marks = 0.0
        for ans in answers:
            q_id = (
                UUID(ans["question_id"])
                if isinstance(ans["question_id"], str)
                else ans["question_id"]
            )
            question = q_map.get(q_id)
            if question is None:
                continue

            student_answer = ans.get("student_answer", "")
            is_correct, marks_earned, ai_feedback = await self._grade_answer(
                question, student_answer, attempt.quiz_id
            )
            earned_marks += marks_earned

            result = QuizResult(
                attempt_id=attempt_id,
                question_id=q_id,
                student_answer=student_answer,
                is_correct=is_correct,
                marks_earned=marks_earned,
                ai_feedback=ai_feedback,
            )
            await self._repos.quiz_results.create(result)

        score = round(earned_marks / total_marks * 100, 2)
        attempt.score = score
        attempt.submitted_at = datetime.utcnow()
        attempt.status = AttemptStatus.submitted.value

        # If all answers were auto/AI-graded, mark as graded immediately
        quiz = await self._repos.quizzes.get_by_id(attempt.quiz_id)
        if quiz and quiz.ai_grading_enabled:
            attempt.status = AttemptStatus.graded.value
            attempt.graded_at = datetime.utcnow()

        return await self._repos.quiz_attempts.update(attempt)

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _grade_answer(
        self, question: Question, student_answer: str, quiz_id: UUID
    ) -> tuple[bool, float, str | None]:
        q_type = question.question_type

        if q_type in (
            QuestionType.multiple_choice.value,
            QuestionType.true_false.value,
        ):
            correct = (
                student_answer.strip().lower()
                == (question.correct_answer or "").strip().lower()
            )
            return correct, question.marks if correct else 0.0, None

        if q_type == QuestionType.short_answer.value:
            quiz = await self._repos.quizzes.get_by_id(quiz_id)
            if quiz and quiz.ai_grading_enabled and _settings.OPENAI_API_KEY:
                return await self._ai_grade(question, student_answer)
            # No AI — return 0, awaiting manual grading
            return False, 0.0, None

        return False, 0.0, None

    async def _ai_grade(
        self, question: Question, student_answer: str
    ) -> tuple[bool, float, str]:
        """Grade a short-answer question with GPT-4o-mini.

        Falls back to (False, 0.0, "AI grading unavailable") on any error.
        """
        try:
            from openai import AsyncOpenAI  # lazy import

            client = AsyncOpenAI(api_key=_settings.OPENAI_API_KEY)
            prompt = (
                "You are grading a student's short-answer response.\n\n"
                f"Question: {question.text}\n"
                f"Expected answer: {question.correct_answer}\n"
                f"Student's answer: {student_answer}\n\n"
                "Respond with valid JSON only (no markdown):\n"
                '{"is_correct": true|false, '
                f'"marks_earned": <number 0 to {question.marks}>, '
                '"feedback": "<one sentence>"}'
            )
            response = await client.chat.completions.create(
                model=_settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150,
            )
            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)
            return (
                bool(data["is_correct"]),
                float(data["marks_earned"]),
                str(data["feedback"]),
            )
        except Exception:
            return False, 0.0, "AI grading unavailable"

    async def _require_quiz(self, quiz_id: UUID) -> Quiz:
        quiz = await self._repos.quizzes.get_by_id(quiz_id)
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found",
            )
        return quiz

    async def _require_attempt(self, attempt_id: UUID) -> QuizAttempt:
        attempt = await self._repos.quiz_attempts.get_by_id(attempt_id)
        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz attempt not found",
            )
        return attempt
