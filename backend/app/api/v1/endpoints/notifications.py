"""Notification endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyAuthenticatedUser, StaffOrAdmin, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import BroadcastNotificationRequest, NotificationCreate, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(StaffOrAdmin)])
async def send_notification(body: NotificationCreate, db: AsyncSession = Depends(get_db)) -> NotificationResponse:
    svc = NotificationService(db)
    notif = await svc.send(body)
    return NotificationResponse.model_validate(notif)


@router.post("/broadcast", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(StaffOrAdmin)])
async def broadcast_notification(
    body: BroadcastNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    svc = NotificationService(db)
    await svc.send_broadcast(
        recipient_ids=body.recipient_ids,
        title=body.title,
        message=body.message,
        sender_id=current_user.id,
        notification_type=(
            body.notification_type.value
            if hasattr(body.notification_type, "value")
            else body.notification_type
        ),
    )


# IMPORTANT: /me must be registered before /{notification_id}
@router.get("/me", response_model=list[NotificationResponse])
async def get_my_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationResponse]:
    svc = NotificationService(db)
    notifs = await svc.get_unread(current_user.id)
    return [NotificationResponse.model_validate(n) for n in notifs]


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    svc = NotificationService(db)
    notif = await svc.mark_read(notification_id, current_user.id)
    return NotificationResponse.model_validate(notif)


@router.delete("/{notification_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_notification(notification_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await NotificationService(db).delete(notification_id)
