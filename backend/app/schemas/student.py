"""
Student Schemas
Student profiles, dashboards, enrollment
"""

from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict, computed_field
from datetime import datetime, date
from uuid import UUID
from typing import Optional, Literal


class StudentCreate(BaseModel):
    """Create student (admin only)"""
    user_id: UUID = Field(..., description="CustomUser UUID")
    class_id: UUID = Field(..., description="Class UUID")
    department_id: UUID = Field(..., description="Department UUID")
    session_year_id: UUID = Field(..., description="Session year UUID")
    
    date_of_birth: date = Field(..., description="Date of birth")
    gender: Literal["M", "F", "OTHER"] = Field(..., description="Gender")
    address: Optional[str] = Field(None, max_length=500, description="Residential address")
    phone: str = Field(..., max_length=20, description="Phone number")
    
    parent_name: str = Field(..., max_length=255, description="Parent/Guardian name")
    parent_phone: str = Field(..., max_length=20, description="Parent phone")
    parent_email: Optional[EmailStr] = Field(None, description="Parent email")
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_dob(cls, v):
        """Ensure reasonable age (5-70 years old)"""
        from datetime import datetime
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 5 or age > 70:
            raise ValueError('Student age must be between 5 and 70 years')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "class_id": "550e8400-e29b-41d4-a716-446655440001",
            "department_id": "550e8400-e29b-41d4-a716-446655440002",
            "session_year_id": "550e8400-e29b-41d4-a716-446655440003",
            "date_of_birth": "2008-05-15",
            "gender": "M",
            "address": "123 Main Street",
            "phone": "+1234567890",
            "parent_name": "Jane Doe",
            "parent_phone": "+1234567891",
            "parent_email": "jane@example.com"
        }
    })


class StudentUpdate(BaseModel):
    """Update student"""
    class_id: Optional[UUID] = None
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)
    parent_name: Optional[str] = Field(None, max_length=255)
    parent_phone: Optional[str] = Field(None, max_length=20)


class StudentResponse(BaseModel):
    """Student response"""
    id: UUID
    user_id: UUID
    class_id: Optional[UUID]
    department_id: Optional[UUID]
    session_year_id: Optional[UUID]
    
    date_of_birth: Optional[date]
    gender: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    
    parent_name: Optional[str]
    parent_phone: Optional[str]
    parent_email: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class StudentDetailedResponse(BaseModel):
    """Detailed student response with related data"""
    id: UUID
    user: 'UserResponse'  # Nested user profile
    class_id: Optional[UUID]
    department_id: Optional[UUID]
    session_year_id: Optional[UUID]
    
    date_of_birth: Optional[date]
    gender: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    
    parent_name: Optional[str]
    parent_phone: Optional[str]
    parent_email: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class StudentDashboardResponse(BaseModel):
    """Student dashboard analytics"""
    student_id: UUID
    total_quizzes: int = Field(..., description="Total quizzes assigned")
    completed_quizzes: int = Field(..., description="Quizzes submitted")
    pending_quizzes: int = Field(..., description="Pending quizzes")
    average_quiz_score: float = Field(default=0.0, description="Average quiz percentage")
    
    total_assignments: int = Field(..., description="Total assignments assigned")
    submitted_assignments: int = Field(..., description="Assignments submitted")
    pending_assignments: int = Field(..., description="Overdue assignments")
    average_assignment_score: float = Field(default=0.0, description="Average assignment percentage")
    
    attendance_percentage: float = Field(..., ge=0, le=100, description="Attendance %")
    total_leaves_approved: int = Field(..., description="Approved leaves")
    total_leaves_pending: int = Field(..., description="Pending leave requests")
    
    unread_notifications: int = Field(..., description="Unread notifications count")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "student_id": "550e8400-e29b-41d4-a716-446655440000",
            "total_quizzes": 10,
            "completed_quizzes": 8,
            "pending_quizzes": 2,
            "average_quiz_score": 78.5,
            "total_assignments": 12,
            "submitted_assignments": 10,
            "pending_assignments": 2,
            "average_assignment_score": 82.0,
            "attendance_percentage": 92.5,
            "total_leaves_approved": 2,
            "total_leaves_pending": 1,
            "unread_notifications": 3
        }
    })


class StudentEnrollmentCreate(BaseModel):
    """Enroll student in class"""
    student_id: UUID = Field(..., description="Student UUID")
    class_id: UUID = Field(..., description="Class UUID")
    enrollment_date: date = Field(default_factory=date.today)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "student_id": "550e8400-e29b-41d4-a716-446655440000",
            "class_id": "550e8400-e29b-41d4-a716-446655440001",
            "enrollment_date": "2024-01-15"
        }
    })


class StudentEnrollmentResponse(BaseModel):
    """Enrollment response"""
    id: UUID
    student_id: UUID
    class_id: UUID
    enrollment_date: date
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Import UserResponse for forward reference
from .auth import UserResponse

StudentDetailedResponse.model_rebuild()
