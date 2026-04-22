"""Leave request service: apply, review, list."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leave import LeaveRequest, LeaveStatus
from app.repositories.factory import RepositoryFactory
from app.schemas.leave import LeaveRequestCreate, LeaveRequestUpdate


class LeaveService:
    def __init__(self, session: AsyncSession) -> None:
        self._repos = RepositoryFactory(session)

    async def apply(self, data: LeaveRequestCreate) -> LeaveRequest:
        """Submit a new leave request."""
        leave = LeaveRequest(
            user_id=data.user_id,
            leave_type=data.leave_type.value if hasattr(data.leave_type, "value") else data.leave_type,
            status=LeaveStatus.pending.value,
            start_date=data.start_date,
            end_date=data.end_date,
            reason=data.reason,
        )
        return await self._repos.leaves.create(leave)

    async def get(self, leave_id: UUID) -> LeaveRequest:
        return await self._require_leave(leave_id)

    async def update(self, leave_id: UUID, data: LeaveRequestUpdate) -> LeaveRequest:
        leave = await self._require_leave(leave_id)
        if leave.status != LeaveStatus.pending.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending leave requests can be edited",
            )
        for field, value in data.model_dump(exclude_unset=True).items():
            if hasattr(value, "value"):
                value = value.value
            setattr(leave, field, value)
        return await self._repos.leaves.update(leave)

    async def review(
        self,
        leave_id: UUID,
        reviewer_id: UUID,
        new_status: LeaveStatus,
        rejection_reason: str | None = None,
    ) -> LeaveRequest:
        """Approve or reject a leave request (staff/admin action)."""
        leave = await self._require_leave(leave_id)

        if leave.status != LeaveStatus.pending.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leave request is no longer pending",
            )

        if new_status == LeaveStatus.rejected and not rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="rejection_reason is required when rejecting a request",
            )

        leave.status = new_status.value
        leave.reviewed_by_id = reviewer_id
        leave.reviewed_at = datetime.utcnow()
        leave.rejection_reason = rejection_reason
        return await self._repos.leaves.update(leave)

    async def get_pending(self) -> list[LeaveRequest]:
        return await self._repos.leaves.get_pending()

    async def get_for_user(self, user_id: UUID) -> list[LeaveRequest]:
        return await self._repos.leaves.get_by_user(user_id)

    async def cancel(self, leave_id: UUID) -> None:
        leave = await self._require_leave(leave_id)
        if leave.status != LeaveStatus.pending.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending leave requests can be cancelled",
            )
        await self._repos.leaves.soft_delete(leave_id)

    async def _require_leave(self, leave_id: UUID) -> LeaveRequest:
        leave = await self._repos.leaves.get_by_id(leave_id)
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found",
            )
        return leave
