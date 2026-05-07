"""Schemas for feedback chat (threads + messages)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import BaseResponse


# ── Nested sender info ────────────────────────────────────────────────────────


class SenderInfo(BaseModel):
    id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    role: str

    model_config = {"from_attributes": True}


# ── Messages ──────────────────────────────────────────────────────────────────


class FeedbackMessageCreate(BaseModel):
    body: str


class FeedbackMessageResponse(BaseResponse):
    thread_id: UUID
    sender_id: UUID
    body: str
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_mime: Optional[str] = None
    is_admin_message: bool
    sender: Optional[SenderInfo] = None


# ── Threads ───────────────────────────────────────────────────────────────────


class FeedbackThreadCreate(BaseModel):
    subject: Optional[str] = None
    body: str  # First message body


class FeedbackThreadResponse(BaseResponse):
    sender_id: UUID
    sender_role: str
    subject: Optional[str] = None
    status: str
    unread_by_admin: int
    unread_by_sender: int
    sender: Optional[SenderInfo] = None
    last_message: Optional[FeedbackMessageResponse] = None
    message_count: int = 0


class FeedbackThreadDetail(FeedbackThreadResponse):
    messages: List[FeedbackMessageResponse] = []
