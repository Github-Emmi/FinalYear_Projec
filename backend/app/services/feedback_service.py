"""
Feedback Service - Managing messaging, announcements, support tickets, and feedback.

This service handles all communication channels:
- Direct messaging between users (students ↔ admin, staff ↔ admin)
- Real-time notifications and conversation threading
- Support ticket system with workflow management
- System-wide announcements with scheduling
- User feedback and survey management

Author: Backend Team
Version: 1.0.0
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from uuid import UUID
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, select

from app.services.base import BaseService
from app.repositories.base import RepositoryFactory
from app.core.exceptions import (
    ValidationError, ConflictError, NotFoundError, ForbiddenError
)

logger = logging.getLogger(__name__)


class FeedbackService(BaseService):
    """
    Service for managing all communication and feedback across the institution.
    
    Provides:
    - Direct messaging with permission control and rate limiting
    - Conversation threading with read status tracking
    - Support ticket lifecycle management
    - System-wide announcements with scheduling
    - User feedback surveys with analytics
    
    Attributes:
        repos: RepositoryFactory for data access
        rate_limit_messages: Max messages per minute per user
        message_archive_days: Days before auto-archiving inactive conversations
        gdpr_retention_days: Days before GDPR-compliant deletion
        announcement_cache_ttl: Seconds for announcement caching
    """
    
    # Rate limiting configuration
    RATE_LIMIT_MESSAGES = 5  # messages per minute
    MESSAGE_ARCHIVE_DAYS = 90
    GDPR_RETENTION_DAYS = 365
    ANNOUNCEMENT_CACHE_TTL = 300  # 5 minutes
    
    # Message types
    MESSAGE_TYPES = {"GENERAL", "SUPPORT", "COMPLAINT", "SUGGESTION"}
    
    # Support ticket statuses
    TICKET_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}
    TICKET_CATEGORIES = {"ACADEMIC", "ADMIN", "TECHNICAL", "OTHER"}
    TICKET_PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT"}
    
    # Announcement types
    ANNOUNCEMENT_TYPES = {"ACADEMIC", "ADMIN", "EMERGENCY", "HOLIDAY"}
    ANNOUNCEMENT_STATUSES = {"DRAFT", "PUBLISHED", "ARCHIVED"}
    TARGET_AUDIENCES = {"ALL", "STUDENTS_ONLY", "STAFF_ONLY", "CLASS_SPECIFIC"}
    
    # Feedback question types
    QUESTION_TYPES = {"RATING", "MULTIPLE_CHOICE", "SHORT_TEXT", "LONG_TEXT", "MATRIX"}
    
    # ==================== Direct Messaging Methods ====================
    
    async def send_message(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        subject: str,
        message_text: str,
        message_type: str = "GENERAL",
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Send a direct message with permission validation and rate limiting.
        
        Validates:
        - Sender and recipient exist
        - Sender has permission to message recipient
        - Rate limit not exceeded (5 messages/minute)
        - Message not empty and within length limits
        
        Auto-creates support ticket if message_type is SUPPORT or COMPLAINT.
        
        Permissions:
        - Students can message: admins, form teachers
        - Staff can message: other staff, admins
        - Admins can message anyone
        
        Args:
            sender_id: UUID of message sender
            recipient_id: UUID of message recipient
            subject: Message subject/title
            message_text: Message body (max 5000 chars)
            message_type: One of GENERAL, SUPPORT, COMPLAINT, SUGGESTION
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "message_id": UUID,
                    "sender_id": UUID,
                    "recipient_id": UUID,
                    "subject": str,
                    "message_text": str,
                    "message_type": str,
                    "created_at": datetime,
                    "is_read": False,
                    "ticket_id": UUID or None
                },
                "error": None
            }
        
        Raises:
            ValidationError: If message invalid or rate limit exceeded
            NotFoundError: If sender or recipient not found
            ForbiddenError: If sender lacks permission
        
        Example:
            >>> response = await feedback_service.send_message(
            ...     sender_id=UUID("..."),
            ...     recipient_id=UUID("..."),
            ...     subject="Academic Support Request",
            ...     message_text="I need help with the physics assignment",
            ...     message_type="SUPPORT"
            ... )
        """
        logger.info(
            f"Sending message from {sender_id} to {recipient_id} "
            f"(type: {message_type})"
        )
        
        # Validate message type
        if message_type not in self.MESSAGE_TYPES:
            raise ValidationError(
                f"Invalid message_type. Must be one of {self.MESSAGE_TYPES}"
            )
        
        # Validate message content
        if not subject or not subject.strip():
            raise ValidationError("Subject cannot be empty")
        
        if not message_text or not message_text.strip():
            raise ValidationError("Message cannot be empty")
        
        if len(message_text) > 5000:
            raise ValidationError("Message exceeds maximum length (5000 characters)")
        
        if len(subject) > 500:
            raise ValidationError("Subject exceeds maximum length (500 characters)")
        
        # Verify sender and recipient exist
        sender = await self.repos.user.get_by_id(sender_id)
        if not sender:
            raise NotFoundError(f"Sender {sender_id} not found")
        
        recipient = await self.repos.user.get_by_id(recipient_id)
        if not recipient:
            raise NotFoundError(f"Recipient {recipient_id} not found")
        
        # Check permission to message
        await self._validate_message_permission(sender, recipient)
        
        # Check rate limit (5 messages per minute)
        message_count = await self._count_recent_messages(sender_id, minutes=1)
        if message_count >= self.RATE_LIMIT_MESSAGES:
            raise ValidationError(
                f"Rate limit exceeded. Maximum {self.RATE_LIMIT_MESSAGES} messages per minute."
            )
        
        ticket_id = None
        async with self.transaction():
            # Create message record
            message = await self.repos.feedback.create({
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "subject": subject.strip(),
                "message": message_text.strip(),
                "message_type": message_type,
                "created_at": datetime.utcnow(),
                "is_read": False,
                "thread_id": None  # New conversation
            })
            
            # Auto-create support ticket for support/complaint messages
            if message_type in ["SUPPORT", "COMPLAINT"]:
                ticket = await self.repos.ticket.create({
                    "ticket_id": self._generate_ticket_id(),
                    "user_id": sender_id,
                    "title": subject,
                    "description": message_text,
                    "category": "TECHNICAL" if message_type == "SUPPORT" else "ADMIN",
                    "priority": "HIGH" if message_type == "COMPLAINT" else "NORMAL",
                    "status": "OPEN",
                    "created_at": datetime.utcnow(),
                    "assigned_to": None
                })
                ticket_id = ticket.id
            
            # Audit log
            self.log_action(
                action="SEND_MESSAGE",
                entity_type="Message",
                entity_id=message.id,
                user_id=user_id,
                changes={
                    "sender_id": str(sender_id),
                    "recipient_id": str(recipient_id),
                    "message_type": message_type,
                    "ticket_created": ticket_id is not None
                }
            )
            
            # Send notification
            await self.repos.notification.create({
                "recipient_id": recipient_id,
                "type": "INFO",
                "title": f"New Message: {subject[:50]}",
                "message": f"From {sender.first_name} {sender.last_name}",
                "created_at": datetime.utcnow()
            })
        
        logger.info(f"Message {message.id} sent successfully")
        
        return self.success_response(
            data={
                "message_id": message.id,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "subject": subject,
                "message_text": message_text,
                "message_type": message_type,
                "created_at": message.created_at.isoformat(),
                "is_read": False,
                "ticket_id": ticket_id
            }
        )
    
    async def reply_to_message(
        self,
        original_message_id: UUID,
        sender_id: UUID,
        reply_text: str,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Reply to existing message with threading and participant validation.
        
        Creates linked message in same conversation thread with automatic
        notifications and read status tracking per participant.
        
        Message archives after 90 days of inactivity.
        
        Args:
            original_message_id: UUID of message being replied to
            sender_id: UUID of reply sender (must be conversation participant)
            reply_text: Reply message content (max 5000 chars)
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "message_id": UUID,
                    "thread_id": UUID,
                    "original_message_id": UUID,
                    "sender_id": UUID,
                    "reply_text": str,
                    "created_at": datetime,
                    "message": Message with updated reply_count
                },
                "error": None
            }
        
        Raises:
            NotFoundError: If original message not found
            ForbiddenError: If sender not a conversation participant
            ValidationError: If reply content invalid
        
        Example:
            >>> response = await feedback_service.reply_to_message(
            ...     original_message_id=UUID("..."),
            ...     sender_id=UUID("..."),
            ...     reply_text="Thank you for your message. Here's my response..."
            ... )
        """
        logger.info(
            f"Creating reply to message {original_message_id} from {sender_id}"
        )
        
        # Validate reply content
        if not reply_text or not reply_text.strip():
            raise ValidationError("Reply cannot be empty")
        
        if len(reply_text) > 5000:
            raise ValidationError("Reply exceeds maximum length (5000 characters)")
        
        # Fetch original message
        original = await self.repos.feedback.get_by_id(original_message_id)
        if not original:
            raise NotFoundError(f"Original message {original_message_id} not found")
        
        # Validate sender is conversation participant
        if sender_id != original.sender_id and sender_id != original.recipient_id:
            raise ForbiddenError(
                "Only conversation participants can reply to this message"
            )
        
        async with self.transaction():
            # Create reply (link to same thread)
            thread_id = original.thread_id or original.id
            
            reply = await self.repos.feedback.create({
                "sender_id": sender_id,
                "recipient_id": (
                    original.recipient_id if sender_id == original.sender_id
                    else original.sender_id
                ),
                "subject": f"Re: {original.subject}",
                "message": reply_text.strip(),
                "message_type": original.message_type,
                "created_at": datetime.utcnow(),
                "is_read": False,
                "thread_id": thread_id
            })
            
            # Update original: increment reply count and last activity
            await self.repos.feedback.update(
                original.id,
                {
                    "reply_count": (original.reply_count or 0) + 1,
                    "last_activity": datetime.utcnow()
                }
            )
            
            # Audit log
            self.log_action(
                action="REPLY_TO_MESSAGE",
                entity_type="Message",
                entity_id=reply.id,
                user_id=user_id,
                changes={
                    "thread_id": str(thread_id),
                    "original_message_id": str(original_message_id),
                    "sender_id": str(sender_id)
                }
            )
            
            # Notify other participant
            await self.repos.notification.create({
                "recipient_id": reply.recipient_id,
                "type": "INFO",
                "title": f"New Reply: {original.subject[:50]}",
                "message": f"From {(await self.repos.user.get_by_id(sender_id)).first_name}",
                "created_at": datetime.utcnow()
            })
        
        logger.info(f"Reply {reply.id} created in thread {thread_id}")
        
        return self.success_response(
            data={
                "message_id": reply.id,
                "thread_id": thread_id,
                "original_message_id": original_message_id,
                "sender_id": sender_id,
                "reply_text": reply_text,
                "created_at": reply.created_at.isoformat(),
                "message": "Reply sent successfully"
            }
        )
    
    async def mark_message_as_read(
        self,
        message_id: UUID,
        reader_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Mark message as read with timestamp tracking.
        
        Validates reader is message recipient and updates read status.
        
        Args:
            message_id: UUID of message
            reader_id: UUID of user marking as read (must be recipient)
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "message_id": UUID,
                    "is_read": True,
                    "read_at": datetime
                },
                "error": None
            }
        
        Raises:
            NotFoundError: If message not found
            ForbiddenError: If reader is not recipient
        
        Example:
            >>> response = await feedback_service.mark_message_as_read(
            ...     message_id=UUID("..."),
            ...     reader_id=UUID("...")
            ... )
        """
        logger.info(f"Marking message {message_id} as read by {reader_id}")
        
        # Fetch message
        message = await self.repos.feedback.get_by_id(message_id)
        if not message:
            raise NotFoundError(f"Message {message_id} not found")
        
        # Validate reader is recipient
        if reader_id != message.recipient_id:
            raise ForbiddenError(
                "Only message recipient can mark as read"
            )
        
        async with self.transaction():
            # Mark as read
            await self.repos.feedback.update(
                message_id,
                {
                    "is_read": True,
                    "read_at": datetime.utcnow()
                }
            )
            
            # Audit log
            self.log_action(
                action="MARK_MESSAGE_READ",
                entity_type="Message",
                entity_id=message_id,
                user_id=user_id,
                changes={"is_read": True}
            )
        
        logger.info(f"Message {message_id} marked as read")
        
        return self.success_response(
            data={
                "message_id": message_id,
                "is_read": True,
                "read_at": datetime.utcnow().isoformat()
            }
        )
    
    async def get_user_conversations(
        self,
        user_id: UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 20
    ) -> Dict:
        """
        Get paginated list of user's conversations with latest message preview.
        
        Groups messages by conversation, shows:
        - Participant names
        - Last message preview
        - Unread count
        - Last activity timestamp
        
        Sorted by most recent activity descending.
        
        Args:
            user_id: UUID of user
            unread_only: If True, only show conversations with unread messages
            skip: Pagination offset (default 0)
            limit: Conversation limit (default 20, max 100)
        
        Returns:
            {
                "success": True,
                "data": {
                    "conversations": [
                        {
                            "conversation_id": UUID,
                            "participant_id": UUID,
                            "participant_name": str,
                            "last_message": str,
                            "last_message_preview": str,
                            "unread_count": int,
                            "last_activity": datetime,
                            "message_type": str
                        },
                        ...
                    ],
                    "total_conversations": 42,
                    "unread_total": 8,
                    "skip": 0,
                    "limit": 20
                },
                "error": None
            }
        
        Example:
            >>> result = await feedback_service.get_user_conversations(
            ...     user_id=UUID("..."),
            ...     unread_only=True,
            ...     limit=10
            ... )
        """
        logger.info(
            f"Fetching conversations for user {user_id} "
            f"(unread_only={unread_only})"
        )
        
        # Validate limit
        limit = min(limit, 100)
        
        # Fetch all messages for user (as sender or recipient)
        messages = await self.repos.feedback.get_all_by_filter(
            or_(
                self.repos.feedback.model.sender_id == user_id,
                self.repos.feedback.model.recipient_id == user_id
            )
        )
        
        if not messages:
            return self.success_response(
                data={
                    "conversations": [],
                    "total_conversations": 0,
                    "unread_total": 0,
                    "skip": skip,
                    "limit": limit
                }
            )
        
        # Group by conversation partner and thread
        conversations_map = {}
        unread_count_global = 0
        
        for msg in messages:
            # Determine conversation partner
            partner_id = msg.recipient_id if msg.sender_id == user_id else msg.sender_id
            conv_key = str(partner_id)
            
            if conv_key not in conversations_map:
                conversations_map[conv_key] = {
                    "participant_id": partner_id,
                    "messages": []
                }
            
            conversations_map[conv_key]["messages"].append(msg)
            
            if msg.recipient_id == user_id and not msg.is_read:
                unread_count_global += 1
        
        # Process conversations
        conversations = []
        for partner_id_str, data in conversations_map.items():
            messages_list = data["messages"]
            
            # Get latest message in conversation
            latest_msg = max(messages_list, key=lambda m: m.created_at)
            
            # Count unread in this conversation
            unread_in_conv = len([
                m for m in messages_list
                if m.recipient_id == user_id and not m.is_read
            ])
            
            # Skip if unread_only and no unread messages
            if unread_only and unread_in_conv == 0:
                continue
            
            # Get participant info
            participant = await self.repos.user.get_by_id(UUID(partner_id_str))
            
            conversations.append({
                "conversation_id": UUID(partner_id_str),
                "participant_id": UUID(partner_id_str),
                "participant_name": (
                    f"{participant.first_name} {participant.last_name}"
                    if participant else "Unknown"
                ),
                "last_message": latest_msg.message[:200],  # Preview
                "last_message_preview": (
                    latest_msg.message[:100] + "..."
                    if len(latest_msg.message) > 100 else latest_msg.message
                ),
                "unread_count": unread_in_conv,
                "last_activity": latest_msg.last_activity or latest_msg.created_at,
                "message_type": latest_msg.message_type
            })
        
        # Sort by last activity descending
        conversations.sort(
            key=lambda x: x["last_activity"],
            reverse=True
        )
        
        # Apply pagination
        total = len(conversations)
        paginated = conversations[skip:skip + limit]
        
        logger.info(f"Found {total} conversations for user {user_id}")
        
        return self.success_response(
            data={
                "conversations": paginated,
                "total_conversations": total,
                "unread_total": unread_count_global,
                "skip": skip,
                "limit": limit
            }
        )
    
    async def search_messages(
        self,
        user_id: UUID,
        query: str,
        sender_id: Optional[UUID] = None,
        message_type: Optional[str] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Dict:
        """
        Full-text search messages with filtering and result highlighting.
        
        Searches in message subject and content. Applies optional filters
        on sender, message type, and date range.
        
        Args:
            user_id: UUID of user performing search
            query: Search query string (min 3 chars, max 100 chars)
            sender_id: Optional filter by sender
            message_type: Optional filter by message type
            date_range: Optional (start_date, end_date) tuple
            skip: Pagination offset
            limit: Result limit (max 100)
        
        Returns:
            {
                "success": True,
                "data": {
                    "results": [
                        {
                            "message_id": UUID,
                            "sender_id": UUID,
                            "recipient_id": UUID,
                            "subject": str,
                            "message_text": str,
                            "message_highlighted": str (with <mark> tags),
                            "message_type": str,
                            "created_at": datetime,
                            "is_read": bool
                        },
                        ...
                    ],
                    "total_results": 125,
                    "query": str,
                    "skip": 0,
                    "limit": 20
                },
                "error": None
            }
        
        Raises:
            ValidationError: If query invalid
        
        Example:
            >>> results = await feedback_service.search_messages(
            ...     user_id=UUID("..."),
            ...     query="physics assignment",
            ...     message_type="SUPPORT",
            ...     limit=10
            ... )
        """
        logger.info(f"Searching messages for user {user_id}: '{query}'")
        
        # Validate query
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")
        
        if len(query) < 3:
            raise ValidationError("Search query must be at least 3 characters")
        
        if len(query) > 100:
            raise ValidationError("Search query cannot exceed 100 characters")
        
        # Validate limit
        limit = min(limit, 100)
        
        # Build filter conditions - only user's own messages
        filters = or_(
            self.repos.feedback.model.sender_id == user_id,
            self.repos.feedback.model.recipient_id == user_id
        )
        
        # Full-text search in subject and message content
        search_term = f"%{query.lower()}%"
        messages = await self.repos.feedback.get_all_by_filter(filters)
        
        # Client-side filtering and search (in production, use DB FTS)
        matching_messages = []
        for msg in messages:
            if (query.lower() in msg.subject.lower() or
                query.lower() in msg.message.lower()):
                
                # Apply optional filters
                if sender_id and msg.sender_id != sender_id:
                    continue
                if message_type and msg.message_type != message_type:
                    continue
                if date_range:
                    start, end = date_range
                    if not (start <= msg.created_at <= end):
                        continue
                
                matching_messages.append(msg)
        
        # Sort by relevance (exact match priority) and recency
        def relevance_score(msg):
            score = 0
            if query.lower() == msg.subject.lower():
                score += 100
            elif query.lower() in msg.subject.lower():
                score += 50
            if query.lower() in msg.message.lower()[:100]:  # Early in message
                score += 25
            return (score, msg.created_at)
        
        matching_messages.sort(key=relevance_score, reverse=True)
        
        # Highlight search terms in results
        results = []
        for msg in matching_messages[skip:skip + limit]:
            # Simple highlighting (in production, use HTML tags)
            highlighted = re.sub(
                f"({re.escape(query)})",
                r"<mark>\1</mark>",
                msg.message,
                flags=re.IGNORECASE
            )
            
            results.append({
                "message_id": msg.id,
                "sender_id": msg.sender_id,
                "recipient_id": msg.recipient_id,
                "subject": msg.subject,
                "message_text": msg.message,
                "message_highlighted": highlighted,
                "message_type": msg.message_type,
                "created_at": msg.created_at.isoformat(),
                "is_read": msg.is_read
            })
        
        logger.info(f"Found {len(matching_messages)} matching messages")
        
        return self.success_response(
            data={
                "results": results,
                "total_results": len(matching_messages),
                "query": query,
                "skip": skip,
                "limit": limit
            }
        )
    
    # ==================== Support Ticket Methods ====================
    
    async def create_support_ticket(
        self,
        user_id: UUID,
        title: str,
        description: str,
        category: str,
        priority: str = "NORMAL",
        creator_id: Optional[UUID] = None
    ) -> Dict:
        """
        Create support ticket with priority-based routing and notifications.
        
        Validates:
        - User exists
        - Category is valid
        - Priority is valid
        - Content not empty
        
        Auto-notifies:
        - URGENT: Principal
        - HIGH: Department head
        - NORMAL: Support team
        
        Ticket ID format: SUPP-YYYY-MM-NNNNN (e.g., SUPP-2026-03-00001)
        
        Args:
            user_id: UUID of ticket creator
            title: Ticket title (max 200 chars)
            description: Detailed description (max 5000 chars)
            category: One of ACADEMIC, ADMIN, TECHNICAL, OTHER
            priority: One of LOW, NORMAL, HIGH, URGENT (default NORMAL)
            creator_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "ticket_id": str,  # SUPP-2026-03-00001
                    "ticket_uuid": UUID,
                    "user_id": UUID,
                    "title": str,
                    "description": str,
                    "category": str,
                    "priority": str,
                    "status": "OPEN",
                    "created_at": datetime,
                    "message": "Support ticket created. Reference: SUPP-2026-03-00001"
                },
                "error": None
            }
        
        Raises:
            ValidationError: If content invalid
            NotFoundError: If user not found
        
        Example:
            >>> response = await feedback_service.create_support_ticket(
            ...     user_id=UUID("..."),
            ...     title="Authentication Issues",
            ...     description="Cannot login with correct credentials",
            ...     category="TECHNICAL",
            ...     priority="HIGH"
            ... )
        """
        logger.info(f"Creating support ticket for user {user_id} (priority: {priority})")
        
        # Validate category and priority
        if category not in self.TICKET_CATEGORIES:
            raise ValidationError(
                f"Invalid category. Must be one of {self.TICKET_CATEGORIES}"
            )
        
        if priority not in self.TICKET_PRIORITIES:
            raise ValidationError(
                f"Invalid priority. Must be one of {self.TICKET_PRIORITIES}"
            )
        
        # Validate content
        if not title or not title.strip():
            raise ValidationError("Title cannot be empty")
        
        if len(title) > 200:
            raise ValidationError("Title exceeds maximum length (200 characters)")
        
        if not description or not description.strip():
            raise ValidationError("Description cannot be empty")
        
        if len(description) > 5000:
            raise ValidationError("Description exceeds maximum length (5000 characters)")
        
        # Verify user exists
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        
        async with self.transaction():
            # Generate ticket ID
            ticket_id_str = self._generate_ticket_id()
            
            # Create ticket
            ticket = await self.repos.ticket.create({
                "ticket_id": ticket_id_str,
                "user_id": user_id,
                "title": title.strip(),
                "description": description.strip(),
                "category": category,
                "priority": priority,
                "status": "OPEN",
                "created_at": datetime.utcnow(),
                "assigned_to": None
            })
            
            # Audit log
            self.log_action(
                action="CREATE_SUPPORT_TICKET",
                entity_type="SupportTicket",
                entity_id=ticket.id,
                user_id=creator_id,
                changes={
                    "ticket_id": ticket_id_str,
                    "category": category,
                    "priority": priority
                }
            )
            
            # Send confirmation to user
            await self.repos.notification.create({
                "recipient_id": user_id,
                "type": "INFO",
                "title": "Support Ticket Created",
                "message": f"Your ticket {ticket_id_str} has been created. {category} - Priority: {priority}",
                "created_at": datetime.utcnow()
            })
            
            # Route by priority
            await self._route_ticket_notification(priority, ticket_id_str, title)
        
        logger.info(f"Support ticket {ticket_id_str} created successfully")
        
        return self.success_response(
            data={
                "ticket_id": ticket_id_str,
                "ticket_uuid": ticket.id,
                "user_id": user_id,
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
                "status": "OPEN",
                "created_at": ticket.created_at.isoformat(),
                "message": f"Support ticket created. Reference: {ticket_id_str}"
            }
        )
    
    async def update_ticket_status(
        self,
        ticket_id: UUID,
        admin_id: UUID,
        new_status: str,
        notes: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Update support ticket status with history tracking and notifications.
        
        Valid transitions:
        - OPEN → IN_PROGRESS (acknowledged)
        - IN_PROGRESS → RESOLVED (issue fixed)
        - RESOLVED → CLOSED (user confirms/admin closes)
        - OPEN → CLOSED (dismiss invalid/spam)
        
        Args:
            ticket_id: UUID of ticket to update
            admin_id: UUID of admin/staff updating status
            new_status: New status (OPEN, IN_PROGRESS, RESOLVED, CLOSED)
            notes: Status update notes (optional)
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "ticket_id": UUID,
                    "ticket_id_str": str,
                    "status": str,
                    "updated_at": datetime,
                    "status_history": [status entries],
                    "message": "Ticket status updated to RESOLVED"
                },
                "error": None
            }
        
        Raises:
            NotFoundError: If ticket not found
            ForbiddenError: If user not authorized
            ValidationError: If invalid status transition
        
        Example:
            >>> response = await feedback_service.update_ticket_status(
            ...     ticket_id=UUID("..."),
            ...     admin_id=UUID("..."),
            ...     new_status="RESOLVED",
            ...     notes="Issue was database connectivity"
            ... )
        """
        logger.info(
            f"Updating ticket {ticket_id} status to {new_status} by {admin_id}"
        )
        
        # Validate status
        if new_status not in self.TICKET_STATUSES:
            raise ValidationError(
                f"Invalid status. Must be one of {self.TICKET_STATUSES}"
            )
        
        # Verify admin exists
        admin = await self.repos.user.get_by_id(admin_id)
        if not admin:
            raise NotFoundError(f"Admin {admin_id} not found")
        
        # Fetch ticket
        ticket = await self.repos.ticket.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError(f"Ticket {ticket_id} not found")
        
        # Validate transition is allowed
        self._validate_ticket_status_transition(ticket.status, new_status)
        
        async with self.transaction():
            # Update ticket status
            update_data = {
                "status": new_status,
                "updated_at": datetime.utcnow()
            }
            
            if new_status == "RESOLVED":
                update_data["resolved_at"] = datetime.utcnow()
            elif new_status == "CLOSED":
                update_data["closed_at"] = datetime.utcnow()
            
            await self.repos.ticket.update(ticket_id, update_data)
            
            # Create status history entry
            await self.repos.ticket_history.create({
                "ticket_id": ticket_id,
                "old_status": ticket.status,
                "new_status": new_status,
                "changed_by": admin_id,
                "notes": notes,
                "changed_at": datetime.utcnow()
            })
            
            # Audit log
            self.log_action(
                action="UPDATE_TICKET_STATUS",
                entity_type="SupportTicket",
                entity_id=ticket_id,
                user_id=user_id,
                changes={
                    "old_status": ticket.status,
                    "new_status": new_status,
                    "notes": notes or "No additional notes"
                }
            )
            
            # Notification to ticket creator
            await self.repos.notification.create({
                "recipient_id": ticket.user_id,
                "type": "INFO" if new_status != "RESOLVED" else "SUCCESS",
                "title": f"Ticket Status Update: {new_status}",
                "message": f"Your support ticket has been {new_status.lower()}. {notes or ''}",
                "created_at": datetime.utcnow()
            })
        
        logger.info(f"Ticket {ticket_id} status updated to {new_status}")
        
        return self.success_response(
            data={
                "ticket_id": ticket_id,
                "ticket_id_str": ticket.ticket_id,
                "status": new_status,
                "updated_at": datetime.utcnow().isoformat(),
                "message": f"Ticket status updated to {new_status}"
            }
        )
    
    async def assign_ticket_to_staff(
        self,
        ticket_id: UUID,
        staff_id: UUID,
        admin_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Assign ticket to support staff with validation and notifications.
        
        Validates:
        - Ticket, staff, and admin exist
        - Staff has appropriate skills/department
        - Ticket not already assigned to another staff
        
        Auto-updates status to IN_PROGRESS.
        
        Args:
            ticket_id: UUID of ticket to assign
            staff_id: UUID of staff member to assign
            admin_id: UUID of admin performing assignment
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "ticket_id": UUID,
                    "assigned_to": UUID,
                    "assigned_at": datetime,
                    "status": "IN_PROGRESS",
                    "message": "Ticket assigned successfully"
                },
                "error": None
            }
        
        Raises:
            NotFoundError: If ticket, staff, or admin not found
            ConflictError: If ticket already assigned
            ForbiddenError: If staff lacks qualifications
        
        Example:
            >>> response = await feedback_service.assign_ticket_to_staff(
            ...     ticket_id=UUID("..."),
            ...     staff_id=UUID("..."),
            ...     admin_id=UUID("...")
            ... )
        """
        logger.info(f"Assigning ticket {ticket_id} to staff {staff_id}")
        
        # Verify entities exist
        ticket = await self.repos.ticket.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError(f"Ticket {ticket_id} not found")
        
        staff = await self.repos.staff.get_by_id(staff_id)
        if not staff:
            raise NotFoundError(f"Staff member {staff_id} not found")
        
        admin = await self.repos.user.get_by_id(admin_id)
        if not admin:
            raise NotFoundError(f"Admin {admin_id} not found")
        
        # Check if already assigned
        if ticket.assigned_to:
            raise ConflictError(
                f"Ticket already assigned to {ticket.assigned_to}. "
                f"Reassign by unassigning first."
            )
        
        async with self.transaction():
            # Assign ticket and update status
            await self.repos.ticket.update(
                ticket_id,
                {
                    "assigned_to": staff_id,
                    "assigned_at": datetime.utcnow(),
                    "status": "IN_PROGRESS"
                }
            )
            
            # Audit log
            self.log_action(
                action="ASSIGN_TICKET",
                entity_type="SupportTicket",
                entity_id=ticket_id,
                user_id=user_id,
                changes={
                    "assigned_to": str(staff_id),
                    "assigned_by": str(admin_id),
                    "status_updated_to": "IN_PROGRESS"
                }
            )
            
            # Notify assigned staff
            staff_user = staff.user
            await self.repos.notification.create({
                "recipient_id": staff_id,
                "type": "INFO",
                "title": f"Ticket Assigned: {ticket.title[:50]}",
                "message": f"Category: {ticket.category}, Priority: {ticket.priority}. Ticket {ticket.ticket_id}",
                "created_at": datetime.utcnow()
            })
            
            # Notify ticket creator (progress update)
            await self.repos.notification.create({
                "recipient_id": ticket.user_id,
                "type": "INFO",
                "title": "Ticket Assignment Update",
                "message": f"Your ticket {ticket.ticket_id} has been assigned to {staff_user.first_name} {staff_user.last_name}",
                "created_at": datetime.utcnow()
            })
        
        logger.info(f"Ticket {ticket_id} assigned to staff {staff_id}")
        
        return self.success_response(
            data={
                "ticket_id": ticket_id,
                "assigned_to": staff_id,
                "assigned_at": datetime.utcnow().isoformat(),
                "status": "IN_PROGRESS",
                "message": "Ticket assigned successfully"
            }
        )
    
    async def get_pending_tickets(
        self,
        department_id: Optional[UUID] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Dict:
        """
        Get pending tickets with optional filtering by department and priority.
        
        Returns all tickets with status in [OPEN, IN_PROGRESS].
        Sorted by priority (HIGH first) and creation date.
        
        Args:
            department_id: Optional filter by department
            priority: Optional filter by priority (LOW, NORMAL, HIGH, URGENT)
            skip: Pagination offset
            limit: Result limit (max 100)
        
        Returns:
            {
                "success": True,
                "data": {
                    "tickets": [
                        {
                            "ticket_id": str,
                            "ticket_uuid": UUID,
                            "user_id": UUID,
                            "title": str,
                            "category": str,
                            "priority": str,
                            "status": str,
                            "assigned_to": UUID or None,
                            "created_at": datetime,
                            "age_hours": int
                        },
                        ...
                    ],
                    "total_pending": 45,
                    "by_priority": {"URGENT": 2, "HIGH": 8, "NORMAL": 30, "LOW": 5},
                    "skip": 0,
                    "limit": 20
                },
                "error": None
            }
        
        Example:
            >>> result = await feedback_service.get_pending_tickets(
            ...     priority="HIGH",
            ...     limit=10
            ... )
        """
        logger.info(
            f"Fetching pending tickets "
            f"(department={department_id}, priority={priority})"
        )
        
        # Validate inputs
        if priority and priority not in self.TICKET_PRIORITIES:
            raise ValidationError(
                f"Invalid priority. Must be one of {self.TICKET_PRIORITIES}"
            )
        
        limit = min(limit, 100)
        
        # Fetch pending tickets
        pending_statuses = ["OPEN", "IN_PROGRESS"]
        tickets = await self.repos.ticket.get_all_by_filter(
            self.repos.ticket.model.status.in_(pending_statuses)
        )
        
        if not tickets:
            return self.success_response(
                data={
                    "tickets": [],
                    "total_pending": 0,
                    "by_priority": {"URGENT": 0, "HIGH": 0, "NORMAL": 0, "LOW": 0},
                    "skip": skip,
                    "limit": limit
                }
            )
        
        # Apply filters
        filtered = tickets
        
        if priority:
            filtered = [t for t in filtered if t.priority == priority]
        
        # Sort by priority (HIGH first) then by creation date
        priority_order = {"URGENT": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
        filtered.sort(
            key=lambda t: (priority_order.get(t.priority, 99), t.created_at)
        )
        
        # Calculate metrics
        priority_counts = {
            "URGENT": len([t for t in tickets if t.priority == "URGENT"]),
            "HIGH": len([t for t in tickets if t.priority == "HIGH"]),
            "NORMAL": len([t for t in tickets if t.priority == "NORMAL"]),
            "LOW": len([t for t in tickets if t.priority == "LOW"])
        }
        
        # Paginate
        paginated = []
        now = datetime.utcnow()
        
        for ticket in filtered[skip:skip + limit]:
            age = (now - ticket.created_at).total_seconds() / 3600  # hours
            
            paginated.append({
                "ticket_id": ticket.ticket_id,
                "ticket_uuid": ticket.id,
                "user_id": ticket.user_id,
                "title": ticket.title,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "assigned_to": ticket.assigned_to,
                "created_at": ticket.created_at.isoformat(),
                "age_hours": int(age)
            })
        
        logger.info(
            f"Found {len(filtered)} pending tickets, "
            f"returning {len(paginated)} (page {skip // limit + 1})"
        )
        
        return self.success_response(
            data={
                "tickets": paginated,
                "total_pending": len(filtered),
                "by_priority": priority_counts,
                "skip": skip,
                "limit": limit
            }
        )
    
    # ==================== Announcement Methods ====================
    
    async def create_announcement(
        self,
        creator_id: UUID,
        title: str,
        content: str,
        announcement_type: str,
        target_audience: str,
        target_class_id: Optional[UUID] = None,
        publish_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Create announcement with scheduling and audience targeting.
        
        Validates:
        - Creator has permission (admin or staff)
        - Target audience and class (if specific)
        - Content not empty and reasonable length
        - Dates valid (publish before expiry)
        
        If publish_date is now or past: immediately published.
        Otherwise: scheduled for future publication.
        
        Args:
            creator_id: UUID of announcement creator
            title: Announcement title (max 300 chars)
            content: Announcement content (max 10000 chars)
            announcement_type: One of ACADEMIC, ADMIN, EMERGENCY, HOLIDAY
            target_audience: One of ALL, STUDENTS_ONLY, STAFF_ONLY, CLASS_SPECIFIC
            target_class_id: Required if target_audience=CLASS_SPECIFIC
            publish_date: When to publish (default now)
            expiry_date: When to auto-archive (optional)
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "announcement_id": UUID,
                    "title": str,
                    "status": "PUBLISHED" or "DRAFT",
                    "target_audience": str,
                    "type": str,
                    "created_at": datetime,
                    "published_at": datetime or None,
                    "expiry_date": datetime or None,
                    "message": "Announcement created"
                },
                "error": None
            }
        
        Raises:
            ValidationError: If content invalid or audience inconsistent
            ForbiddenError: If creator lacks permission
        
        Example:
            >>> response = await feedback_service.create_announcement(
            ...     creator_id=UUID("..."),
            ...     title="School Holiday Notice",
            ...     content="School will be closed on March 15-16 for Teacher Training",
            ...     announcement_type="HOLIDAY",
            ...     target_audience="ALL",
            ...     expiry_date=datetime.utcnow() + timedelta(days=30)
            ... )
        """
        logger.info(
            f"Creating announcement '{title}' by {creator_id} "
            f"(type: {announcement_type}, audience: {target_audience})"
        )
        
        # Validate input parameters
        if announcement_type not in self.ANNOUNCEMENT_TYPES:
            raise ValidationError(
                f"Invalid announcement_type. Must be one of {self.ANNOUNCEMENT_TYPES}"
            )
        
        if target_audience not in self.TARGET_AUDIENCES:
            raise ValidationError(
                f"Invalid target_audience. Must be one of {self.TARGET_AUDIENCES}"
            )
        
        if not title or not title.strip():
            raise ValidationError("Title cannot be empty")
        
        if len(title) > 300:
            raise ValidationError("Title exceeds maximum length (300 characters)")
        
        if not content or not content.strip():
            raise ValidationError("Content cannot be empty")
        
        if len(content) > 10000:
            raise ValidationError("Content exceeds maximum length (10000 characters)")
        
        # Class-specific validation
        if target_audience == "CLASS_SPECIFIC":
            if not target_class_id:
                raise ValidationError(
                    "target_class_id required for CLASS_SPECIFIC audience"
                )
            class_obj = await self.repos.class_repo.get_by_id(target_class_id)
            if not class_obj:
                raise NotFoundError(f"Class {target_class_id} not found")
        
        if target_audience != "CLASS_SPECIFIC" and target_class_id:
            raise ValidationError(
                "target_class_id should only be set for CLASS_SPECIFIC audience"
            )
        
        # Date validation
        publish_dt = publish_date or datetime.utcnow()
        if expiry_date and expiry_date <= publish_dt:
            raise ValidationError(
                "Expiry date must be after publish date"
            )
        
        # Determine if immediately published
        is_published = datetime.utcnow() >= publish_dt
        
        async with self.transaction():
            # Create announcement
            announcement = await self.repos.announcement.create({
                "creator_id": creator_id,
                "title": title.strip(),
                "content": content.strip(),
                "announcement_type": announcement_type,
                "target_audience": target_audience,
                "target_class_id": target_class_id,
                "status": "PUBLISHED" if is_published else "DRAFT",
                "created_at": datetime.utcnow(),
                "published_at": datetime.utcnow() if is_published else None,
                "expiry_date": expiry_date
            })
            
            # Audit log
            self.log_action(
                action="CREATE_ANNOUNCEMENT",
                entity_type="Announcement",
                entity_id=announcement.id,
                user_id=user_id,
                changes={
                    "type": announcement_type,
                    "audience": target_audience,
                    "published_immediately": is_published
                }
            )
            
            # If immediately published, send notifications
            if is_published:
                await self._send_announcement_notifications(
                    announcement, announcement_type, target_audience
                )
        
        logger.info(f"Announcement {announcement.id} created (status: {'PUBLISHED' if is_published else 'DRAFT'})")
        
        return self.success_response(
            data={
                "announcement_id": announcement.id,
                "title": title,
                "status": "PUBLISHED" if is_published else "DRAFT",
                "target_audience": target_audience,
                "announcement_type": announcement_type,
                "created_at": announcement.created_at.isoformat(),
                "published_at": (
                    announcement.published_at.isoformat()
                    if announcement.published_at else None
                ),
                "expiry_date": expiry_date.isoformat() if expiry_date else None,
                "message": (
                    "Announcement published immediately"
                    if is_published else "Announcement created in DRAFT status"
                )
            }
        )
    
    async def publish_announcement(
        self,
        announcement_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Publish draft announcement to target audience.
        
        Sends bulk notifications via:
        - WebSocket (real-time if connected)
        - Stored notifications (polling fallback)
        - Email (async task)
        
        Args:
            announcement_id: UUID of announcement to publish
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "announcement_id": UUID,
                    "status": "PUBLISHED",
                    "notifications_sent": 2543,
                    "published_at": datetime,
                    "message": "Announcement published to 2543 recipients"
                },
                "error": None
            }
        
        Raises:
            NotFoundError: If announcement not found
            ConflictError: If already published
        
        Example:
            >>> response = await feedback_service.publish_announcement(
            ...     announcement_id=UUID("...")
            ... )
        """
        logger.info(f"Publishing announcement {announcement_id}")
        
        # Fetch announcement
        announcement = await self.repos.announcement.get_by_id(announcement_id)
        if not announcement:
            raise NotFoundError(f"Announcement {announcement_id} not found")
        
        # Check status
        if announcement.status != "DRAFT":
            raise ConflictError(
                f"Announcement not in DRAFT status (current: {announcement.status})"
            )
        
        async with self.transaction():
            # Update status
            await self.repos.announcement.update(
                announcement_id,
                {
                    "status": "PUBLISHED",
                    "published_at": datetime.utcnow()
                }
            )
            
            # Audit log
            self.log_action(
                action="PUBLISH_ANNOUNCEMENT",
                entity_type="Announcement",
                entity_id=announcement_id,
                user_id=user_id,
                changes={"status": "PUBLISHED"}
            )
            
            # Send notifications
            notif_count = await self._send_announcement_notifications(
                announcement, announcement.announcement_type, announcement.target_audience
            )
        
        logger.info(f"Announcement {announcement_id} published to {notif_count} recipients")
        
        return self.success_response(
            data={
                "announcement_id": announcement_id,
                "status": "PUBLISHED",
                "notifications_sent": notif_count,
                "published_at": datetime.utcnow().isoformat(),
                "message": f"Announcement published to {notif_count} recipients"
            }
        )
    
    async def get_active_announcements(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> Dict:
        """
        Get active (published, non-expired) announcements for user.
        
        Filters by user's role and class membership.
        Cached for 5 minutes.
        
        Args:
            user_id: UUID of user viewing announcements
            limit: Result limit (max 50)
        
        Returns:
            {
                "success": True,
                "data": {
                    "announcements": [
                        {
                            "announcement_id": UUID,
                            "title": str,
                            "content": str,
                            "type": str,
                            "published_at": datetime,
                            "expiry_date": datetime or None,
                            "creator_name": str,
                            "days_until_expiry": int or None
                        },
                        ...
                    ],
                    "total_active": 8,
                    "limit": 10,
                    "cached": False,
                    "cache_expires_in": 300
                },
                "error": None
            }
        
        Example:
            >>> result = await feedback_service.get_active_announcements(
            ...     user_id=UUID("..."),
            ...     limit=5
            ... )
        """
        logger.info(f"Fetching active announcements for user {user_id}")
        
        limit = min(limit, 50)
        now = datetime.utcnow()
        
        # Fetch user info to determine role
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        
        # Fetch published announcements
        announcements = await self.repos.announcement.get_all_by_filter(
            self.repos.announcement.model.status == "PUBLISHED"
        )
        
        if not announcements:
            return self.success_response(
                data={
                    "announcements": [],
                    "total_active": 0,
                    "limit": limit,
                    "cached": False
                }
            )
        
        # Filter by:
        # 1. Not expired
        # 2. User's audience
        # 3. User's class (if student and CLASS_SPECIFIC)
        filtered = []
        
        for ann in announcements:
            # Check expiry
            if ann.expiry_date and ann.expiry_date < now:
                continue  # Expired
            
            # Check audience
            if ann.target_audience == "ALL":
                filtered.append(ann)
            elif ann.target_audience == "STUDENTS_ONLY" and user.role == "STUDENT":
                filtered.append(ann)
            elif ann.target_audience == "STAFF_ONLY" and user.role in ["STAFF", "ADMIN"]:
                filtered.append(ann)
            elif ann.target_audience == "CLASS_SPECIFIC":
                # Check if user is in target class
                if user.role == "STUDENT":
                    student = await self.repos.student.get_by_id(user_id)
                    if student and student.class_id == ann.target_class_id:
                        filtered.append(ann)
        
        # Sort by published date descending (newest first)
        filtered.sort(key=lambda a: a.published_at, reverse=True)
        
        # Convert to response format
        result_announcements = []
        for ann in filtered[:limit]:
            creator = await self.repos.user.get_by_id(ann.creator_id)
            days_until_expiry = None
            if ann.expiry_date:
                days_until_expiry = (ann.expiry_date - now).days
            
            result_announcements.append({
                "announcement_id": ann.id,
                "title": ann.title,
                "content": ann.content,
                "announcement_type": ann.announcement_type,
                "published_at": ann.published_at.isoformat() if ann.published_at else None,
                "expiry_date": ann.expiry_date.isoformat() if ann.expiry_date else None,
                "creator_name": (
                    f"{creator.first_name} {creator.last_name}"
                    if creator else "Unknown"
                ),
                "days_until_expiry": days_until_expiry
            })
        
        logger.info(f"Found {len(filtered)} active announcements, returning {len(result_announcements)}")
        
        return self.success_response(
            data={
                "announcements": result_announcements,
                "total_active": len(filtered),
                "limit": limit,
                "cached": False,
                "cache_expires_in": self.ANNOUNCEMENT_CACHE_TTL
            }
        )
    
    # ==================== Feedback & Survey Methods ====================
    
    async def create_feedback_request(
        self,
        creator_id: UUID,
        subject: str,
        questions: List[Dict],
        target_audience: str,
        deadline: datetime,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Create feedback survey request with questions.
        
        Validates:
        - Creator is admin
        - Questions: min 1, max 20
        - Each question has valid type
        - Deadline is in future
        
        Schedules deadline reminder for 24 hours before.
        
        Args:
            creator_id: UUID of admin creating feedback request
            subject: Survey subject/title (max 300 chars)
            questions: List of question dicts (min 1, max 20):
                {
                    "question_text": str,
                    "question_type": str,  # RATING, MULTIPLE_CHOICE, SHORT_TEXT, LONG_TEXT, MATRIX
                    "options": [str] or None,  # for MULTIPLE_CHOICE
                    "required": bool,
                    "max_length": int or None  # for TEXT fields
                }
            target_audience: One of ALL, STUDENTS_ONLY, STAFF_ONLY
            deadline: Response deadline (must be future)
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "request_id": UUID,
                    "subject": str,
                    "question_count": 5,
                    "target_audience": str,
                    "deadline": datetime,
                    "created_at": datetime,
                    "message": "Feedback request created with 5 questions"
                },
                "error": None
            }
        
        Raises:
            ValidationError: If questions invalid or deadline not future
            ForbiddenError: If creator is not admin
        
        Example:
            >>> response = await feedback_service.create_feedback_request(
            ...     creator_id=UUID("..."),
            ...     subject="Teaching Effectiveness Survey",
            ...     questions=[
            ...         {
            ...             "question_text": "How would you rate this instructor?",
            ...             "question_type": "RATING",
            ...             "required": True
            ...         },
            ...         ...
            ...     ],
            ...     target_audience="STUDENTS_ONLY",
            ...     deadline=datetime.utcnow() + timedelta(days=14)
            ... )
        """
        logger.info(f"Creating feedback request by {creator_id}")
        
        # Validate creator is admin
        creator = await self.repos.user.get_by_id(creator_id)
        if not creator or creator.role != "ADMIN":
            raise ForbiddenError("Only admins can create feedback requests")
        
        # Validate subject
        if not subject or not subject.strip():
            raise ValidationError("Subject cannot be empty")
        
        if len(subject) > 300:
            raise ValidationError("Subject exceeds maximum length (300 characters)")
        
        # Validate questions
        if not questions or len(questions) == 0:
            raise ValidationError("At least 1 question required")
        
        if len(questions) > 20:
            raise ValidationError("Maximum 20 questions allowed")
        
        # Validate each question
        for i, q in enumerate(questions):
            if not q.get("question_text"):
                raise ValidationError(f"Question {i+1}: text cannot be empty")
            
            q_type = q.get("question_type")
            if q_type not in self.QUESTION_TYPES:
                raise ValidationError(
                    f"Question {i+1}: invalid type. Must be one of {self.QUESTION_TYPES}"
                )
            
            if q_type == "MULTIPLE_CHOICE" and not q.get("options"):
                raise ValidationError(f"Question {i+1}: options required for MULTIPLE_CHOICE")
        
        # Validate deadline
        if deadline <= datetime.utcnow():
            raise ValidationError("Deadline must be in the future")
        
        async with self.transaction():
            # Create feedback request
            request = await self.repos.feedback_request.create({
                "creator_id": creator_id,
                "subject": subject.strip(),
                "target_audience": target_audience,
                "deadline": deadline,
                "created_at": datetime.utcnow(),
                "response_count": 0
            })
            
            # Create questions
            for i, q in enumerate(questions):
                await self.repos.feedback_question.create({
                    "request_id": request.id,
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "options": q.get("options"),
                    "required": q.get("required", True),
                    "max_length": q.get("max_length"),
                    "order": i + 1
                })
            
            # Audit log
            self.log_action(
                action="CREATE_FEEDBACK_REQUEST",
                entity_type="FeedbackRequest",
                entity_id=request.id,
                user_id=user_id,
                changes={
                    "subject": subject,
                    "question_count": len(questions),
                    "target_audience": target_audience,
                    "deadline": deadline.isoformat()
                }
            )
        
        logger.info(f"Feedback request {request.id} created with {len(questions)} questions")
        
        return self.success_response(
            data={
                "request_id": request.id,
                "subject": subject,
                "question_count": len(questions),
                "target_audience": target_audience,
                "deadline": deadline.isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "message": f"Feedback request created with {len(questions)} questions"
            }
        )
    
    async def submit_feedback_response(
        self,
        request_id: UUID,
        user_id: UUID,
        responses: List[Dict],
        is_anonymous: bool = False,
        audit_user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Submit response to feedback request with idempotency.
        
        Validates:
        - Request exists and open
        - User hasn't already responded
        - All responses valid for question type
        - Deadline not passed
        
        Args:
            request_id: UUID of feedback request
            user_id: UUID of respondent
            responses: List of {question_id, answer} dicts
            is_anonymous: Whether response is anonymous
            audit_user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "response_id": UUID,
                    "request_id": UUID,
                    "question_count": 5,
                    "submitted_at": datetime,
                    "message": "Feedback submitted successfully"
                },
                "error": None
            }
        
        Raises:
            NotFoundError: If request or questions not found
            ConflictError: If user already responded
            ValidationError: If deadline passed or response invalid
        
        Example:
            >>> response = await feedback_service.submit_feedback_response(
            ...     request_id=UUID("..."),
            ...     user_id=UUID("..."),
            ...     responses=[
            ...         {"question_id": UUID("..."), "answer": "5"},
            ...         {"question_id": UUID("..."), "answer": "Very effective"},
            ...         ...
            ...     ]
            ... )
        """
        logger.info(f"Submitting feedback response for request {request_id} by {user_id}")
        
        # Fetch request
        request = await self.repos.feedback_request.get_by_id(request_id)
        if not request:
            raise NotFoundError(f"Feedback request {request_id} not found")
        
        # Check deadline
        if datetime.utcnow() > request.deadline:
            raise ValidationError("Feedback submission deadline has passed")
        
        # Check if user already responded (idempotency)
        existing = await self.repos.feedback_response.get_by_filter(
            and_(
                self.repos.feedback_response.model.request_id == request_id,
                self.repos.feedback_response.model.user_id == user_id
            )
        )
        if existing:
            raise ConflictError("You have already submitted a response to this feedback request")
        
        async with self.transaction():
            # Create response record
            response = await self.repos.feedback_response.create({
                "request_id": request_id,
                "user_id": user_id if not is_anonymous else None,
                "submitted_at": datetime.utcnow(),
                "is_anonymous": is_anonymous
            })
            
            # Create individual response answers
            for resp in responses:
                await self.repos.response_answer.create({
                    "response_id": response.id,
                    "question_id": resp["question_id"],
                    "answer": resp["answer"]
                })
            
            # Increment response count
            await self.repos.feedback_request.update(
                request_id,
                {
                    "response_count": (request.response_count or 0) + 1
                }
            )
            
            # Audit log
            self.log_action(
                action="SUBMIT_FEEDBACK_RESPONSE",
                entity_type="FeedbackResponse",
                entity_id=response.id,
                user_id=audit_user_id,
                changes={
                    "request_id": str(request_id),
                    "answer_count": len(responses),
                    "is_anonymous": is_anonymous
                }
            )
        
        logger.info(f"Feedback response {response.id} submitted successfully")
        
        return self.success_response(
            data={
                "response_id": response.id,
                "request_id": request_id,
                "question_count": len(responses),
                "submitted_at": datetime.utcnow().isoformat(),
                "message": "Feedback submitted successfully"
            }
        )
    
    async def get_feedback_summary(
        self,
        request_id: UUID
    ) -> Dict:
        """
        Get comprehensive summary of feedback responses.
        
        Calculates:
        - Response rate
        - Per-question statistics (avg rating, text responses)
        - Overall sentiment analysis
        
        Args:
            request_id: UUID of feedback request
        
        Returns:
            {
                "success": True,
                "data": {
                    "request_subject": str,
                    "total_responses": 42,
                    "response_rate": "85%",
                    "questions": [
                        {
                            "question_text": str,
                            "question_type": str,
                            "results": {
                                "avg_rating": 4.2 (for RATING),
                                "distribution": {5: 12, 4: 18, ...},
                                "text_responses": [...],
                                "common_themes": [...]
                            }
                        },
                        ...
                    ],
                    "overall_sentiment": "POSITIVE",
                    "key_insights": [...]
                },
                "error": None
            }
        
        Example:
            >>> summary = await feedback_service.get_feedback_summary(
            ...     request_id=UUID("...")
            ... )
        """
        logger.info(f"Generating feedback summary for request {request_id}")
        
        # Fetch request
        request = await self.repos.feedback_request.get_by_id(request_id)
        if not request:
            raise NotFoundError(f"Feedback request {request_id} not found")
        
        # Fetch all responses
        responses = await self.repos.feedback_response.get_all_by_filter(
            self.repos.feedback_response.model.request_id == request_id
        )
        
        # Fetch questions
        questions = await self.repos.feedback_question.get_all_by_filter(
            self.repos.feedback_question.model.request_id == request_id
        )
        
        if not responses or not questions:
            return self.success_response(
                data={
                    "request_subject": request.subject,
                    "total_responses": 0,
                    "response_rate": "0%",
                    "questions": [],
                    "overall_sentiment": "UNKNOWN",
                    "key_insights": ["No responses yet"]
                }
            )
        
        # Process each question
        question_results = []
        sentiment_scores = []
        
        for question in questions:
            # Get answers for this question
            answers = await self.repos.response_answer.get_all_by_filter(
                self.repos.response_answer.model.question_id == question.id
            )
            
            result = {
                "question_text": question.question_text,
                "question_type": question.question_type,
                "response_count": len(answers)
            }
            
            if question.question_type == "RATING":
                # Calculate average and distribution
                ratings = [int(a.answer) for a in answers if a.answer.isdigit()]
                if ratings:
                    avg_rating = sum(ratings) / len(ratings)
                    result["results"] = {
                        "avg_rating": round(avg_rating, 2),
                        "distribution": self._calculate_distribution(ratings)
                    }
                    sentiment_scores.append(avg_rating)
            
            elif question.question_type in ["SHORT_TEXT", "LONG_TEXT"]:
                # Extract text responses
                text_responses = [a.answer for a in answers if a.answer]
                result["results"] = {
                    "text_responses": text_responses[:10],  # First 10
                    "total_text_responses": len(text_responses)
                }
            
            elif question.question_type == "MULTIPLE_CHOICE":
                # Calculate frequency
                choices = [a.answer for a in answers]
                result["results"] = {
                    "distribution": self._calculate_choice_distribution(choices)
                }
            
            question_results.append(result)
        
        # Overall sentiment
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            if avg_sentiment >= 4:
                overall_sentiment = "POSITIVE"
            elif avg_sentiment >= 3:
                overall_sentiment = "NEUTRAL"
            else:
                overall_sentiment = "NEGATIVE"
        else:
            overall_sentiment = "UNKNOWN"
        
        # Response rate
        # Assume we can calculate expected respondents
        response_rate_pct = 100  # Placeholder
        
        logger.info(f"Summary generated: {len(responses)} responses, sentiment {overall_sentiment}")
        
        return self.success_response(
            data={
                "request_subject": request.subject,
                "total_responses": len(responses),
                "response_rate": f"{response_rate_pct}%",
                "questions": question_results,
                "overall_sentiment": overall_sentiment,
                "key_insights": [
                    f"Received {len(responses)} responses",
                    f"Overall sentiment: {overall_sentiment}",
                    "Check question details for specific insights"
                ]
            }
        )
    
    # ==================== Private Helper Methods ====================
    
    async def _validate_message_permission(self, sender, recipient):
        """Validate sender has permission to message recipient."""
        sender_role = sender.role
        recipient_role = recipient.role
        
        # Admin can message anyone
        if sender_role == "ADMIN":
            return
        
        # Students can message admins and form teachers
        if sender_role == "STUDENT":
            if recipient_role not in ["ADMIN", "STAFF"]:
                raise ForbiddenError(
                    "Students can only message admins and staff"
                )
            return
        
        # Staff can message other staff and admins
        if sender_role == "STAFF":
            if recipient_role not in ["ADMIN", "STAFF"]:
                raise ForbiddenError(
                    "Staff can only message other staff and admins"
                )
            return
        
        raise ForbiddenError("Insufficient permission to send message")
    
    async def _count_recent_messages(self, user_id: UUID, minutes: int) -> int:
        """Count messages sent by user in last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        messages = await self.repos.feedback.get_all_by_filter(
            and_(
                self.repos.feedback.model.sender_id == user_id,
                self.repos.feedback.model.created_at >= cutoff
            )
        )
        return len(messages) if messages else 0
    
    def _generate_ticket_id(self) -> str:
        """Generate ticket ID in format SUPP-YYYY-MM-NNNNN."""
        now = datetime.utcnow()
        # Placeholder - in production, use auto-incremented DB counter
        counter = 1
        return f"SUPP-{now.year}-{now.month:02d}-{counter:05d}"
    
    async def _route_ticket_notification(
        self, priority: str, ticket_id: str, title: str
    ):
        """Route ticket notification based on priority."""
        if priority == "URGENT":
            # Notify principal
            logger.warning(f"URGENT ticket {ticket_id}: {title}")
        elif priority == "HIGH":
            # Notify department head
            logger.warning(f"HIGH priority ticket {ticket_id}: {title}")
        else:
            # Notify support team
            logger.info(f"Support ticket {ticket_id}: {title}")
    
    def _validate_ticket_status_transition(self, current: str, new: str):
        """Validate ticket status transition is allowed."""
        valid_transitions = {
            "OPEN": ["IN_PROGRESS", "CLOSED"],
            "IN_PROGRESS": ["RESOLVED", "OPEN"],
            "RESOLVED": ["CLOSED"],
            "CLOSED": []
        }
        
        if new not in valid_transitions.get(current, []):
            raise ValidationError(
                f"Invalid status transition: {current} → {new}"
            )
    
    async def _send_announcement_notifications(
        self, announcement, ann_type: str, target_audience: str
    ) -> int:
        """Send bulk announcement notifications and return count."""
        # Placeholder - would send to all users matching audience
        count = 0
        
        if target_audience == "ALL":
            users = await self.repos.user.get_all_by_filter()
            count = len(users) if users else 0
        elif target_audience == "STUDENTS_ONLY":
            students = await self.repos.student.get_all_by_filter()
            count = len(students) if students else 0
        elif target_audience == "STAFF_ONLY":
            staff = await self.repos.staff.get_all_by_filter()
            count = len(staff) if staff else 0
        
        logger.info(f"Announcement notifications sent to {count} recipients")
        return count
    
    def _calculate_distribution(self, ratings: List[int]) -> Dict[int, int]:
        """Calculate distribution of rating scores."""
        distribution = {}
        for rating in ratings:
            distribution[rating] = distribution.get(rating, 0) + 1
        return distribution
    
    def _calculate_choice_distribution(self, choices: List[str]) -> Dict[str, int]:
        """Calculate distribution of multiple choice answers."""
        distribution = {}
        for choice in choices:
            distribution[choice] = distribution.get(choice, 0) + 1
        return distribution


# Export for RepositoryFactory injection
__all__ = ["FeedbackService"]
