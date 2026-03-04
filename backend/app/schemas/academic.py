"""
Academic Structure Schemas
SessionYear, Department, Class, Subject, TimeTable
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict, computed_field
from datetime import datetime, time
from uuid import UUID
from typing import Optional, Literal


class SessionYearCreate(BaseModel):
    """Create academic session"""
    session_name: str = Field(..., min_length=3, max_length=50, description="Session name (e.g., 2023-2024)")
    session_start_year: int = Field(..., ge=2000, le=2200, description="Start year")
    session_end_year: int = Field(..., ge=2000, le=2200, description="End year")
    is_active: bool = Field(False, description="Set as current active session")
    
    @field_validator('session_end_year')
    @classmethod
    def validate_year_range(cls, v, info):
        """Ensure end year > start year"""
        if 'session_start_year' in info.data and v <= info.data['session_start_year']:
            raise ValueError('session_end_year must be greater than session_start_year')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "session_name": "2023-2024",
            "session_start_year": 2023,
            "session_end_year": 2024,
            "is_active": True
        }
    })


class SessionYearUpdate(BaseModel):
    """Update session"""
    session_name: Optional[str] = Field(None, min_length=3, max_length=50)
    is_active: Optional[bool] = Field(None)


class SessionYearResponse(BaseModel):
    """Session year response"""
    id: UUID
    session_name: str
    session_start_year: int
    session_end_year: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DepartmentCreate(BaseModel):
    """Create department"""
    department_name: str = Field(..., min_length=3, max_length=100, description="Department name")
    description: Optional[str] = Field(None, max_length=500, description="Department description")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "department_name": "Mathematics",
            "description": "Department of Mathematics and Sciences"
        }
    })


class DepartmentUpdate(BaseModel):
    """Update department"""
    department_name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class DepartmentResponse(BaseModel):
    """Department response"""
    id: UUID
    department_name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ClassCreate(BaseModel):
    """Create class/form"""
    class_name: str = Field(..., min_length=2, max_length=100, description="Class name (e.g., Form 1A)")
    description: Optional[str] = Field(None, max_length=500)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "class_name": "Form 1A",
            "description": "Senior Form 1, Stream A"
        }
    })


class ClassUpdate(BaseModel):
    """Update class"""
    class_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class ClassResponse(BaseModel):
    """Class response"""
    id: UUID
    class_name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SubjectCreate(BaseModel):
    """Create subject"""
    subject_name: str = Field(..., min_length=3, max_length=100, description="Subject name")
    code: str = Field(..., min_length=2, max_length=20, description="Subject code (e.g., MTH101)")
    class_id: UUID = Field(..., description="Class UUID")
    department_id: UUID = Field(..., description="Department UUID")
    staff_id: UUID = Field(..., description="Teacher UUID")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "subject_name": "Mathematics",
            "code": "MTH101",
            "class_id": "550e8400-e29b-41d4-a716-446655440000",
            "department_id": "550e8400-e29b-41d4-a716-446655440001",
            "staff_id": "550e8400-e29b-41d4-a716-446655440002"
        }
    })


class SubjectUpdate(BaseModel):
    """Update subject"""
    subject_name: Optional[str] = Field(None, min_length=3, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    staff_id: Optional[UUID] = None


class SubjectResponse(BaseModel):
    """Subject response"""
    id: UUID
    subject_name: str
    code: str
    class_id: UUID
    department_id: UUID
    staff_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TimeTableCreate(BaseModel):
    """Create timetable entry"""
    subject_id: UUID = Field(..., description="Subject UUID")
    teacher_id: UUID = Field(..., description="Teacher/Staff UUID")
    class_id: UUID = Field(..., description="Class UUID")
    department_id: UUID = Field(..., description="Department UUID")
    session_year_id: UUID = Field(..., description="Session year UUID")
    
    day: str = Field(..., description="Day of week (MON-SAT)")
    start_time: time = Field(..., description="Start time (HH:MM)")
    end_time: time = Field(..., description="End time (HH:MM)")
    classroom: Optional[str] = Field(None, max_length=100, description="Room number/name")
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        """Ensure end time > start time"""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
    
    @field_validator('day')
    @classmethod
    def validate_day(cls, v):
        """Validate day of week"""
        valid_days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        if v.upper() not in valid_days:
            raise ValueError(f'Day must be one of {valid_days}')
        return v.upper()
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "subject_id": "550e8400-e29b-41d4-a716-446655440000",
            "teacher_id": "550e8400-e29b-41d4-a716-446655440001",
            "class_id": "550e8400-e29b-41d4-a716-446655440002",
            "department_id": "550e8400-e29b-41d4-a716-446655440003",
            "session_year_id": "550e8400-e29b-41d4-a716-446655440004",
            "day": "MON",
            "start_time": "09:00",
            "end_time": "10:00",
            "classroom": "A101"
        }
    })


class TimeTableUpdate(BaseModel):
    """Update timetable"""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    classroom: Optional[str] = Field(None, max_length=100)
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        """Ensure end time > start time"""
        if 'start_time' in info.data and info.data['start_time'] and v and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class TimeTableResponse(BaseModel):
    """Timetable response"""
    id: UUID
    subject_id: UUID
    teacher_id: UUID
    class_id: UUID
    department_id: UUID
    session_year_id: UUID
    
    day: str
    start_time: time
    end_time: time
    classroom: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
