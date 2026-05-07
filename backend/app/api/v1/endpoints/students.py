"""Student profile endpoints."""

from __future__ import annotations

from uuid import UUID

from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AdminOnly, AnyAuthenticatedUser, get_current_user
from app.core.database import get_db
from app.core.security import hash_password
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.repositories.factory import RepositoryFactory
from app.schemas.student import (
    StudentCreateWithUser,
    StudentProfileCreate,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["students"])


@router.post(
    "",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AdminOnly)],
)
async def create_student(
    body: StudentCreateWithUser, db: AsyncSession = Depends(get_db)
) -> StudentProfileResponse:
    """Create a user account + student profile in one call."""
    from app.services.user_service import UserService
    from fastapi import HTTPException

    # 1. Create the user
    user_svc = UserService(db)
    from app.schemas.user import UserCreate
    user = await user_svc.create(
        UserCreate(
            username=body.username,
            email=body.email,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
            role=UserRole.student,
        )
    )
    # 2. Create the profile
    svc = StudentService(db)
    profile = await svc.create_profile(
        StudentProfileCreate(
            user_id=user.id,
            classroom_id=body.classroom_id,
            session_year_id=body.session_year_id,
            roll_number=body.roll_number,
            date_of_birth=body.date_of_birth,
            gender=body.gender,
            phone=body.phone,
            address=body.address,
        )
    )
    return StudentProfileResponse.model_validate(profile)


@router.get("", response_model=dict, dependencies=[Depends(AdminOnly)])
async def list_students(
    page: int = 1,
    size: int = 50,
    skip: int = 0,
    limit: int = 0,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_skip = skip if skip else (page - 1) * size
    effective_limit = limit if limit else size

    if search:
        term = f"%{search.strip()}%"
        # Join with User to search on names / email / username + roll_number
        q = (
            select(StudentProfile)
            .join(User, StudentProfile.user_id == User.id)
            .where(
                StudentProfile.is_deleted.is_(False),
                or_(
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.username.ilike(term),
                    User.email.ilike(term),
                    StudentProfile.roll_number.ilike(term),
                ),
            )
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.classroom),
            )
            .offset(effective_skip)
            .limit(effective_limit)
            .order_by(StudentProfile.created_at.desc())
        )
        result = await db.execute(q)
        profiles = list(result.scalars().all())
    else:
        repo = RepositoryFactory(db)
        profiles = await repo.students.get_all(skip=effective_skip, limit=effective_limit)

    items = [StudentProfileResponse.model_validate(p) for p in profiles]
    return {"items": [i.model_dump() for i in items], "total": len(items), "page": max(page, 1), "size": effective_limit}


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
