"""Student profile endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyAuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.factory import RepositoryFactory
from app.schemas.student import StudentProfileCreate, StudentProfileResponse, StudentProfileUpdate
from app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["students"])


@router.post(
    "",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AdminOnly)],
)
async def create_student_profile(
    body: StudentProfileCreate, db: AsyncSession = Depends(get_db)
) -> StudentProfileResponse:
    svc = StudentService(db)
    profile = await svc.create_profile(body)
    return StudentProfileResponse.model_validate(profile)


@router.get("", response_model=list[StudentProfileResponse], dependencies=[Depends(AdminOnly)])
async def list_students(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[StudentProfileResponse]:
    repo = RepositoryFactory(db)
    profiles = await repo.students.get_all(skip=skip, limit=limit)
    return [StudentProfileResponse.model_validate(p) for p in profiles]


# IMPORTANT: /me MUST be registered before /{student_id} to prevent "me" being parsed as UUID
@router.get("/me", response_model=StudentProfileResponse)
async def get_my_student_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentProfileResponse:
    svc = StudentService(db)
    profile = await svc.get_by_user_id(current_user.id)
    return StudentProfileResponse.model_validate(profile)


@router.get(
    "/{student_id}",
    response_model=StudentProfileResponse,
    dependencies=[Depends(AnyAuthenticatedUser)],
)
async def get_student_profile(
    student_id: UUID, db: AsyncSession = Depends(get_db)
) -> StudentProfileResponse:
    svc = StudentService(db)
    profile = await svc.get_profile(student_id)
    return StudentProfileResponse.model_validate(profile)


@router.patch("/{student_id}", response_model=StudentProfileResponse, dependencies=[Depends(AdminOnly)])
async def update_student_profile(
    student_id: UUID,
    body: StudentProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> StudentProfileResponse:
    svc = StudentService(db)
    profile = await svc.update_profile(student_id, body)
    return StudentProfileResponse.model_validate(profile)


@router.delete("/{student_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_student_profile(student_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    svc = StudentService(db)
    await svc.delete_profile(student_id)
