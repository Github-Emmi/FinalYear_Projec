"""
Staff & Admin Schemas
Staff profiles and administrator roles
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional


class StaffCreate(BaseModel):
    """Create staff member"""
    user_id: UUID = Field(..., description="CustomUser UUID")
    qualification: str = Field(..., max_length=255, description="Academic qualification")
    years_of_experience: int = Field(default=0, ge=0, description="Years of teaching experience")
    address: Optional[str] = Field(None, max_length=500, description="Address")
    phone: str = Field(..., max_length=20, description="Phone number")
    session_year_id: UUID = Field(..., description="Current session year UUID")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "qualification": "Master's in Mathematics",
            "years_of_experience": 8,
            "address": "456 Oak Avenue",
            "phone": "+1234567890",
            "session_year_id": "550e8400-e29b-41d4-a716-446655440001"
        }
    })


class StaffUpdate(BaseModel):
    """Update staff"""
    qualification: Optional[str] = Field(None, max_length=255)
    years_of_experience: Optional[int] = Field(None, ge=0)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)


class StaffResponse(BaseModel):
    """Staff response"""
    id: UUID
    user_id: UUID
    qualification: str
    years_of_experience: int
    address: Optional[str]
    phone: str
    session_year_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class StaffDetailedResponse(BaseModel):
    """Detailed staff response with user data"""
    id: UUID
    user: 'UserResponse'  # Nested user
    qualification: str
    years_of_experience: int
    address: Optional[str]
    phone: str
    session_year_id: UUID
    assigned_subjects: list['SubjectResponse'] = []
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AdminHODCreate(BaseModel):
    """Create admin/HOD (Head of Department)"""
    user_id: UUID = Field(..., description="CustomUser UUID")
    title: Optional[str] = Field(None, max_length=255, description="Title (e.g., Principal, Vice Principal)")
    office_location: Optional[str] = Field(None, max_length=255, description="Office location")
    phone: Optional[str] = Field(None, max_length=20, description="Office phone")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Head of Science Department",
            "office_location": "Admin Block, Room 201",
            "phone": "+1234567890"
        }
    })


class AdminHODUpdate(BaseModel):
    """Update admin/HOD"""
    title: Optional[str] = Field(None, max_length=255)
    office_location: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)


class AdminHODResponse(BaseModel):
    """Admin/HOD response"""
    id: UUID
    user_id: UUID
    title: Optional[str]
    office_location: Optional[str]
    phone: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AdminHODDetailedResponse(BaseModel):
    """Detailed admin/HOD response with user and department data"""
    id: UUID
    user: 'UserResponse'  # Nested user
    title: Optional[str]
    office_location: Optional[str]
    phone: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Import forward references
from .auth import UserResponse
from .academic import SubjectResponse

StaffDetailedResponse.model_rebuild()
AdminHODDetailedResponse.model_rebuild()
