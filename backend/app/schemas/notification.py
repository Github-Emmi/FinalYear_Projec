"""Notification schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.notification import NotificationType
from app.schemas.base import BaseResponse


class NotificationCreate(BaseModel):
    recipient_id: UUID
    title: str
    message: str
    notification_type: NotificationType = NotificationType.info
    sender_id: Optional[UUID] = None


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None


class NotificationResponse(BaseResponse):
    sender_id: Optional[UUID] = None
    recipient_id: UUID
    title: str
    message: str
    notification_type: str
    is_read: bool
    read_at: Optional[datetime] = None
