"""Assignment service: CRUD, submission handling, AI feedback."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
from app.repositories.factory import RepositoryFactory
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate

_settings = get_settings()


class AssignmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._repos = RepositoryFactory(session)

    # ── Assignment CRUD ────────────────────────────────────────────────────────

    async def create(self, data: AssignmentCreate) -> Assignment:
        assignment = Assignment(**data.model_dump())
        return await self._repos.assignments.create(assignment)

    async def get(self, assignment_id: UUID) -> Assignment:
        return await self._require_assignment(assignment_id)

    async def update(self, assignment_id: UUID, data: AssignmentUpdate) -> Assignment:
        assignment = await self._require_assignment(assignment_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(assignment, field, value)
        return await self._repos.assignments.update(assignment)

    async def delete(self, assignment_id: UUID) -> None:
        await self._require_assignment(assignment_id)
        await self._repos.assignments.soft_delete(assignment_id)

    # ── Submission lifecycle ───────────────────────────────────────────────────

    async def submit(
        self,
        assignment_id: UUID,
        student_id: UUID,
        file_url: str | None = None,
    ) -> AssignmentSubmission:
        """Create or replace a submission for the given student."""
        assignment = await self._require_assignment(assignment_id)

        existing = await self._repos.submissions.get_by_assignment(assignment_id)
        prior = next((s for s in existing if s.student_id == student_id), None)
        if prior:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Submission already exists for this student",
            )

        submission = AssignmentSubmission(
            assignment_id=assignment_id,
            student_id=student_id,
            file_url=file_url,
            status=SubmissionStatus.submitted.value,
            submitted_at=datetime.utcnow(),
        )
        return await self._repos.submissions.create(submission)

    async def grade(
        self,
        submission_id: UUID,
        score: float,
        feedback: str | None = None,
    ) -> AssignmentSubmission:
        submission = await self._require_submission(submission_id)
        submission.score = score
        submission.feedback = feedback
        submission.status = SubmissionStatus.graded.value
        submission.graded_at = datetime.utcnow()
        return await self._repos.submissions.update(submission)

    async def grade_with_ai(self, submission_id: UUID) -> AssignmentSubmission:
        """Generate AI feedback for a submission using GPT-4o-mini."""
        submission = await self._require_submission(submission_id)
        assignment = await self._require_assignment(submission.assignment_id)

        if not assignment.ai_grading_enabled or not _settings.OPENAI_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI grading is not enabled for this assignment",
            )

        ai_feedback = await self._generate_ai_feedback(assignment, submission)
        submission.ai_feedback = ai_feedback
        submission.status = SubmissionStatus.graded.value
        submission.graded_at = datetime.utcnow()
        return await self._repos.submissions.update(submission)

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _generate_ai_feedback(
        self, assignment: Assignment, submission: AssignmentSubmission
    ) -> str:
        try:
            from app.services.ai_agent import ai_agent  # lazy to avoid circular import

            feedback = await ai_agent.grade_essay(
                assignment_title=assignment.title,
                assignment_description=assignment.description,
                file_url=submission.file_url,
            )
            return feedback or "AI feedback unavailable"
        except Exception:
            return "AI feedback unavailable"

    async def _require_assignment(self, assignment_id: UUID) -> Assignment:
        obj = await self._repos.assignments.get_by_id(assignment_id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found",
            )
        return obj

    async def _require_submission(
        self, submission_id: UUID
    ) -> AssignmentSubmission:
        obj = await self._repos.submissions.get_by_id(submission_id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found",
            )
        return obj
