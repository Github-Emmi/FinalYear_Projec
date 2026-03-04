"""
Feedback Repository - Feedback, messaging, and announcements
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.feedback import Feedback, Message, Announcement
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[Feedback]):
    """Repository for Feedback queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Feedback)
    
    async def get_by_student(
        self,
        student_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Feedback], int]:
        """Get feedback submitted by a student."""
        count_query = select(func.count(Feedback.id)).where(
            Feedback.student_id == student_id
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(Feedback).where(
            Feedback.student_id == student_id
        ).offset(skip).limit(limit).order_by(Feedback.created_at.desc())
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_by_type(self, feedback_type: str) -> List[Feedback]:
        """Get feedback by type."""
        query = select(Feedback).where(
            Feedback.feedback_type == feedback_type
        ).order_by(Feedback.created_at.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Feedback], int]:
        """Get feedback by status."""
        count_query = select(func.count(Feedback.id)).where(
            Feedback.status == status
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(Feedback).where(
            Feedback.status == status
        ).offset(skip).limit(limit).order_by(Feedback.created_at.desc())
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_high_priority(self) -> List[Feedback]:
        """Get high priority feedback."""
        query = select(Feedback).where(
            Feedback.priority == "HIGH"
        ).order_by(Feedback.created_at.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_unresolved(self) -> List[Feedback]:
        """Get unresolved feedback."""
        query = select(Feedback).where(
            and_(
                Feedback.status.in_(["OPEN", "IN_REVIEW"])
            )
        ).order_by(Feedback.created_at.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()


class MessageRepository(BaseRepository[Message]):
    """Repository for Message queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Message)
    
    async def get_user_inbox(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Message], int]:
        """Get messages received by user."""
        count_query = select(func.count(Message.id)).where(
            Message.recipient_id == user_id
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(Message).where(
            Message.recipient_id == user_id
        ).offset(skip).limit(limit).order_by(Message.created_at.desc())
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_user_sent(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Message], int]:
        """Get messages sent by user."""
        count_query = select(func.count(Message.id)).where(
            Message.sender_id == user_id
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(Message).where(
            Message.sender_id == user_id
        ).offset(skip).limit(limit).order_by(Message.created_at.desc())
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_conversation(
        self,
        user_a: UUID,
        user_b: UUID
    ) -> List[Message]:
        """Get conversation between two users."""
        query = select(Message).where(
            and_(
                (Message.sender_id == user_a) & (Message.recipient_id == user_b) |
                (Message.sender_id == user_b) & (Message.recipient_id == user_a)
            )
        ).order_by(Message.created_at.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_unread_count(self, user_id: UUID) -> int:
        """Count unread messages for user."""
        count_query = select(func.count(Message.id)).where(
            and_(
                Message.recipient_id == user_id,
                Message.is_read == False
            )
        )
        total = await self.db_session.scalar(count_query)
        return total or 0
    
    async def mark_as_read(self, message_id: UUID) -> bool:
        """Mark message as read."""
        message = await self.get_by_id(message_id)
        if not message:
            return False
        
        message.is_read = True
        await self.db_session.commit()
        return True


class AnnouncementRepository(BaseRepository[Announcement]):
    """Repository for Announcement queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Announcement)
    
    async def get_active_announcements(self) -> List[Announcement]:
        """Get currently active announcements."""
        from datetime import datetime
        
        query = select(Announcement).where(
            Announcement.expires_at >= datetime.utcnow()
        ).order_by(Announcement.created_at.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_by_type(self, announcement_type: str) -> List[Announcement]:
        """Get announcements by type."""
        query = select(Announcement).where(
            Announcement.announcement_type == announcement_type
        ).order_by(Announcement.created_at.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_urgent_announcements(self) -> List[Announcement]:
        """Get urgent announcements."""
        query = select(Announcement).where(
            Announcement.announcement_type == "URGENT"
        ).order_by(Announcement.created_at.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_by_creator(self, creator_id: UUID) -> List[Announcement]:
        """Get announcements created by user."""
        query = select(Announcement).where(
            Announcement.created_by == creator_id
        ).order_by(Announcement.created_at.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
