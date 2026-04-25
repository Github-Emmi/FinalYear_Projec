"""Celery tasks for AI grading of assignments and quiz attempts."""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.database import async_session_maker
from app.services.assignment_service import AssignmentService
from app.services.assessment_service import AssessmentService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.grading_tasks.grade_submission_task")
def grade_submission_task(submission_id: str) -> None:
    """Grade an assignment submission with AI."""

    async def _grade() -> None:
        async with async_session_maker() as session:
            await AssignmentService(session).grade_with_ai(UUID(submission_id))

    asyncio.run(_grade())


@celery_app.task(name="app.tasks.grading_tasks.grade_attempt_task")
def grade_attempt_task(attempt_id: str) -> None:
    """Grade a quiz attempt with AI."""

    async def _grade() -> None:
        async with async_session_maker() as session:
            await AssessmentService(session).grade_attempt_with_ai(UUID(attempt_id))

    asyncio.run(_grade())
