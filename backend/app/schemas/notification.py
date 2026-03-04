"""
Notification & Reminder Schemas
"""

from pydantic import BaseModel, Field, ConfigDict, computed_field
from datetime import datetime
from uuid import UUID
from typing import Optional, Literal


class NotificationCreate(BaseModel):
    """Create notification"""
    recipient_id: UUID = Field(..., description="Recipient user UUID")
    title: str = Field(..., min_length=5, max_length=255, description="Notification title")
    message: str = Field(..., min_length=10, max_length=500, description="Notification message")
    
    notification_type: Literal[
        "ASSIGNMENT_POSTED",
        "QUIZ_PUBLISHED",
        "QUIZ_GRADED",
        "ASSIGNMENT_GRADED",
        "ATTENDANCE_MARKED",
        "LEAVE_APPROVED",
        "LEAVE_REJECTED",
        "ANNOUNCEMENT",
        "MESSAGE",
        "GRADE_ALERT",
        "SYSTEM",
        "OTHER"
    ] = Field("OTHER")
    
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = Field("NORMAL")
    
    related_model: Optional[Literal["ASSIGNMENT", "QUIZ", "LEAVE", "GRADE", "ANNOUNCEMENT"]] = None
    related_id: Optional[UUID] = None
    action_url: Optional[str] = Field(None, max_length=500, description="Deep link to relevant page")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "recipient_id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Mathematics Assignment Graded",
            "message": "Your mathematics assignment has been graded. Score: 85/100",
            "notification_type": "ASSIGNMENT_GRADED",
            "priority": "NORMAL",
            "related_model": "ASSIGNMENT",
            "related_id": "550e8400-e29b-41d4-a716-446655440001",
            "action_url": "/assignments/550e8400-e29b-41d4-a716-446655440001"
        }
    })


class NotificationResponse(BaseModel):
    """Notification record"""
    id: UUID
    recipient_id: UUID
    
    title: str
    message: str
    notification_type: str
    priority: str
    
    is_read: bool = False
    read_at: Optional[datetime] = None
    
    related_model: Optional[str]
    related_id: Optional[UUID]
    action_url: Optional[str]
    
    created_at: datetime
    
    @computed_field
    @property
    def age_in_minutes(self) -> int:
        """How many minutes ago was this created"""
        delta = datetime.now() - self.created_at
        return delta.total_seconds() // 60
    
    model_config = ConfigDict(from_attributes=True)


class NotificationPreferencesCreate(BaseModel):
    """User notification preferences"""
    user_id: UUID
    
    # Email notifications
    email_assignment_posted: bool = True
    email_quiz_published: bool = True
    email_results_graded: bool = True
    email_attendance_marked: bool = False
    email_announcements: bool = True
    
    # In-app notifications
    app_assignment_posted: bool = True
    app_quiz_published: bool = True
    app_results_graded: bool = True
    app_announcements: bool = True
    app_messages: bool = True
    
    # Quiet hours
    silent_mode_enabled: bool = False
    silent_mode_start: Optional[str] = None  # HH:MM format
    silent_mode_end: Optional[str] = None    # HH:MM format
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "email_assignment_posted": True,
            "email_quiz_published": True,
            "email_results_graded": True,
            "app_assignment_posted": True,
            "app_quiz_published": True,
            "silent_mode_enabled": True,
            "silent_mode_start": "22:00",
            "silent_mode_end": "08:00"
        }
    })


class NotificationPreferencesResponse(BaseModel):
    """Notification preferences record"""
    id: UUID
    user_id: UUID
    
    email_assignment_posted: bool
    email_quiz_published: bool
    email_results_graded: bool
    email_attendance_marked: bool
    email_announcements: bool
    
    app_assignment_posted: bool
    app_quiz_published: bool
    app_results_graded: bool
    app_announcements: bool
    app_messages: bool
    
    silent_mode_enabled: bool
    silent_mode_start: Optional[str]
    silent_mode_end: Optional[str]
    
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ReminderCreate(BaseModel):
    """Create reminder for user"""
    user_id: UUID
    title: str = Field(..., min_length=5, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    
    reminder_type: Literal["ASSIGNMENT_DUE", "QUIZ_UPCOMING", "CLASS_REMINDER", "MEETING", "CUSTOM"] = Field("CUSTOM")
    
    remind_at: datetime = Field(..., description="When to send reminder")
    related_model: Optional[str] = None
    related_id: Optional[UUID] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Mathematics Assignment Due Tomorrow",
            "reminder_type": "ASSIGNMENT_DUE",
            "remind_at": "2024-03-24T15:00:00",
            "related_model": "ASSIGNMENT",
            "related_id": "550e8400-e29b-41d4-a716-446655440001"
        }
    })


class ReminderResponse(BaseModel):
    """Reminder record"""
    id: UUID
    user_id: UUID
    
    title: str
    description: Optional[str]
    reminder_type: str
    
    remind_at: datetime
    reminded_at: Optional[datetime] = None  # When it was actually sent
    is_sent: bool = False
    
    related_model: Optional[str]
    related_id: Optional[UUID]
    
    created_at: datetime
    
    @computed_field
    @property
    def is_upcoming(self) -> bool:
        """Check if reminder hasn't been sent yet"""
        return not self.is_sent and datetime.now() < self.remind_at
    
    model_config = ConfigDict(from_attributes=True)


class UserNotificationSummaryResponse(BaseModel):
    """Summary of user's notifications"""
    user_id: UUID
    
    unread_notifications: int
    total_notifications: int
    
    recent_notifications: list[NotificationResponse] = []  # Last 10
    
    @computed_field
    @property
    def unread_percentage(self) -> float:
        """Percentage of unread notifications"""
        if self.total_notifications == 0:
            return 0.0
        return round((self.unread_notifications / self.total_notifications) * 100, 2)
    
    last_notification_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "unread_notifications": 3,
            "total_notifications": 45,
            "unread_percentage": 6.67,
            "last_notification_at": "2024-03-15T10:30:00"
        }
    })
