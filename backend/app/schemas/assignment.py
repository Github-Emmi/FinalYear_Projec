"""
Assignment Schemas (Creation, Submission, Grading)
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict, computed_field
from datetime import datetime
from uuid import UUID
from typing import Optional, Literal


class AssignmentCreate(BaseModel):
    """Create assignment (staff only)"""
    title: str = Field(..., min_length=5, max_length=255, description="Assignment title")
    description: str = Field(..., min_length=20, max_length=5000, description="Assignment description")
    
    subject_id: UUID = Field(..., description="Subject UUID")
    class_id: UUID = Field(..., description="Class UUID")
    department_id: UUID = Field(..., description="Department UUID")
    session_year_id: UUID = Field(..., description="Session year UUID")
    
    due_date: datetime = Field(..., description="Submission deadline")
    max_score: float = Field(100.0, ge=1, le=1000, description="Maximum score for assignment")
    
    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        """Ensure due date is in the future"""
        if v <= datetime.now():
            raise ValueError('due_date must be in the future')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Math Problem Set 3",
            "description": "Complete exercises 1-20 from chapter 5",
            "subject_id": "550e8400-e29b-41d4-a716-446655440000",
            "class_id": "550e8400-e29b-41d4-a716-446655440001",
            "department_id": "550e8400-e29b-41d4-a716-446655440002",
            "session_year_id": "550e8400-e29b-41d4-a716-446655440003",
            "due_date": "2024-03-25T23:59:00",
            "max_score": 100.0
        }
    })


class AssignmentUpdate(BaseModel):
    """Update assignment (before due date)"""
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=20, max_length=5000)
    due_date: Optional[datetime] = None
    max_score: Optional[float] = Field(None, ge=1, le=1000)


class AssignmentResponse(BaseModel):
    """Assignment details"""
    id: UUID
    title: str
    description: str
    
    subject_id: UUID
    class_id: UUID
    department_id: UUID
    session_year_id: UUID
    staff_id: UUID
    
    due_date: datetime
    max_score: float
    
    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Check if assignment is overdue"""
        return datetime.now() > self.due_date
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AssignmentSubmissionCreate(BaseModel):
    """Submit assignment"""
    assignment_id: UUID = Field(..., description="Assignment UUID")
    submission_text: Optional[str] = Field(None, max_length=10000, description="Written submission")
    file_url: Optional[str] = Field(None, max_length=500, description="File upload URL from storage")


class AssignmentSubmissionUpdate(BaseModel):
    """Update ungraded submission"""
    submission_text: Optional[str] = Field(None, max_length=10000)
    file_url: Optional[str] = Field(None, max_length=500)


class AssignmentSubmissionResponse(BaseModel):
    """Submission details"""
    id: UUID
    assignment_id: UUID
    student_id: UUID
    
    submission_text: Optional[str]
    file_url: Optional[str]
    
    submitted_at: datetime
    graded_at: Optional[datetime]
    
    @computed_field
    @property
    def is_submitted(self) -> bool:
        return self.submitted_at is not None
    
    @computed_field
    @property
    def is_late(self) -> bool:
        """Check if submitted after deadline"""
        if 'assignment' in self and hasattr(self, 'assignment'):
            return self.submitted_at > self.assignment.due_date
        return False
    
    model_config = ConfigDict(from_attributes=True)


class AssignmentGradeRequest(BaseModel):
    """Grade submission"""
    submission_id: UUID = Field(..., description="Submission UUID")
    marks: float = Field(..., ge=0, description="Marks awarded")
    feedback: Optional[str] = Field(None, max_length=2000, description="Grading feedback")
    
    @field_validator('marks')
    @classmethod
    def validate_marks(cls, v, info):
        """Marks must not exceed max_score"""
        # Note: Max score validation happens in service layer with assignment context
        if v < 0:
            raise ValueError('marks cannot be negative')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "submission_id": "550e8400-e29b-41d4-a716-446655440000",
            "marks": 85.0,
            "feedback": "Excellent work! Good problem-solving approach."
        }
    })


class AssignmentGradeResponse(BaseModel):
    """Grading response"""
    id: UUID
    submission_id: UUID
    marks: float
    feedback: Optional[str]
    graded_at: datetime
    graded_by: UUID  # Staff ID
    
    model_config = ConfigDict(from_attributes=True)


class StudentAssignmentResponse(BaseModel):
    """Student's assignment view"""
    id: UUID
    title: str
    description: str
    due_date: datetime
    max_score: float
    
    submission: Optional[AssignmentSubmissionResponse] = None
    grade: Optional[AssignmentGradeResponse] = None
    
    @computed_field
    @property
    def submission_status(self) -> str:
        """NOT_SUBMITTED, SUBMITTED, GRADED"""
        if self.grade:
            return "GRADED"
        elif self.submission:
            return "SUBMITTED"
        return "NOT_SUBMITTED"
    
    model_config = ConfigDict(from_attributes=True)
