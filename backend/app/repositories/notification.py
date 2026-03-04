"""
Notification Repository - Notifications, preferences, and reminders
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.notification import Notification, NotificationPreferences, Reminder
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Notification)
    
    async def get_user_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Notification], int]:
        """Get notifications for a user."""
        count_query = select(func.count(Notification.id)).where(
            Notification.recipient_id == user_id
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(Notification).where(
            Notification.recipient_id == user_id
        ).offset(skip).limit(limit).order_by(Notification.created_at.desc())
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_unread_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Notification], int]:
        """Get unread notifications for a user."""
        count_query = select(func.count(Notification.id)).where(
            and_(
                Notification.recipient_id == user_id,
                Notification.is_read == False
            )
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(Notification).where(
            and_(
                Notification.recipient_id == user_id,
                Notification.is_read == False
            )
        ).offset(skip).limit(limit).order_by(Notification.created_at.desc())
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def count_unread(self, user_id: UUID) -> int:
        """Count unread notifications for user."""
        count_query = select(func.count(Notification.id)).where(
            and_(
                Notification.recipient_id == user_id,
                Notification.is_read == False
            )
        )
        total = await self.db_session.scalar(count_query)
        return total or 0
    
    async def get_by_type(
        self,
        user_id: UUID,
        notification_type: str
    ) -> List[Notification]:
        """Get notifications of specific type for user."""
        query = select(Notification).where(
            and_(
                Notification.recipient_id == user_id,
                Notification.notification_type == notification_type
            )
        ).order_by(Notification.created_at.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_by_priority(
        self,
        user_id: UUID,
        priority: str
    ) -> List[Notification]:
        """Get notifications by priority."""
        query = select(Notification).where(
            and_(
                Notification.recipient_id == user_id,
                Notification.priority == priority
            )
        ).order_by(Notification.created_at.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def mark_as_read(self, notification_id: UUID) -> bool:
        """Mark notification as read."""
        notification = await self.get_by_id(notification_id)
        if not notification:
            return False
        
        from datetime import datetime
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        await self.db_session.commit()
        return True
    
    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for user."""
        # Get all unread notifications
        unread = await self.get_unread_notifications(user_id, skip=0, limit=9999)
        
        from datetime import datetime
        for notif in unread:
            notif.is_read = True
            notif.read_at = datetime.utcnow()
        
        await self.db_session.commit()
        return len(unread)


class NotificationPreferencesRepository(BaseRepository[NotificationPreferences]):
    """Repository for Notification Preferences"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, NotificationPreferences)
    
    async def get_by_user(self, user_id: UUID) -> Optional[NotificationPreferences]:
        """Get notification preferences for a user."""
        query = select(NotificationPreferences).where(
            NotificationPreferences.user_id == user_id
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def get_or_create(self, user_id: UUID) -> NotificationPreferences:
        """Get preferences or create default."""
        prefs = await self.get_by_user(user_id)
        
        if not prefs:
            prefs = NotificationPreferences(user_id=user_id)
            self.db_session.add(prefs)
            await self.db_session.commit()
            await self.db_session.refresh(prefs)
        
        return prefs


class ReminderRepository(BaseRepository[Reminder]):
    """Repository for Reminder queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Reminder)
    
    async def get_user_reminders(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Reminder], int]:
        """Get reminders for a user."""
        count_query = select(func.count(Reminder.id)).where(
            Reminder.user_id == user_id
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(Reminder).where(
            Reminder.user_id == user_id
        ).offset(skip).limit(limit).order_by(Reminder.remind_at.asc())
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_pending_reminders(self) -> List[Reminder]:
        """Get all unsent reminders."""
        from datetime import datetime
        
        now = datetime.utcnow()
        query = select(Reminder).where(
            and_(
                Reminder.is_sent == False,
                Reminder.remind_at <= now
            )
        ).order_by(Reminder.remind_at.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_upcoming_reminders(self, user_id: UUID) -> List[Reminder]:
        """Get upcoming unsent reminders for a user."""
        from datetime import datetime
        
        query = select(Reminder).where(
            and_(
                Reminder.user_id == user_id,
                Reminder.is_sent == False
            )
        ).order_by(Reminder.remind_at.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def mark_as_sent(self, reminder_id: UUID) -> bool:
        """Mark reminder as sent."""
        from datetime import datetime
        
        reminder = await self.get_by_id(reminder_id)
        if not reminder:
            return False
        
        reminder.is_sent = True
        reminder.reminded_at = datetime.utcnow()
        await self.db_session.commit()
        return True
    
    async def get_by_type(self, reminder_type: str) -> List[Reminder]:
        """Get reminders by type."""
        query = select(Reminder).where(
            Reminder.reminder_type == reminder_type
        ).order_by(Reminder.remind_at.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
