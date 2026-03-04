"""
Base Pydantic schemas for requests/responses.
Provides common patterns, pagination, error handling.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Generic, TypeVar, List, Any
from datetime import datetime
from uuid import UUID


class BaseSchema(BaseModel):
    """
    Base schema with common configuration.
    All schemas should inherit from this.
    """
    model_config = ConfigDict(
        from_attributes=True,  # Allow creation from ORM objects
        populate_by_name=True,  # Allow both field name and alias
        use_enum_values=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields"""
    created_at: datetime
    updated_at: datetime


class UUIDSchema(BaseSchema):
    """Schema with UUID id"""
    id: UUID = Field(..., description="Unique identifier")


class BaseResponseSchema(UUIDSchema, TimestampSchema):
    """Standard response schema with id and timestamps"""
    pass


# Pagination
T = TypeVar("T")


class PaginationParams(BaseSchema):
    """Query parameters for paginated requests"""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and limit"""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseSchema, Generic[T]):
    """Paginated API response"""
    data: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total items count")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total pages")
    
    def __init__(self, data: List[T], total: int, page: int, limit: int):
        pages = (total + limit - 1) // limit  # Ceiling division
        super().__init__(data=data, total=total, page=page, limit=limit, pages=pages)


# Error responses
class ErrorDetail(BaseSchema):
    """Error detail with code and message"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(default=None, description="Additional details")


class ErrorResponse(BaseSchema):
    """Standard error response"""
    success: bool = Field(default=False)
    error: ErrorDetail
    request_id: Optional[str] = Field(default=None, description="Request tracking ID")


class SuccessResponse(BaseSchema, Generic[T]):
    """Standard success response"""
    success: bool = Field(default=True)
    data: T
    message: Optional[str] = Field(default=None, description="Success message")


# Standard status
class StatusResponse(BaseSchema):
    """Simple status response"""
    success: bool
    message: str


# ============= DOMAIN SCHEMA IMPORTS =============

# Authentication
from app.schemas.auth import (
    UserLogin,
    UserRegister,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest
)

# Academic Structure
from app.schemas.academic import (
    SessionYearCreate,
    SessionYearUpdate,
    SessionYearResponse,
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    ClassCreate,
    ClassUpdate,
    ClassResponse,
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    TimeTableCreate,
    TimeTableUpdate,
    TimeTableResponse
)

# Student Management
from app.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentDetailedResponse,
    StudentDashboardResponse,
    StudentEnrollmentCreate,
    StudentEnrollmentResponse
)

# Staff & Administration
from app.schemas.staff import (
    StaffCreate,
    StaffUpdate,
    StaffResponse,
    StaffDetailedResponse,
    AdminHODCreate,
    AdminHODUpdate,
    AdminHODResponse,
    AdminHODDetailedResponse
)

# Assessment & Quiz
from app.schemas.assessment import (
    QuizCreate,
    QuizUpdate,
    QuizPublishRequest,
    QuizResponse,
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    StudentAnswerCreate,
    StudentQuizSubmissionCreate,
    StudentQuizSubmissionResponse,
    QuizAttemptStartResponse,
    QuizAttemptResponse,
    QuizResultsResponse
)

# Assignment Management
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentResponse,
    AssignmentSubmissionCreate,
    AssignmentSubmissionUpdate,
    AssignmentSubmissionResponse,
    AssignmentGradeRequest,
    AssignmentGradeResponse,
    StudentAssignmentResponse
)

# Attendance Tracking
from app.schemas.attendance import (
    AttendanceRecordCreate,
    AttendanceCreate,
    AttendanceResponse,
    AttendanceReportResponse,
    StudentAttendanceHistoryResponse,
    ClassAttendanceSummaryResponse
)

# Leave Management
from app.schemas.leave import (
    StudentLeaveCreate,
    StudentLeaveResponse,
    StaffLeaveCreate,
    StaffLeaveResponse,
    LeaveApprovalRequest,
    LeaveStatisticsResponse
)

# Feedback & Messaging
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackReplyCreate,
    FeedbackReplyResponse,
    FeedbackDetailResponse,
    MessageCreate,
    MessageResponse,
    ConversationResponse,
    AnnouncementCreate,
    AnnouncementResponse
)

# Notifications & Reminders
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationPreferencesCreate,
    NotificationPreferencesResponse,
    ReminderCreate,
    ReminderResponse,
    UserNotificationSummaryResponse
)
