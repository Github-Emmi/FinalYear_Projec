"""Staff profile endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyAuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.factory import RepositoryFactory
from app.schemas.staff import StaffProfileCreate, StaffProfileResponse, StaffProfileUpdate
from app.services.staff_service import StaffService

router = APIRouter(prefix="/staff", tags=["staff"])


@router.post(
    "",
    response_model=StaffProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AdminOnly)],
)
async def create_staff_profile(
    body: StaffProfileCreate, db: AsyncSession = Depends(get_db)
) -> StaffProfileResponse:
    svc = StaffService(db)
    profile = await svc.create_profile(body)
    return StaffProfileResponse.model_validate(profile)


@router.get("", response_model=list[StaffProfileResponse], dependencies=[Depends(AdminOnly)])
async def list_staff(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[StaffProfileResponse]:
    repo = RepositoryFactory(db)
    profiles = await repo.staff.get_all(skip=skip, limit=limit)
    return [StaffProfileResponse.model_validate(p) for p in profiles]


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
