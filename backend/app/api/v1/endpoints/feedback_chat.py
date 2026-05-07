"""Feedback chat endpoints.

Routes
------
GET    /feedback/threads                  – list threads (admin: all, user: own)
POST   /feedback/threads                  – open a new thread (student / staff)
GET    /feedback/threads/{thread_id}      – thread detail with messages
POST   /feedback/threads/{thread_id}/messages  – send a message in a thread
PATCH  /feedback/threads/{thread_id}/resolve   – mark thread resolved (admin)
POST   /feedback/upload                   – upload a file attachment (returns URL)
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AdminOnly, AnyAuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models.feedback_chat import FeedbackMessage, FeedbackThread
from app.models.notification import NotificationType
from app.models.user import User
from app.schemas.feedback_chat import (
    FeedbackMessageCreate,
    FeedbackMessageResponse,
    FeedbackThreadCreate,
    FeedbackThreadDetail,
    FeedbackThreadResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback-chat"])

# ── Media upload directory ────────────────────────────────────────────────────
MEDIA_DIR = Path(__file__).resolve().parents[5] / "media" / "feedback"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME_PREFIXES = ("image/", "application/pdf", "text/", "application/msword",
                         "application/vnd.", "audio/", "video/")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ── Helpers ───────────────────────────────────────────────────────────────────


def _thread_to_response(t: FeedbackThread, last_msg: Optional[FeedbackMessage] = None) -> FeedbackThreadResponse:
    msgs = t.messages if hasattr(t, "messages") and t.messages is not None else []
    resp = FeedbackThreadResponse(
        id=t.id,
        created_at=t.created_at,
        updated_at=t.updated_at,
        sender_id=t.sender_id,
        sender_role=t.sender_role,
        subject=t.subject,
        status=t.status,
        unread_by_admin=t.unread_by_admin,
        unread_by_sender=t.unread_by_sender,
        message_count=len(msgs),
    )
    if t.sender:
        from app.schemas.feedback_chat import SenderInfo
        resp.sender = SenderInfo(
            id=t.sender.id,
            first_name=t.sender.first_name,
            last_name=t.sender.last_name,
            email=t.sender.email,
            role=t.sender.role,
        )
    if last_msg:
        resp.last_message = _msg_to_response(last_msg)
    elif msgs:
        resp.last_message = _msg_to_response(msgs[-1])
    return resp


def _msg_to_response(m: FeedbackMessage) -> FeedbackMessageResponse:
    r = FeedbackMessageResponse(
        id=m.id,
        created_at=m.created_at,
        updated_at=m.updated_at,
        thread_id=m.thread_id,
        sender_id=m.sender_id,
        body=m.body,
        file_url=m.file_url,
        file_name=m.file_name,
        file_mime=m.file_mime,
        is_admin_message=m.is_admin_message,
    )
    if m.sender:
        from app.schemas.feedback_chat import SenderInfo
        r.sender = SenderInfo(
            id=m.sender.id,
            first_name=m.sender.first_name,
            last_name=m.sender.last_name,
            email=m.sender.email,
            role=m.sender.role,
        )
    return r


async def _push_ws_and_notify(
    db: AsyncSession,
    recipient_id: str,
    title: str,
    message: str,
    thread_id: str,
    current_user_id: str,
) -> None:
    """Persist notification + fire WebSocket push."""
    try:
        from app.models.notification import Notification
        from app.websockets.manager import manager
        import asyncio

        notif = Notification(
            sender_id=uuid.UUID(current_user_id),
            recipient_id=uuid.UUID(recipient_id),
            title=title,
            message=message,
            notification_type=NotificationType.info.value,
            is_read=False,
        )
        db.add(notif)
        await db.commit()

        asyncio.create_task(
            manager.send_to_user(
                recipient_id,
                {
                    "type": "feedback:new_message",
                    "title": title,
                    "message": message,
                    "thread_id": thread_id,
                },
            )
        )
    except Exception as exc:
        logger.warning("WS/notify push failed: %s", exc)


# ── List threads ──────────────────────────────────────────────────────────────


@router.get("/threads", response_model=dict)
async def list_threads(
    role_filter: Optional[str] = Query(None, description="Filter by sender_role: student | staff"),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Admins see all threads; students/staff see only their own."""
    q = (
        select(FeedbackThread)
        .options(
            selectinload(FeedbackThread.sender),
            selectinload(FeedbackThread.messages).selectinload(FeedbackMessage.sender),
        )
        .order_by(desc(FeedbackThread.updated_at))
    )

    if current_user.role == "admin":
        if role_filter:
            q = q.where(FeedbackThread.sender_role == role_filter)
        if status_filter:
            q = q.where(FeedbackThread.status == status_filter)
    else:
        # Non-admin users only see their own threads
        q = q.where(FeedbackThread.sender_id == current_user.id)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    q = q.offset((page - 1) * size).limit(size)
    threads = (await db.execute(q)).scalars().all()

    return {
        "items": [_thread_to_response(t) for t in threads],
        "total": total,
        "page": page,
        "size": size,
    }


# ── Create thread ─────────────────────────────────────────────────────────────


@router.post("/threads", response_model=FeedbackThreadDetail, status_code=status.HTTP_201_CREATED)
async def create_thread(
    body: FeedbackThreadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AnyAuthenticatedUser),
) -> FeedbackThreadDetail:
    """Open a new feedback thread (student or staff only)."""
    if current_user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins reply to existing threads; they cannot open new ones.",
        )

    thread = FeedbackThread(
        sender_id=current_user.id,
        sender_role=current_user.role,
        subject=body.subject,
        status="open",
        unread_by_admin=1,
        unread_by_sender=0,
    )
    db.add(thread)
    await db.flush()

    msg = FeedbackMessage(
        thread_id=thread.id,
        sender_id=current_user.id,
        body=body.body,
        is_admin_message=False,
    )
    db.add(msg)
    await db.commit()

    # Re-fetch with relationships
    result = await db.execute(
        select(FeedbackThread)
        .options(
            selectinload(FeedbackThread.sender),
            selectinload(FeedbackThread.messages).selectinload(FeedbackMessage.sender),
        )
        .where(FeedbackThread.id == thread.id)
    )
    thread = result.scalar_one()

    # Notify all admins via WS
    try:
        from app.websockets.manager import manager
        from app.models.user import UserRole
        import asyncio

        admin_rows = (
            await db.execute(
                select(User).where(User.role == UserRole.admin.value, User.is_active.is_(True))
            )
        ).scalars().all()

        sender_name = (
            f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
            or current_user.email
        )
        for admin in admin_rows:
            await _push_ws_and_notify(
                db,
                str(admin.id),
                f"New feedback from {sender_name}",
                body.subject or body.body[:60],
                str(thread.id),
                str(current_user.id),
            )
    except Exception as exc:
        logger.warning("Admin notify failed: %s", exc)

    detail = FeedbackThreadDetail(
        id=thread.id,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        sender_id=thread.sender_id,
        sender_role=thread.sender_role,
        subject=thread.subject,
        status=thread.status,
        unread_by_admin=thread.unread_by_admin,
        unread_by_sender=thread.unread_by_sender,
        message_count=len(thread.messages),
        messages=[_msg_to_response(m) for m in thread.messages],
    )
    if thread.sender:
        from app.schemas.feedback_chat import SenderInfo
        detail.sender = SenderInfo(
            id=thread.sender.id,
            first_name=thread.sender.first_name,
            last_name=thread.sender.last_name,
            email=thread.sender.email,
            role=thread.sender.role,
        )
    return detail


# ── Thread detail ─────────────────────────────────────────────────────────────


@router.get("/threads/{thread_id}", response_model=FeedbackThreadDetail)
async def get_thread(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackThreadDetail:
    result = await db.execute(
        select(FeedbackThread)
        .options(
            selectinload(FeedbackThread.sender),
            selectinload(FeedbackThread.messages).selectinload(FeedbackMessage.sender),
        )
        .where(FeedbackThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Access control: non-admins may only read their own thread
    if current_user.role != "admin" and str(thread.sender_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorised")

    # Mark read
    if current_user.role == "admin" and thread.unread_by_admin > 0:
        thread.unread_by_admin = 0
        await db.commit()
    elif current_user.role != "admin" and thread.unread_by_sender > 0:
        thread.unread_by_sender = 0
        await db.commit()

    detail = FeedbackThreadDetail(
        id=thread.id,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        sender_id=thread.sender_id,
        sender_role=thread.sender_role,
        subject=thread.subject,
        status=thread.status,
        unread_by_admin=thread.unread_by_admin,
        unread_by_sender=thread.unread_by_sender,
        message_count=len(thread.messages),
        messages=[_msg_to_response(m) for m in thread.messages],
    )
    if thread.sender:
        from app.schemas.feedback_chat import SenderInfo
        detail.sender = SenderInfo(
            id=thread.sender.id,
            first_name=thread.sender.first_name,
            last_name=thread.sender.last_name,
            email=thread.sender.email,
            role=thread.sender.role,
        )
    return detail


# ── Send message ──────────────────────────────────────────────────────────────


@router.post("/threads/{thread_id}/messages", response_model=FeedbackMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    thread_id: uuid.UUID,
    body: FeedbackMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackMessageResponse:
    result = await db.execute(
        select(FeedbackThread)
        .options(selectinload(FeedbackThread.sender))
        .where(FeedbackThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    is_admin = current_user.role == "admin"

    # Access check
    if not is_admin and str(thread.sender_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorised")

    if thread.status == "resolved" and not is_admin:
        raise HTTPException(status_code=400, detail="Thread is resolved")

    msg = FeedbackMessage(
        thread_id=thread.id,
        sender_id=current_user.id,
        body=body.body,
        is_admin_message=is_admin,
    )
    db.add(msg)

    # Update thread unread counters + updated_at
    if is_admin:
        thread.unread_by_sender = (thread.unread_by_sender or 0) + 1
    else:
        thread.unread_by_admin = (thread.unread_by_admin or 0) + 1

    await db.commit()

    # Re-fetch message with sender relationship
    re = await db.execute(
        select(FeedbackMessage)
        .options(selectinload(FeedbackMessage.sender))
        .where(FeedbackMessage.id == msg.id)
    )
    msg = re.scalar_one()

    # WS push to the other party
    sender_name = (
        f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
        or current_user.email
    )
    if is_admin:
        # Notify the original sender (student/staff)
        await _push_ws_and_notify(
            db,
            str(thread.sender_id),
            "Admin replied to your feedback",
            body.body[:80],
            str(thread.id),
            str(current_user.id),
        )
    else:
        # Notify all admins
        from app.models.user import UserRole
        admin_rows = (
            await db.execute(
                select(User).where(User.role == UserRole.admin.value, User.is_active.is_(True))
            )
        ).scalars().all()
        for admin in admin_rows:
            await _push_ws_and_notify(
                db,
                str(admin.id),
                f"New message from {sender_name}",
                body.body[:80],
                str(thread.id),
                str(current_user.id),
            )

    return _msg_to_response(msg)


# ── Resolve thread ────────────────────────────────────────────────────────────


@router.patch("/threads/{thread_id}/resolve", response_model=FeedbackThreadResponse, dependencies=[Depends(AdminOnly)])
async def resolve_thread(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FeedbackThreadResponse:
    result = await db.execute(
        select(FeedbackThread)
        .options(
            selectinload(FeedbackThread.sender),
            selectinload(FeedbackThread.messages),
        )
        .where(FeedbackThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.status = "resolved"
    await db.commit()
    return _thread_to_response(thread)


# ── File upload ───────────────────────────────────────────────────────────────


@router.post("/upload", response_model=dict)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload a file attachment and return its public URL."""
    if not file.content_type or not any(file.content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file.content_type}' is not allowed.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds maximum size of 10 MB.",
        )

    ext = Path(file.filename or "file").suffix
    safe_name = f"{uuid.uuid4()}{ext}"
    dest = MEDIA_DIR / safe_name
    dest.write_bytes(contents)

    return {
        "file_url": f"/media/feedback/{safe_name}",
        "file_name": file.filename,
        "file_mime": file.content_type,
    }
