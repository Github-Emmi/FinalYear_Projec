"""
Leave Management Schemas (Student & Staff Leave)
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict, computed_field
from datetime import datetime, date
from uuid import UUID
from typing import Optional, Literal


class StudentLeaveCreate(BaseModel):
    """Student requests leave"""
    reason: str = Field(..., min_length=10, max_length=1000, description="Reason for leave")
    start_date: date = Field(..., description="Leave start date")
    end_date: date = Field(..., description="Leave end date")
    leave_type: Literal["SICK", "CASUAL", "FAMILY_EMERGENCY", "OTHER"] = Field(...)
    supporting_document: Optional[str] = Field(None, max_length=500, description="Document URL for medical/emergency")
    
    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v):
        """Start date must be today or future"""
        if v < date.today():
            raise ValueError('start_date cannot be in the past')
        return v
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        """End date must be after or equal to start date"""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be after or equal to start_date')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "reason": "Medical consultation for dental treatment",
            "start_date": "2024-03-18",
            "end_date": "2024-03-18",
            "leave_type": "SICK",
            "supporting_document": "https://storage.example.com/medical_certificate.pdf"
        }
    })


class StudentLeaveResponse(BaseModel):
    """Student leave request"""
    id: UUID
    student_id: UUID
    
    reason: str
    start_date: date
    end_date: date
    leave_type: str
    
    @computed_field
    @property
    def duration_days(self) -> int:
        """Number of days in leave"""
        return (self.end_date - self.start_date).days + 1
    
    status: Literal["PENDING", "APPROVED", "REJECTED", "WITHDRAWN"] = "PENDING"
    approved_by: Optional[UUID] = None  # Admin/HOD ID
    approval_date: Optional[datetime] = None
    approval_remarks: Optional[str] = None
    
    requested_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class StaffLeaveCreate(BaseModel):
    """Staff member requests leave"""
    reason: str = Field(..., min_length=10, max_length=1000, description="Reason for leave")
    start_date: date = Field(..., description="Leave start date")
    end_date: date = Field(..., description="Leave end date")
    leave_type: Literal["SICK", "CASUAL", "EARNED", "STUDY", "OFFICIAL", "OTHER"] = Field(...)
    cover_staff_id: Optional[UUID] = Field(None, description="Cover staff member UUID if needed")
    
    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v):
        """Start date must be in the future (few days notice)"""
        min_notice = 3  # 3 days notice required
        from datetime import timedelta
        if v < date.today() + timedelta(days=min_notice):
            raise ValueError(f'start_date requires at least {min_notice} days notice')
        return v
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        """End date must be after start date"""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be after or equal to start_date')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "reason": "Annual leave for family vacation",
            "start_date": "2024-05-01",
            "end_date": "2024-05-14",
            "leave_type": "CASUAL",
            "cover_staff_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    })


class StaffLeaveResponse(BaseModel):
    """Staff leave request"""
    id: UUID
    staff_id: UUID
    
    reason: str
    start_date: date
    end_date: date
    leave_type: str
    cover_staff_id: Optional[UUID]
    
    @computed_field
    @property
    def duration_days(self) -> int:
        """Number of days in leave"""
        return (self.end_date - self.start_date).days + 1
    
    status: Literal["PENDING", "APPROVED", "REJECTED", "WITHDRAWN"] = "PENDING"
    approved_by: Optional[UUID] = None  # Principal/HOD ID
    approval_date: Optional[datetime] = None
    approval_remarks: Optional[str] = None
    
    requested_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LeaveApprovalRequest(BaseModel):
    """Approve or reject leave request"""
    leave_id: UUID = Field(..., description="Leave request UUID")
    leave_type: Literal["STUDENT", "STAFF"] = Field(..., description="Leave type")
    action: Literal["APPROVE", "REJECT"] = Field(..., description="Approval action")
    remarks: Optional[str] = Field(None, max_length=500, description="Approval remarks/feedback")
    
    @field_validator('remarks')
    @classmethod
    def validate_remarks(cls, v, info):
        """Remarks required for rejection"""
        if info.data.get('action') == "REJECT" and not v:
            raise ValueError('remarks are required when rejecting a leave request')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "leave_id": "550e8400-e29b-41d4-a716-446655440000",
            "leave_type": "STUDENT",
            "action": "APPROVE",
            "remarks": "Approved for medical reasons"
        }
    })


class LeaveStatisticsResponse(BaseModel):
    """Leave statistics for user"""
    user_id: UUID
    user_type: Literal["STUDENT", "STAFF"]
    
    total_pending: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    
    current_leave: Optional[dict] = None  # Current active leave if any
    upcoming_leaves: list[dict] = []  # Next 5 upcoming approved leaves
    
    leaves_used_current_year: int = 0
    leaves_remaining: Optional[int] = None  # For staff only
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_type": "STAFF",
            "total_pending": 1,
            "total_approved": 5,
            "total_rejected": 0,
            "leaves_used_current_year": 15,
            "leaves_remaining": 15
        }
    })
