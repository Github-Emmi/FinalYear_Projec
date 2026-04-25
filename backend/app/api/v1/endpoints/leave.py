"""Leave request endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticatedUser, StaffOrAdmin
from app.core.database import get_db
from app.schemas.leave import LeaveRequestCreate, LeaveRequestResponse, LeaveRequestReview, LeaveRequestUpdate
from app.services.leave_service import LeaveService

router = APIRouter(prefix="/leave", tags=["leave"])


@router.post("", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AnyAuthenticatedUser)])
async def apply_leave(body: LeaveRequestCreate, db: AsyncSession = Depends(get_db)) -> LeaveRequestResponse:
    svc = LeaveService(db)
    leave = await svc.apply(body)
    return LeaveRequestResponse.model_validate(leave)


# IMPORTANT: /pending MUST be registered before /{leave_id}
@router.get("/pending", response_model=list[LeaveRequestResponse], dependencies=[Depends(StaffOrAdmin)])
async def get_pending_leaves(db: AsyncSession = Depends(get_db)) -> list[LeaveRequestResponse]:
    svc = LeaveService(db)
    leaves = await svc.get_pending()
    return [LeaveRequestResponse.model_validate(lv) for lv in leaves]


@router.get("/{leave_id}", response_model=LeaveRequestResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_leave(leave_id: UUID, db: AsyncSession = Depends(get_db)) -> LeaveRequestResponse:
    svc = LeaveService(db)
    leave = await svc.get(leave_id)
    return LeaveRequestResponse.model_validate(leave)


@router.patch("/{leave_id}", response_model=LeaveRequestResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def update_leave(leave_id: UUID, body: LeaveRequestUpdate, db: AsyncSession = Depends(get_db)) -> LeaveRequestResponse:
    svc = LeaveService(db)
    leave = await svc.update(leave_id, body)
    return LeaveRequestResponse.model_validate(leave)


@router.delete("/{leave_id}/cancel", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AnyAuthenticatedUser)])
async def cancel_leave(leave_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await LeaveService(db).cancel(leave_id)


@router.post("/{leave_id}/review", response_model=LeaveRequestResponse, dependencies=[Depends(StaffOrAdmin)])
async def review_leave(
    leave_id: UUID,
    body: LeaveRequestReview,
    db: AsyncSession = Depends(get_db),
) -> LeaveRequestResponse:
    svc = LeaveService(db)
    leave = await svc.review(
        leave_id,
        reviewer_id=body.reviewed_by_id,
        new_status=body.status,
        rejection_reason=body.rejection_reason,
    )
    return LeaveRequestResponse.model_validate(leave)
