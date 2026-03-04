"""
Common Filter and Search Parameters
"""

from pydantic import BaseModel, Field
from datetime import date
from uuid import UUID
from typing import Optional, Literal
from enum import Enum


class SortOrder(str, Enum):
    """Sort order enum"""
    ASC = "asc"
    DESC = "desc"


class QuizFilterParams(BaseModel):
    """Filter parameters for quiz queries"""
    subject_id: Optional[UUID] = None
    class_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    staff_id: Optional[UUID] = None
    
    status: Optional[Literal["DRAFT", "PUBLISHED", "ARCHIVED"]] = None
    
    search: Optional[str] = Field(None, max_length=255, description="Search by title or instructions")
    
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[Literal["created_at", "start_time", "title"]] = "created_at"
    sort_order: SortOrder = SortOrder.DESC


class AssignmentFilterParams(BaseModel):
    """Filter parameters for assignment queries"""
    subject_id: Optional[UUID] = None
    class_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    staff_id: Optional[UUID] = None
    
    search: Optional[str] = Field(None, max_length=255, description="Search by title or description")
    
    status: Optional[Literal["ACTIVE", "CLOSED", "ARCHIVED"]] = None
    
    due_after: Optional[date] = None
    due_before: Optional[date] = None
    
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[Literal["due_date", "created_at", "title"]] = "due_date"
    sort_order: SortOrder = SortOrder.ASC


class StudentFilterParams(BaseModel):
    """Filter parameters for student queries"""
    class_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    session_year_id: Optional[UUID] = None
    
    search: Optional[str] = Field(None, max_length=255, description="Search by name, email, or enrollment number")
    
    status: Optional[Literal["ACTIVE", "INACTIVE", "COMPLETED"]] = "ACTIVE"
    
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=200)
    sort_by: Optional[Literal["name", "email", "enrollment_number", "created_at"]] = "name"
    sort_order: SortOrder = SortOrder.ASC


class StaffFilterParams(BaseModel):
    """Filter parameters for staff queries"""
    department_id: Optional[UUID] = None
    session_year_id: Optional[UUID] = None
    
    search: Optional[str] = Field(None, max_length=255, description="Search by name or email")
    
    role: Optional[Literal["TEACHER", "HOD", "ADMIN"]] = None
    
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=200)
    sort_by: Optional[Literal["name", "email", "qualification", "created_at"]] = "name"
    sort_order: SortOrder = SortOrder.ASC


class AttendanceFilterParams(BaseModel):
    """Filter parameters for attendance queries"""
    class_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    student_id: Optional[UUID] = None
    
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    
    status: Optional[Literal["PRESENT", "ABSENT", "LATE", "EXCUSED"]] = None
    
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=200)
    sort_by: Optional[Literal["attendance_date", "student_name"]] = "attendance_date"
    sort_order: SortOrder = SortOrder.DESC


class LeaveFilterParams(BaseModel):
    """Filter parameters for leave queries"""
    leave_type: Optional[Literal["STUDENT", "STAFF"]] = None
    
    status: Optional[Literal["PENDING", "APPROVED", "REJECTED", "WITHDRAWN"]] = None
    
    user_id: Optional[UUID] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    
    search: Optional[str] = Field(None, max_length=255, description="Search by user name or reason")
    
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=25, ge=1, le=100)
    sort_by: Optional[Literal["start_date", "requested_at", "status"]] = "start_date"
    sort_order: SortOrder = SortOrder.DESC


class FeedbackFilterParams(BaseModel):
    """Filter parameters for feedback queries"""
    student_id: Optional[UUID] = None
    staff_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    class_id: Optional[UUID] = None
    
    feedback_type: Optional[Literal["POSITIVE", "NEGATIVE", "SUGGESTION", "COMPLAINT", "GENERAL"]] = None
    status: Optional[Literal["OPEN", "IN_REVIEW", "RESOLVED", "CLOSED"]] = None
    priority: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = None
    
    search: Optional[str] = Field(None, max_length=255, description="Search by title or message")
    
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=25, ge=1, le=100)
    sort_by: Optional[Literal["created_at", "priority", "status"]] = "created_at"
    sort_order: SortOrder = SortOrder.DESC


class NotificationFilterParams(BaseModel):
    """Filter parameters for notification queries"""
    user_id: UUID = Field(..., description="User to get notifications for")
    
    notification_type: Optional[str] = None
    priority: Optional[Literal["LOW", "NORMAL", "HIGH", "URGENT"]] = None
    
    is_read: Optional[bool] = None
    
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=200)
    sort_by: Optional[Literal["created_at", "priority"]] = "created_at"
    sort_order: SortOrder = SortOrder.DESC


class MessageFilterParams(BaseModel):
    """Filter parameters for message queries"""
    user_id: UUID = Field(..., description="User's messages to fetch")
    
    conversation_with: Optional[UUID] = Field(None, description="Filter by specific user")
    
    is_read: Optional[bool] = None
    
    folder: Optional[Literal["INBOX", "SENT", "ARCHIVED"]] = "INBOX"
    
    search: Optional[str] = Field(None, max_length=255, description="Search by subject or body")
    
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=200)
    sort_by: Optional[Literal["created_at", "sender"]] = "created_at"
    sort_order: SortOrder = SortOrder.DESC


class DateRangeFilter(BaseModel):
    """Reusable date range filter"""
    date_from: Optional[date] = Field(None, description="Start date (inclusive)")
    date_to: Optional[date] = Field(None, description="End date (inclusive)")


class SearchFilter(BaseModel):
    """Reusable search filter"""
    query: str = Field(..., min_length=1, max_length=255, description="Search query")
    search_fields: Optional[list[str]] = None  # Which fields to search in


class PaginationFilter(BaseModel):
    """Reusable pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")


class SortingFilter(BaseModel):
    """Reusable sorting parameters"""
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort direction")
