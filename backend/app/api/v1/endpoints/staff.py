"""Staff profile endpoints."""

from __future__ import annotations

from uuid import UUID

from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AdminOnly, AnyAuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models.staff import StaffProfile
from app.models.user import User, UserRole
from app.repositories.factory import RepositoryFactory
from app.schemas.staff import (
    StaffCreateWithUser,
    StaffProfileCreate,
    StaffProfileResponse,
    StaffProfileUpdate,
)
from app.services.staff_service import StaffService

router = APIRouter(prefix="/staff", tags=["staff"])


@router.post(
    "",
    response_model=StaffProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AdminOnly)],
)
async def create_staff(
    body: StaffCreateWithUser, db: AsyncSession = Depends(get_db)
) -> StaffProfileResponse:
    """Create a user account + staff profile in one call."""
    from app.services.user_service import UserService
    from app.schemas.user import UserCreate

    user_svc = UserService(db)
    user = await user_svc.create(
        UserCreate(
            username=body.username,
            email=body.email,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
            role=UserRole.staff,
        )
    )
    svc = StaffService(db)
    profile = await svc.create_profile(
        StaffProfileCreate(
            user_id=user.id,
            department_id=body.department_id,
            designation=body.designation,
            phone=body.phone,
        )
    )
    return StaffProfileResponse.model_validate(profile)


@router.get("", response_model=dict, dependencies=[Depends(AdminOnly)])
async def list_staff(
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
        q = (
            select(StaffProfile)
            .join(User, StaffProfile.user_id == User.id)
            .where(
                StaffProfile.is_deleted.is_(False),
                or_(
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.username.ilike(term),
                    User.email.ilike(term),
                    StaffProfile.designation.ilike(term),
                ),
            )
            .options(
                selectinload(StaffProfile.user),
                selectinload(StaffProfile.department),
            )
            .offset(effective_skip)
            .limit(effective_limit)
            .order_by(StaffProfile.created_at.desc())
        )
        result = await db.execute(q)
        profiles = list(result.scalars().all())
    else:
        repo = RepositoryFactory(db)
        profiles = await repo.staff.get_all(skip=effective_skip, limit=effective_limit)

    items = [StaffProfileResponse.model_validate(p) for p in profiles]
    return {"items": [i.model_dump() for i in items], "total": len(items), "page": max(page, 1), "size": effective_limit}


# IMPORTANT: /me MUST be registered before /{staff_id}
@router.get("/me", response_model=StaffProfileResponse)
async def get_my_staff_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StaffProfileResponse:
    svc = StaffService(db)
    profile = await svc.get_by_user_id(current_user.id)
    return StaffProfileResponse.model_validate(profile)


@router.get(
    "/{staff_id}",
    response_model=StaffProfileResponse,
    dependencies=[Depends(AnyAuthenticatedUser)],
)
async def get_staff_profile(
    staff_id: UUID, db: AsyncSession = Depends(get_db)
) -> StaffProfileResponse:
    svc = StaffService(db)
    profile = await svc.get_profile(staff_id)
    return StaffProfileResponse.model_validate(profile)


@router.patch("/{staff_id}", response_model=StaffProfileResponse, dependencies=[Depends(AdminOnly)])
async def update_staff_profile(
    staff_id: UUID,
    body: StaffProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> StaffProfileResponse:
    svc = StaffService(db)
    profile = await svc.update_profile(staff_id, body)
    return StaffProfileResponse.model_validate(profile)


@router.delete("/{staff_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_staff_profile(staff_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    svc = StaffService(db)
    await svc.delete_profile(staff_id)
