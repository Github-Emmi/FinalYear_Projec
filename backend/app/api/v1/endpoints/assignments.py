"""Assignment and submission endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticatedUser, StaffOrAdmin
from app.core.database import get_db
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
    SubmissionCreate,
    SubmissionResponse,
    SubmissionUpdate,
)
from app.services.assignment_service import AssignmentService
from app.tasks.grading_tasks import grade_submission_task

router = APIRouter(prefix="/assignments", tags=["assignments"])


# ── Assignment CRUD ────────────────────────────────────────────────────────────

@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(StaffOrAdmin)])
async def create_assignment(body: AssignmentCreate, db: AsyncSession = Depends(get_db)) -> AssignmentResponse:
    svc = AssignmentService(db)
    assignment = await svc.create(body)
    return AssignmentResponse.model_validate(assignment)


@router.get("/{assignment_id}", response_model=AssignmentResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_assignment(assignment_id: UUID, db: AsyncSession = Depends(get_db)) -> AssignmentResponse:
    svc = AssignmentService(db)
    assignment = await svc.get(assignment_id)
    return AssignmentResponse.model_validate(assignment)


@router.patch("/{assignment_id}", response_model=AssignmentResponse, dependencies=[Depends(StaffOrAdmin)])
async def update_assignment(assignment_id: UUID, body: AssignmentUpdate, db: AsyncSession = Depends(get_db)) -> AssignmentResponse:
    svc = AssignmentService(db)
    assignment = await svc.update(assignment_id, body)
    return AssignmentResponse.model_validate(assignment)


@router.delete("/{assignment_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(StaffOrAdmin)])
async def delete_assignment(assignment_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AssignmentService(db).delete(assignment_id)


# ── Submission ─────────────────────────────────────────────────────────────────

@router.post("/{assignment_id}/submit", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AnyAuthenticatedUser)])
async def submit_assignment(
    assignment_id: UUID,
    student_id: UUID,
    file_url: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    svc = AssignmentService(db)
    submission = await svc.submit(assignment_id, student_id, file_url)
    return SubmissionResponse.model_validate(submission)


@router.post("/submissions/{submission_id}/grade", response_model=SubmissionResponse, dependencies=[Depends(StaffOrAdmin)])
async def grade_submission(
    submission_id: UUID,
    score: float,
    feedback: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    svc = AssignmentService(db)
    submission = await svc.grade(submission_id, score, feedback)
    return SubmissionResponse.model_validate(submission)


@router.post("/submissions/{submission_id}/grade-ai", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(StaffOrAdmin)])
async def grade_submission_with_ai(submission_id: UUID, db: AsyncSession = Depends(get_db)):
    """Enqueue AI grading for a submission. Returns 202 Accepted immediately."""
    from fastapi import HTTPException
    try:
        grade_submission_task.delay(str(submission_id))
    except Exception as exc:  # broker unavailable (e.g. Redis not reachable)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Grading queue unavailable — check broker configuration: {exc}",
        )
    return {"detail": "Grading task enqueued", "submission_id": str(submission_id)}
