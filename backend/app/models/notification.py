"""
Notification models: NotificationStudent, NotificationStaff
Event model: Event
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class NotificationStudent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    In-app notification for students.
    Tracks read/unread status.
    """
    __tablename__ = "notification_student"

    recipient_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, index=True)
    
    # Content
    verb = Column(String(255), nullable=False)  # Action: "quiz_published", "assignment_graded", etc.
    description: Text = Column(Text, nullable=True)  # Detailed message
    link = Column(String(500), nullable=True)  # Link to resource (quiz, assignment, etc.)
    
    # Status
    read: Boolean = Column(Boolean, default=False, nullable=False, index=True)
    
    # Metadata
    notification_type = Column(String(50), nullable=True)  # alert, info, success, warning
    
    # Relationships
    recipient = relationship("CustomUser", foreign_keys=[recipient_id])

    __table_args__ = (
        Index("ix_notification_student_read", "read"),
        Index("ix_notification_student_timestamp", "created_at"),
    )

    def __str__(self):
        return f"{self.verb} - {self.description[:50]}"


class NotificationStaff(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    In-app notification for staff.
    Tracks read/unread status.
    """
    __tablename__ = "notification_staff"

    recipient_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, index=True)
    
    # Content
    verb = Column(String(255), nullable=False)  # Action: "assignment_submitted", "quiz_attempt", etc.
    description: Text = Column(Text, nullable=True)  # Detailed message
    link = Column(String(500), nullable=True)  # Link to resource
    
    # Status
    read: Boolean = Column(Boolean, default=False, nullable=False, index=True)
    
    # Metadata
    notification_type = Column(String(50), nullable=True)  # alert, info, success, warning
    
    # Relationships
    recipient = relationship("CustomUser", foreign_keys=[recipient_id])

    __table_args__ = (
        Index("ix_notification_staff_read", "read"),
        Index("ix_notification_staff_timestamp", "created_at"),
    )

    def __str__(self):
        return f"{self.verb} - {self.description[:50]}"


class Event(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Academic events (exams, holidays, results, etc.).
    Visible on calendar and sends notifications.
    """
    __tablename__ = "event"

    EVENT_TYPES = [
        ("EVENT", "Event"),
        ("EXAM", "Exam"),
        ("HOLIDAY", "Holiday"),
        ("RESULT", "Result Release"),
        ("ASSIGNMENT", "Assignment"),
        ("OTHER", "Other"),
    ]

    # Content
    title = Column(String(255), nullable=False, index=True)
    description: Text = Column(Text, nullable=True)
    event_type = Column(String(20), nullable=False)  # EXAM, HOLIDAY, RESULT, EVENT, ASSIGNMENT, OTHER
    
    # Schedule
    event_datetime = Column(DateTime, nullable=False, index=True)
    end_datetime = Column(DateTime, nullable=True)  # For multi-day events
    all_day: Boolean = Column(Boolean, default=False, nullable=False)
    
    # Academic context
    session_year_id = Column(UUID(as_uuid=True), ForeignKey("session_year.id"), nullable=True, index=True)
    target_audience = Column(String(20), nullable=False)  # ALL, STUDENTS, STAFFS, SPECIFIC_CLASS
    target_class_id = Column(UUID(as_uuid=True), ForeignKey("class.id"), nullable=True)
    
    # Color/visibility
    color = Column(String(7), default="#6c757d", nullable=False)  # Hex color for calendar
    show_on_calendar: Boolean = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    session_year = relationship("SessionYear")
    target_class = relationship("Class")

    __table_args__ = (
        Index("ix_event_type_datetime", "event_type", "event_datetime"),
        Index("ix_event_audience", "target_audience"),
    )

    def __str__(self):
        return f"{self.title} ({self.event_datetime.date()})"
    
    @staticmethod
    def get_event_color(event_type: str) -> str:
        """Get default color for event type"""
        colors = {
            "EXAM": "#007bff",      # Blue
            "HOLIDAY": "#dc3545",   # Red
            "RESULT": "#ffc107",    # Yellow
            "ASSIGNMENT": "#6610f2",  # Purple
            "EVENT": "#28a745",     # Green
            "OTHER": "#6c757d",     # Gray
        }
        return colors.get(event_type, "#6c757d")
