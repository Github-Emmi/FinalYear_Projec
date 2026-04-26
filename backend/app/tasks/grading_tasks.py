"""Celery tasks for AI grading of assignments and quiz attempts."""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings  # called inside tasks to avoid import-time stale settings
from app.services.assignment_service import AssignmentService
from app.services.assessment_service import AssessmentService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.grading_tasks.grade_submission_task")
def grade_submission_task(submission_id: str) -> None:
    """Grade an assignment submission with AI."""

    async def _grade() -> None:
        # Create a fresh engine per task — the module-level engine's asyncpg pool
        # is bound to the parent process event loop and cannot be used after fork.
        settings = get_settings()
        engine = create_async_engine(
            settings.async_database_url,
            echo=False,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
        )
        try:
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as session:
                await AssignmentService(session).grade_with_ai(UUID(submission_id))
        finally:
            await engine.dispose()

    asyncio.run(_grade())


@celery_app.task(name="app.tasks.grading_tasks.grade_attempt_task")
def grade_attempt_task(attempt_id: str) -> None:
    """Grade a quiz attempt with AI."""

    async def _grade() -> None:
        settings = get_settings()
        engine = create_async_engine(
            settings.async_database_url,
            echo=False,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
        )
        try:
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as session:
                await AssessmentService(session).grade_attempt_with_ai(UUID(attempt_id))
        finally:
            await engine.dispose()

    asyncio.run(_grade())
