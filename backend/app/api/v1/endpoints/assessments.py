"""Quiz / question / attempt endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticatedUser, StaffOrAdmin
from app.core.database import get_db
from app.repositories.factory import RepositoryFactory
from app.schemas.assessment import (
    AnswerItem,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    QuizAttemptResponse,
    QuizCreate,
    QuizResponse,
    QuizResultResponse,
    QuizUpdate,
    SubmitAttemptRequest,
)
from app.models.assessment import Question
from app.services.assessment_service import AssessmentService
from app.tasks.grading_tasks import grade_attempt_task

router = APIRouter(prefix="/quizzes", tags=["assessments"])


# ── Quiz CRUD ─────────────────────────────────────────────────────────────────

@router.post("", response_model=QuizResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(StaffOrAdmin)])
async def create_quiz(body: QuizCreate, db: AsyncSession = Depends(get_db)) -> QuizResponse:
    svc = AssessmentService(db)
    quiz = await svc.create_quiz(body)
    return QuizResponse.model_validate(quiz)


@router.get("/{quiz_id}", response_model=QuizResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_quiz(quiz_id: UUID, db: AsyncSession = Depends(get_db)) -> QuizResponse:
    svc = AssessmentService(db)
    quiz = await svc.get_quiz(quiz_id)
    return QuizResponse.model_validate(quiz)


@router.patch("/{quiz_id}", response_model=QuizResponse, dependencies=[Depends(StaffOrAdmin)])
async def update_quiz(quiz_id: UUID, body: QuizUpdate, db: AsyncSession = Depends(get_db)) -> QuizResponse:
    svc = AssessmentService(db)
    quiz = await svc.update_quiz(quiz_id, body)
    return QuizResponse.model_validate(quiz)


@router.delete("/{quiz_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(StaffOrAdmin)])
async def delete_quiz(quiz_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AssessmentService(db).delete_quiz(quiz_id)


# ── Quiz lifecycle ─────────────────────────────────────────────────────────────

@router.post("/{quiz_id}/publish", response_model=QuizResponse, dependencies=[Depends(StaffOrAdmin)])
async def publish_quiz(quiz_id: UUID, db: AsyncSession = Depends(get_db)) -> QuizResponse:
    svc = AssessmentService(db)
    quiz = await svc.publish_quiz(quiz_id)
    return QuizResponse.model_validate(quiz)


@router.post("/{quiz_id}/close", response_model=QuizResponse, dependencies=[Depends(StaffOrAdmin)])
async def close_quiz(quiz_id: UUID, db: AsyncSession = Depends(get_db)) -> QuizResponse:
    svc = AssessmentService(db)
    quiz = await svc.close_quiz(quiz_id)
    return QuizResponse.model_validate(quiz)


# ── Questions ──────────────────────────────────────────────────────────────────

@router.post("/{quiz_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(StaffOrAdmin)])
async def add_question(quiz_id: UUID, body: QuestionCreate, db: AsyncSession = Depends(get_db)) -> QuestionResponse:
    repo = RepositoryFactory(db)
    body_dict = body.model_dump(exclude_none=True)
    body_dict["quiz_id"] = quiz_id
    question = await repo.questions.create(Question(**body_dict))
    return QuestionResponse.model_validate(question)


@router.get("/{quiz_id}/questions", response_model=list[QuestionResponse], dependencies=[Depends(AnyAuthenticatedUser)])
async def list_questions(quiz_id: UUID, db: AsyncSession = Depends(get_db)) -> list[QuestionResponse]:
    repo = RepositoryFactory(db)
    questions = await repo.questions.get_by_quiz(quiz_id)
    return [QuestionResponse.model_validate(q) for q in questions]


@router.patch("/{quiz_id}/questions/{question_id}", response_model=QuestionResponse, dependencies=[Depends(StaffOrAdmin)])
async def update_question(quiz_id: UUID, question_id: UUID, body: QuestionUpdate, db: AsyncSession = Depends(get_db)) -> QuestionResponse:
    repo = RepositoryFactory(db)
    question = await repo.questions.get_by_id(question_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(question, field, value)
    updated = await repo.questions.update(question)
    return QuestionResponse.model_validate(updated)


# ── Attempt lifecycle ──────────────────────────────────────────────────────────

@router.post("/{quiz_id}/attempt", response_model=QuizAttemptResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AnyAuthenticatedUser)])
async def start_attempt(quiz_id: UUID, student_id: UUID, db: AsyncSession = Depends(get_db)) -> QuizAttemptResponse:
    svc = AssessmentService(db)
    attempt = await svc.start_attempt(quiz_id, student_id)
    return QuizAttemptResponse.model_validate(attempt)


@router.post("/attempts/{attempt_id}/submit", response_model=QuizAttemptResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def submit_attempt(attempt_id: UUID, body: SubmitAttemptRequest, db: AsyncSession = Depends(get_db)) -> QuizAttemptResponse:
    svc = AssessmentService(db)
    answers = [{"question_id": a.question_id, "student_answer": a.answer} for a in body.answers]
    attempt = await svc.submit_attempt(attempt_id, answers)
    # Enqueue Celery task for AI grading — best-effort (non-blocking failure)
    from fastapi import HTTPException
    try:
        grade_attempt_task.delay(str(attempt_id))
    except Exception as exc:  # broker unavailable
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Grading queue unavailable — check broker configuration: {exc}",
        )
    return QuizAttemptResponse.model_validate(attempt)


@router.get("/attempts/{attempt_id}", response_model=QuizAttemptResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_attempt(attempt_id: UUID, db: AsyncSession = Depends(get_db)) -> QuizAttemptResponse:
    repo = RepositoryFactory(db)
    attempt = await repo.quiz_attempts.get_by_id(attempt_id)
    return QuizAttemptResponse.model_validate(attempt)
