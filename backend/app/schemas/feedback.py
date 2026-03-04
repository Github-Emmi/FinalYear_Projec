"""
Feedback & Messaging Schemas
"""

from pydantic import BaseModel, Field, ConfigDict, computed_field
from datetime import datetime
from uuid import UUID
from typing import Optional, Literal


class FeedbackCreate(BaseModel):
    """Submit feedback about class/teacher/subject"""
    title: str = Field(..., min_length=5, max_length=255, description="Feedback title")
    message: str = Field(..., min_length=20, max_length=5000, description="Feedback message")
    
    feedback_type: Literal["POSITIVE", "NEGATIVE", "SUGGESTION", "COMPLAINT", "GENERAL"] = Field(...)
    priority: Literal["LOW", "MEDIUM", "HIGH"] = Field("MEDIUM")
    
    # Optional contextual information
    subject_id: Optional[UUID] = Field(None, description="Subject UUID if about a subject")
    staff_id: Optional[UUID] = Field(None, description="Staff UUID if about a teacher")
    class_id: Optional[UUID] = Field(None, description="Class UUID if about a class")
    
    attachments: Optional[list[str]] = Field(None, description="File URLs")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Excellent Teaching Method",
            "message": "Teacher's explanation of complex topics is very clear and engaging. The interactive approach helps students understand better.",
            "feedback_type": "POSITIVE",
            "priority": "LOW",
            "subject_id": "550e8400-e29b-41d4-a716-446655440000",
            "staff_id": "550e8400-e29b-41d4-a716-446655440001"
        }
    })


class FeedbackResponse(BaseModel):
    """Feedback record"""
    id: UUID
    student_id: UUID
    
    title: str
    message: str
    feedback_type: str
    priority: str
    
    subject_id: Optional[UUID]
    staff_id: Optional[UUID]
    class_id: Optional[UUID]
    
    status: Literal["OPEN", "IN_REVIEW", "RESOLVED", "CLOSED"] = "OPEN"
    
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class FeedbackReplyCreate(BaseModel):
    """Reply to feedback"""
    feedback_id: UUID = Field(..., description="Feedback UUID")
    reply_text: str = Field(..., min_length=5, max_length=2000, description="Reply message")


class FeedbackReplyResponse(BaseModel):
    """Feedback reply/response"""
    id: UUID
    feedback_id: UUID
    
    replied_by: UUID  # Admin/HOD/Teacher ID
    reply_text: str
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class FeedbackDetailResponse(BaseModel):
    """Detailed feedback with all replies"""
    feedback: FeedbackResponse
    replies: list[FeedbackReplyResponse] = []
    
    @computed_field
    @property
    def total_replies(self) -> int:
        return len(self.replies)
    
    @computed_field
    @property
    def last_reply_at(self) -> Optional[datetime]:
        """Last reply timestamp if any"""
        if self.replies:
            return max(r.created_at for r in self.replies)
        return None


class MessageCreate(BaseModel):
    """Send message to student/teacher"""
    recipient_id: UUID = Field(..., description="Recipient user UUID")
    subject: str = Field(..., min_length=3, max_length=255, description="Message subject")
    body: str = Field(..., min_length=5, max_length=5000, description="Message body")
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = Field("NORMAL")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "recipient_id": "550e8400-e29b-41d4-a716-446655440000",
            "subject": "Assignment Submission Deadline Extension",
            "body": "Your assignment submission deadline has been extended to March 25, 2024. Please submit your work by the new deadline.",
            "priority": "NORMAL"
        }
    })


class MessageResponse(BaseModel):
    """Message record (inbox/sent)"""
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    
    subject: str
    body: str
    priority: str
    
    is_read: bool = False
    read_at: Optional[datetime] = None
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Conversation between two users"""
    other_user_id: UUID
    other_user_name: str
    
    messages: list[MessageResponse] = []
    unread_count: int = 0
    
    @computed_field
    @property
    def last_message_at(self) -> Optional[datetime]:
        """Timestamp of last message"""
        if self.messages:
            return max(m.created_at for m in self.messages)
        return None
    
    @computed_field
    @property
    def total_messages(self) -> int:
        return len(self.messages)


class AnnouncementCreate(BaseModel):
    """Create announcement (admin/HOD/teacher)"""
    title: str = Field(..., min_length=5, max_length=255, description="Announcement title")
    content: str = Field(..., min_length=20, max_length=5000, description="Announcement content")
    
    announcement_type: Literal["GENERAL", "ACADEMIC", "HOLIDAY", "EVENT", "URGENT"] = Field("GENERAL")
    
    target_audience: Literal["ALL", "STUDENTS", "STAFF", "CLASS_SPECIFIC", "DEPARTMENT_SPECIFIC"] = Field("ALL")
    target_class_ids: Optional[list[UUID]] = Field(None, description="For CLASS_SPECIFIC announcements")
    target_department_ids: Optional[list[UUID]] = Field(None, description="For DEPARTMENT_SPECIFIC")
    
    expires_at: Optional[datetime] = Field(None, description="When announcement expires (optional)")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Mid-term Exam Schedule Released",
            "content": "The mid-term examination schedule has been released. Please refer to the academic calendar for dates and times.",
            "announcement_type": "ACADEMIC",
            "target_audience": "ALL"
        }
    })


class AnnouncementResponse(BaseModel):
    """Announcement record"""
    id: UUID
    title: str
    content: str
    announcement_type: str
    target_audience: str
    
    created_by: UUID  # Staff/Admin ID
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    
    @computed_field
    @property
    def is_active(self) -> bool:
        """Check if announcement is still active"""
        if self.expires_at:
            return datetime.now() < self.expires_at
        return True
    
    model_config = ConfigDict(from_attributes=True)
