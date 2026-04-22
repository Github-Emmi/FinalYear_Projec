"""Notification model."""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class NotificationType(str, enum.Enum):
    info = "info"
    warning = "warning"
    success = "success"
    error = "error"


class Notification(BaseModel):
    __tablename__ = "notifications"

    sender_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    recipient_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(
        String(50), default=NotificationType.info.value, nullable=False
    )
    is_read = Column(Boolean, default=False, nullable=False, server_default="false")
    read_at = Column(DateTime, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    sender = relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="sent_notifications",
    )
    recipient = relationship(
        "User",
        foreign_keys=[recipient_id],
        back_populates="received_notifications",
    )
