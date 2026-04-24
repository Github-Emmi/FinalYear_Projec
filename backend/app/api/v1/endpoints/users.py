"""User management endpoints (admin-gated writes)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import PasswordChangeRequest
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AdminOnly)],
)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    svc = UserService(db)
    user = await svc.create(body)
    return UserResponse.model_validate(user)


@router.get("", response_model=list[UserResponse], dependencies=[Depends(AdminOnly)])
async def list_users(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[UserResponse]:
    svc = UserService(db)
    users = await svc.get_all(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(AdminOnly)])
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)) -> UserResponse:
    svc = UserService(db)
    user = await svc.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(AdminOnly)])
async def update_user(
    user_id: UUID, body: UserUpdate, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    svc = UserService(db)
    user = await svc.update(user_id, body)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    svc = UserService(db)
    await svc.soft_delete(user_id)


@router.post("/{user_id}/change-password", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    user_id: UUID,
    body: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Admin may change any user's password; authenticated users may change their own."""
    if current_user.role != "admin" and str(current_user.id) != str(user_id): #type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    svc = UserService(db)
    await svc.change_password(user_id, body)


@router.patch("/{user_id}/activate", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def set_user_active(
    user_id: UUID, active: bool, db: AsyncSession = Depends(get_db)
) -> None:
    svc = UserService(db)
    await svc.set_active(user_id, active=active)
