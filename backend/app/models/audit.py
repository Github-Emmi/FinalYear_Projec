"""AuditLog model — immutable record of state-changing actions."""

from __future__ import annotations

import enum

from sqlalchemy import Column, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AuditAction(str, enum.Enum):
    create = "create"
    update = "update"
    delete = "delete"
    login = "login"
    logout = "logout"
    view = "view"


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user = relationship("User", back_populates="audit_logs")
