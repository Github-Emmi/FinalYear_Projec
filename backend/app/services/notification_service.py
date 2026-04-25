"""Notification service: send, mark-read, list unread."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.repositories.factory import RepositoryFactory
from app.schemas.notification import NotificationCreate


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._repos = RepositoryFactory(session)

    async def send(self, data: NotificationCreate) -> Notification:
        notification = Notification(
            sender_id=data.sender_id,
            recipient_id=data.recipient_id,
            title=data.title,
            message=data.message,
            notification_type=(
                data.notification_type.value
                if hasattr(data.notification_type, "value")
                else data.notification_type
            ),
            is_read=False,
        )
        notif = await self._repos.notifications.create(notification)
        # Fire-and-forget WebSocket push
        try:
            from app.websockets.manager import manager
            import asyncio
            asyncio.create_task(manager.send_to_user(
                str(notif.recipient_id),
                {"type": "notification", "title": notif.title, "message": notif.message}
            ))
        except Exception:
            pass
        return notif

    async def send_broadcast(
        self,
        recipient_ids: list[UUID],
        title: str,
        message: str,
        sender_id: UUID | None = None,
        notification_type: str = NotificationType.info.value,
    ) -> list[Notification]:
        """Send the same notification to multiple recipients."""
        created = []
        from app.websockets.manager import manager
        import asyncio
        for rid in recipient_ids:
            n = Notification(
                sender_id=sender_id,
                recipient_id=rid,
                title=title,
                message=message,
                notification_type=notification_type,
                is_read=False,
            )
            notif = await self._repos.notifications.create(n)
            try:
                asyncio.create_task(manager.send_to_user(
                    str(notif.recipient_id),
                    {"type": "notification", "title": notif.title, "message": notif.message}
                ))
            except Exception:
                pass
            created.append(notif)
        return created

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        n = await self._repos.notifications.get_by_id(notification_id)
        if not n:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        if n.recipient_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot mark another user's notification as read",
            )
        n.is_read = True
        n.read_at = datetime.utcnow()
        return await self._repos.notifications.update(n)

    async def get_unread(self, user_id: UUID) -> list[Notification]:
        return await self._repos.notifications.get_unread_for_user(user_id)

    async def delete(self, notification_id: UUID) -> None:
        n = await self._repos.notifications.get_by_id(notification_id)
        if not n:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        await self._repos.notifications.soft_delete(notification_id)
