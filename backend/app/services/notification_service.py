"""
Notification Service - Manages notification creation, delivery, and tracking.

Provides methods for:
- Sending real-time and queued notifications
- Managing notification read status
- Bulk notifications for broadcasts
- Scheduled notification delivery
- Audit trail of all notifications
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    NotificationStudent,
    NotificationStaff,
    User,
    Notification,
)
from app.schemas import NotificationResponse
from app.utils.exceptions import NotFoundError, ValidationError
from app.services.base_service import BaseService
from app.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)

# Notification Type Constants
VALID_NOTIFICATION_TYPES = {"INFO", "WARNING", "ALERT"}
NOTIFICATION_RETENTION_DAYS = 90


class NotificationService(BaseService[Notification]):
    """
    Service for managing user notifications and real-time alerts.

    Handles notification creation, delivery (real-time and queued), read status
    management, bulk broadcasts, and scheduled delivery with WebSocket integration
    for real-time push capabilities.
    """

    def __init__(self, session: AsyncSession, repos: RepositoryFactory):
        """Initialize NotificationService with database session and repositories."""
        super().__init__(Notification, session, repos)
        self.logger = logger

    async def send_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str,
        data: Optional[dict] = None,
    ) -> dict:
        """
        Send notification to a single user.

        Args:
            user_id: UUID of recipient user
            title: Notification title
            message: Notification message body
            notification_type: Type of notification ("INFO", "WARNING", "ALERT")
            data: Optional JSON data payload

        Returns:
            {notification_id, created_at, delivered_via}

        Raises:
            NotFoundError: If user not found
            ValidationError: If invalid notification type or data
        """
        try:
            # Validate notification type
            if notification_type not in VALID_NOTIFICATION_TYPES:
                raise ValidationError(
                    f"Invalid notification type: {notification_type}. Must be one of {VALID_NOTIFICATION_TYPES}"
                )

            # Validate user exists
            user = await self.repos.user.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")

            # Validate title and message
            if not title or len(title.strip()) == 0:
                raise ValidationError("Notification title cannot be empty")
            if len(title) > 255:
                raise ValidationError("Notification title must be <= 255 characters")

            if not message or len(message.strip()) == 0:
                raise ValidationError("Notification message cannot be empty")
            if len(message) > 2000:
                raise ValidationError("Notification message must be <= 2000 characters")

            # Serialize data
            data_json = json.dumps(data) if data else None

            # Create notification
            async with self.transaction():
                notification = await self.repos.notification.create(
                    {
                        "user_id": user_id,
                        "title": title,
                        "message": message,
                        "type": notification_type,
                        "data": data_json,
                        "created_at": datetime.now(),
                        "is_read": False,
                    }
                )

                # Attempt real-time delivery via WebSocket if available
                delivered_via = "stored"
                try:
                    # Check if WebSocketManager is available and user is connected
                    # This is a placeholder - actual implementation depends on your WebSocket setup
                    websocket_manager = getattr(self, "websocket_manager", None)
                    if websocket_manager and await websocket_manager.is_connected(user_id):
                        await websocket_manager.send_personal(
                            user_id,
                            {
                                "type": "notification",
                                "notification_id": str(notification.id),
                                "title": title,
                                "message": message,
                                "notification_type": notification_type,
                            },
                        )
                        delivered_via = "real-time"
                except Exception as ws_error:
                    self.logger.warning(
                        f"WebSocket delivery failed for {user_id}: {str(ws_error)}"
                    )
                    delivered_via = "stored"

                # Log audit trail
                self.log_action(
                    action="SEND_NOTIFICATION",
                    entity_type="Notification",
                    entity_id=str(notification.id),
                    user_id=str(user_id),
                    changes={
                        "title": title,
                        "type": notification_type,
                        "delivered_via": delivered_via,
                    },
                )

            return self.success_response(
                data={
                    "notification_id": str(notification.id),
                    "created_at": notification.created_at.isoformat(),
                    "delivered_via": delivered_via,
                    "notification_type": notification_type,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error sending notification: {str(e)}")
            raise ValidationError(f"Failed to send notification: {str(e)}")

    async def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """
        Fetch paginated notifications for a user.

        Args:
            user_id: UUID of user
            unread_only: If True, return only unread notifications
            skip: Number of records to skip (pagination)
            limit: Maximum records to return (default 20, max 100)

        Returns:
            {notifications: [...], total_count, unread_count, has_more}

        Raises:
            ValidationError: If pagination parameters invalid
        """
        try:
            # Validate pagination
            if skip < 0:
                raise ValidationError("Skip must be >= 0")
            if limit < 1 or limit > 100:
                raise ValidationError("Limit must be between 1 and 100")

            # Validate user exists
            user = await self.repos.user.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")

            # Fetch notifications
            notifications, total_count = (
                await self.repos.notification.get_by_user_paginated(
                    user_id,
                    unread_only=unread_only,
                    skip=skip,
                    limit=limit,
                    order_by_desc=True,  # Newest first
                )
            )

            # Get total unread count
            unread_count = await self.repos.notification.count_unread(user_id)

            # Format response
            notifications_list = [
                {
                    "notification_id": str(n.id),
                    "title": n.title,
                    "message": n.message,
                    "type": n.type,
                    "data": json.loads(n.data) if n.data else None,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat(),
                    "read_at": n.read_at.isoformat() if n.read_at else None,
                }
                for n in notifications
            ]

            has_more = (skip + limit) < total_count

            return self.success_response(
                data={
                    "notifications": notifications_list,
                    "total_count": total_count,
                    "unread_count": unread_count,
                    "skip": skip,
                    "limit": limit,
                    "has_more": has_more,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error fetching notifications: {str(e)}")
            raise ValidationError(f"Failed to fetch notifications: {str(e)}")

    async def mark_as_read(self, notification_id: UUID) -> dict:
        """
        Mark a single notification as read.

        Args:
            notification_id: UUID of notification to mark as read

        Returns:
            {notification_id, is_read, read_at}

        Raises:
            NotFoundError: If notification not found
        """
        try:
            # Fetch notification
            notification = await self.repos.notification.get_by_id(notification_id)
            if not notification:
                raise NotFoundError(f"Notification {notification_id} not found")

            # Update to read if not already
            async with self.transaction():
                if not notification.is_read:
                    await self.repos.notification.update(
                        notification,
                        {
                            "is_read": True,
                            "read_at": datetime.now(),
                        },
                    )

                    # Log audit
                    self.log_action(
                        action="MARK_NOTIFICATION_READ",
                        entity_type="Notification",
                        entity_id=str(notification_id),
                        user_id=str(notification.user_id),
                        changes={"is_read": True},
                    )

            return self.success_response(
                data={
                    "notification_id": str(notification.id),
                    "is_read": notification.is_read,
                    "read_at": notification.read_at.isoformat()
                    if notification.read_at
                    else None,
                }
            )

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error marking notification as read: {str(e)}")
            raise ValidationError(f"Failed to mark as read: {str(e)}")

    async def mark_all_as_read(self, user_id: UUID) -> dict:
        """
        Mark all unread notifications as read for a user.

        Args:
            user_id: UUID of user

        Returns:
            {total_marked, user_id}

        Raises:
            NotFoundError: If user not found
        """
        try:
            # Validate user exists
            user = await self.repos.user.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")

            async with self.transaction():
                # Fetch all unread notifications for user
                unread_notifications = (
                    await self.repos.notification.get_unread_by_user(user_id)
                )

                # Update all to read
                total_marked = 0
                for notification in unread_notifications:
                    await self.repos.notification.update(
                        notification,
                        {
                            "is_read": True,
                            "read_at": datetime.now(),
                        },
                    )
                    total_marked += 1

                # Log audit
                self.log_action(
                    action="MARK_ALL_NOTIFICATIONS_READ",
                    entity_type="Notification",
                    entity_id="BATCH",
                    user_id=str(user_id),
                    changes={"total_marked": total_marked},
                )

            return self.success_response(
                data={
                    "total_marked": total_marked,
                    "user_id": str(user_id),
                }
            )

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error marking all as read: {str(e)}")
            raise ValidationError(f"Failed to mark all as read: {str(e)}")

    async def send_bulk_notification(
        self,
        user_ids: List[UUID],
        title: str,
        message: str,
        notification_type: str,
        data: Optional[dict] = None,
    ) -> dict:
        """
        Send notification to multiple users efficiently.

        Batch inserts for large broadcasts (e.g., 500+ students).

        Args:
            user_ids: List of user UUIDs to notify
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            data: Optional JSON data payload

        Returns:
            {total_sent, failed_count, notification_ids: [...]}

        Raises:
            ValidationError: If invalid parameters
        """
        try:
            # Validate inputs
            if not user_ids:
                raise ValidationError("User list cannot be empty")
            if len(user_ids) > 10000:
                raise ValidationError("Cannot send to more than 10,000 users at once")

            if notification_type not in VALID_NOTIFICATION_TYPES:
                raise ValidationError(
                    f"Invalid notification type: {notification_type}"
                )

            if not title or len(title.strip()) == 0:
                raise ValidationError("Notification title cannot be empty")
            if not message or len(message.strip()) == 0:
                raise ValidationError("Notification message cannot be empty")

            # Serialize data
            data_json = json.dumps(data) if data else None

            # Prepare batch create
            async with self.transaction():
                # Verify all users exist
                existing_users = await self.repos.user.get_by_ids(user_ids)
                existing_user_ids = {u.id for u in existing_users}
                invalid_users = set(user_ids) - existing_user_ids

                notification_records = []
                for user_id in existing_user_ids:
                    notification_records.append(
                        {
                            "user_id": user_id,
                            "title": title,
                            "message": message,
                            "type": notification_type,
                            "data": data_json,
                            "created_at": datetime.now(),
                            "is_read": False,
                        }
                    )

                # Batch insert
                created_notifications = (
                    await self.repos.notification.create_bulk(notification_records)
                )

                # Log audit
                self.log_action(
                    action="SEND_BULK_NOTIFICATION",
                    entity_type="Notification",
                    entity_id="BATCH",
                    user_id="SYSTEM",
                    changes={
                        "total_sent": len(created_notifications),
                        "failed_count": len(invalid_users),
                        "title": title,
                        "type": notification_type,
                    },
                )

            return self.success_response(
                data={
                    "total_sent": len(created_notifications),
                    "failed_count": len(invalid_users),
                    "notification_ids": [str(n.id) for n in created_notifications],
                }
            )

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error sending bulk notification: {str(e)}")
            raise ValidationError(f"Failed to send bulk notification: {str(e)}")

    async def delete_notification(self, notification_id: UUID) -> dict:
        """
        Soft delete a notification (mark as deleted, don't remove from DB).

        Args:
            notification_id: UUID of notification to delete

        Returns:
            {message, notification_id}

        Raises:
            NotFoundError: If notification not found
        """
        try:
            # Fetch notification
            notification = await self.repos.notification.get_by_id(notification_id)
            if not notification:
                raise NotFoundError(f"Notification {notification_id} not found")

            # Soft delete
            async with self.transaction():
                await self.repos.notification.update(
                    notification,
                    {
                        "is_deleted": True,
                        "deleted_at": datetime.now(),
                    },
                )

                # Log audit
                self.log_action(
                    action="DELETE_NOTIFICATION",
                    entity_type="Notification",
                    entity_id=str(notification_id),
                    user_id=str(notification.user_id),
                    changes={"is_deleted": True},
                )

            return self.success_response(
                data={
                    "message": "Notification deleted successfully",
                    "notification_id": str(notification_id),
                }
            )

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error deleting notification: {str(e)}")
            raise ValidationError(f"Failed to delete notification: {str(e)}")

    async def send_scheduled_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str,
        send_at: datetime,
        data: Optional[dict] = None,
    ) -> dict:
        """
        Schedule a notification for delivery at a future time.

        Requires: Celery Beat for background scheduling.

        Args:
            user_id: UUID of recipient
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            send_at: Datetime when notification should be sent
            data: Optional JSON data payload

        Returns:
            {scheduled_notification_id, scheduled_for}

        Raises:
            NotFoundError: If user not found
            ValidationError: If invalid datetime or parameters
        """
        try:
            # Validate user exists
            user = await self.repos.user.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")

            # Validate notification type
            if notification_type not in VALID_NOTIFICATION_TYPES:
                raise ValidationError(f"Invalid notification type: {notification_type}")

            # Validate datetime
            if send_at <= datetime.now():
                raise ValidationError("Scheduled time must be in the future")

            # Validate title and message
            if not title or len(title.strip()) == 0:
                raise ValidationError("Notification title cannot be empty")
            if not message or len(message.strip()) == 0:
                raise ValidationError("Notification message cannot be empty")

            # Serialize data
            data_json = json.dumps(data) if data else None

            # Create scheduled notification record
            async with self.transaction():
                scheduled = await self.repos.scheduled_notification.create(
                    {
                        "user_id": user_id,
                        "title": title,
                        "message": message,
                        "type": notification_type,
                        "data": data_json,
                        "scheduled_for": send_at,
                        "created_at": datetime.now(),
                        "sent": False,
                    }
                )

                # Queue with Celery Beat
                try:
                    from app.celery_app import send_scheduled_notification_task

                    # Calculate delay in seconds
                    delay_seconds = (send_at - datetime.now()).total_seconds()
                    send_scheduled_notification_task.apply_async(
                        args=[str(scheduled.id)],
                        countdown=int(delay_seconds),
                    )
                except Exception as celery_error:
                    self.logger.warning(
                        f"Failed to queue Celery task: {str(celery_error)}"
                    )

                # Log audit
                self.log_action(
                    action="SCHEDULE_NOTIFICATION",
                    entity_type="ScheduledNotification",
                    entity_id=str(scheduled.id),
                    user_id=str(user_id),
                    changes={
                        "scheduled_for": send_at.isoformat(),
                        "title": title,
                        "type": notification_type,
                    },
                )

            return self.success_response(
                data={
                    "scheduled_notification_id": str(scheduled.id),
                    "scheduled_for": send_at.isoformat(),
                    "user_id": str(user_id),
                    "notification_type": notification_type,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error scheduling notification: {str(e)}")
            raise ValidationError(f"Failed to schedule notification: {str(e)}")

    async def cleanup_old_notifications(self, retention_days: int = 90) -> dict:
        """
        Clean up notifications older than retention period.

        Args:
            retention_days: Number of days to retain (default 90)

        Returns:
            {total_deleted, date_threshold}

        Raises:
            ValidationError: If retention_days invalid
        """
        try:
            # Validate retention days
            if retention_days < 1:
                raise ValidationError("Retention days must be at least 1")

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            async with self.transaction():
                # Delete old notifications (soft delete)
                total_deleted = (
                    await self.repos.notification.soft_delete_before_date(cutoff_date)
                )

                # Log audit
                self.log_action(
                    action="CLEANUP_OLD_NOTIFICATIONS",
                    entity_type="Notification",
                    entity_id="BATCH",
                    user_id="SYSTEM",
                    changes={
                        "total_deleted": total_deleted,
                        "retention_days": retention_days,
                        "date_threshold": cutoff_date.isoformat(),
                    },
                )

            return self.success_response(
                data={
                    "total_deleted": total_deleted,
                    "date_threshold": cutoff_date.isoformat(),
                    "retention_days": retention_days,
                }
            )

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error cleaning up notifications: {str(e)}")
            raise ValidationError(f"Failed to cleanup notifications: {str(e)}")
