"""Feedback-chat models: FeedbackThread (conversation) + FeedbackMessage (message)."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class FeedbackThread(BaseModel):
    """A conversation thread between a user (student or staff) and the admin."""

    __tablename__ = "feedback_threads"

    # The user who initiated the thread
    sender_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    # "student" | "staff"
    sender_role = Column(String(20), nullable=False)
    # Optional subject / title for the thread
    subject = Column(String(255), nullable=True)
    # "open" | "resolved"
    status = Column(String(20), default="open", nullable=False)
    # Unread counters
    unread_by_admin = Column(Integer, default=0, nullable=False, server_default="0")
    unread_by_sender = Column(Integer, default=0, nullable=False, server_default="0")

    # ── Relationships ──────────────────────────────────────────────────────────
    sender = relationship("User", foreign_keys=[sender_id])
    messages = relationship(
        "FeedbackMessage",
        back_populates="thread",
        order_by="FeedbackMessage.created_at",
        cascade="all, delete-orphan",
    )


class FeedbackMessage(BaseModel):
    """A single message within a FeedbackThread."""

    __tablename__ = "feedback_messages"

    thread_id = Column(
        Uuid, ForeignKey("feedback_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    # File attachment (optional)
    file_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_mime = Column(String(100), nullable=True)
    # True when the message was sent by admin (i.e. it's an admin reply)
    is_admin_message = Column(Boolean, default=False, nullable=False, server_default="false")

    # ── Relationships ──────────────────────────────────────────────────────────
    thread = relationship("FeedbackThread", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
