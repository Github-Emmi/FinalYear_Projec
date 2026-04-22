"""Assessment repositories: Quiz, Question, QuizAttempt, QuizResult."""

from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Question, Quiz, QuizAttempt, QuizResult
from app.repositories.base import BaseRepository


class QuizRepository(BaseRepository[Quiz]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Quiz, session)

    async def get_by_subject(self, subject_id: UUID) -> List[Quiz]:
        result = await self.session.execute(
            select(Quiz).where(
                Quiz.subject_id == subject_id, Quiz.is_deleted.is_(False)
            )
        )
        return list(result.scalars().all())


class QuestionRepository(BaseRepository[Question]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Question, session)

    async def get_by_quiz(self, quiz_id: UUID) -> List[Question]:
        result = await self.session.execute(
            select(Question)
            .where(Question.quiz_id == quiz_id, Question.is_deleted.is_(False))
            .order_by(Question.order)
        )
        return list(result.scalars().all())


class QuizAttemptRepository(BaseRepository[QuizAttempt]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(QuizAttempt, session)

    async def get_by_student_and_quiz(
        self, student_id: UUID, quiz_id: UUID
    ) -> List[QuizAttempt]:
        result = await self.session.execute(
            select(QuizAttempt).where(
                QuizAttempt.student_id == student_id,
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())


class QuizResultRepository(BaseRepository[QuizResult]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(QuizResult, session)

    async def get_by_attempt(self, attempt_id: UUID) -> List[QuizResult]:
        result = await self.session.execute(
            select(QuizResult).where(
                QuizResult.attempt_id == attempt_id,
                QuizResult.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())
