"""User model — authentication identity for all roles."""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"
    student = "student"


class User(BaseModel):
    __tablename__ = "users"

    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.student.value)
    is_active = Column(Boolean, default=True, nullable=False, server_default="true")
    last_login = Column(DateTime, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    student_profile = relationship(
        "StudentProfile", back_populates="user", uselist=False
    )
    staff_profile = relationship(
        "StaffProfile", back_populates="user", uselist=False
    )
    leave_requests = relationship("LeaveRequest", back_populates="user")
    sent_notifications = relationship(
        "Notification",
        foreign_keys="Notification.sender_id",
        back_populates="sender",
    )
    received_notifications = relationship(
        "Notification",
        foreign_keys="Notification.recipient_id",
        back_populates="recipient",
    )
    audit_logs = relationship("AuditLog", back_populates="user")
