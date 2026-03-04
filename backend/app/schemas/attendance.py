"""
Attendance Schemas (Record, Reports, History)
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict, computed_field
from datetime import datetime, date
from uuid import UUID
from typing import Optional, Literal
from decimal import Decimal


class AttendanceRecordCreate(BaseModel):
    """Record single student attendance"""
    student_id: UUID = Field(..., description="Student UUID")
    status: Literal["PRESENT", "ABSENT", "LATE", "EXCUSED"] = Field(..., description="Attendance status")
    remarks: Optional[str] = Field(None, max_length=500, description="Remarks/notes")


class AttendanceCreate(BaseModel):
    """Record class attendance (bulk)"""
    class_id: UUID = Field(..., description="Class UUID")
    subject_id: UUID = Field(..., description="Subject UUID")
    attendance_date: date = Field(..., description="Date of attendance")
    session_year_id: UUID = Field(..., description="Session year UUID")
    
    records: list[AttendanceRecordCreate] = Field(..., description="Student attendance records")
    
    @field_validator('attendance_date')
    @classmethod
    def validate_date(cls, v):
        """Attendance date cannot be in future"""
        if v > date.today():
            raise ValueError('attendance_date cannot be in the future')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "class_id": "550e8400-e29b-41d4-a716-446655440000",
            "subject_id": "550e8400-e29b-41d4-a716-446655440001",
            "attendance_date": "2024-03-15",
            "session_year_id": "550e8400-e29b-41d4-a716-446655440002",
            "records": [
                {
                    "student_id": "550e8400-e29b-41d4-a716-446655440003",
                    "status": "PRESENT",
                    "remarks": ""
                }
            ]
        }
    })


class AttendanceResponse(BaseModel):
    """Single attendance record"""
    id: UUID
    student_id: UUID
    class_id: UUID
    subject_id: UUID
    session_year_id: UUID
    
    attendance_date: date
    status: str
    remarks: Optional[str]
    
    recorded_by: UUID  # Staff ID
    recorded_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AttendanceReportResponse(BaseModel):
    """Attendance statistics for student"""
    student_id: UUID
    class_id: UUID
    session_year_id: UUID
    
    total_classes: int = Field(..., description="Total classes held")
    days_present: int
    days_absent: int
    days_late: int
    days_excused: int
    
    @computed_field
    @property
    def attendance_percentage(self) -> float:
        """Calculate attendance percentage"""
        if self.total_classes == 0:
            return 0.0
        # Count PRESENT as full, LATE as 0.75
        days_attended = self.days_present + (self.days_late * 0.75)
        return round((days_attended / self.total_classes) * 100, 2)
    
    @computed_field
    @property
    def attendance_status(self) -> str:
        """EXCELLENT (>=95%), GOOD (85-94%), SATISFACTORY (75-84%), POOR (<75%)"""
        pct = self.attendance_percentage
        if pct >= 95:
            return "EXCELLENT"
        elif pct >= 85:
            return "GOOD"
        elif pct >= 75:
            return "SATISFACTORY"
        return "POOR"
    
    report_generated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "student_id": "550e8400-e29b-41d4-a716-446655440000",
            "class_id": "550e8400-e29b-41d4-a716-446655440001",
            "session_year_id": "550e8400-e29b-41d4-a716-446655440002",
            "total_classes": 50,
            "days_present": 48,
            "days_absent": 1,
            "days_late": 1,
            "days_excused": 0,
            "attendance_percentage": 96.5,
            "attendance_status": "EXCELLENT",
            "report_generated_at": "2024-03-15T10:30:00"
        }
    })


class StudentAttendanceHistoryResponse(BaseModel):
    """Student's attendance history for specific period"""
    student_id: UUID
    class_id: UUID
    
    attendance_records: list[AttendanceResponse]
    
    @computed_field
    @property
    def total_records(self) -> int:
        return len(self.attendance_records)
    
    @computed_field
    @property
    def overall_percentage(self) -> float:
        """Calculate percentage from records"""
        if not self.attendance_records:
            return 0.0
        
        present_count = sum(1 for r in self.attendance_records if r.status == "PRESENT")
        late_count = sum(1 for r in self.attendance_records if r.status == "LATE")
        
        days_attended = present_count + (late_count * 0.75)
        return round((days_attended / self.total_records) * 100, 2) if self.total_records > 0 else 0.0
    
    period_start: date
    period_end: date
    generated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True)


class ClassAttendanceSummaryResponse(BaseModel):
    """Summary of class attendance"""
    class_id: UUID
    session_year_id: UUID
    
    total_students: int
    date: date
    
    present_count: int
    absent_count: int
    late_count: int
    excused_count: int
    
    @computed_field
    @property
    def present_percentage(self) -> float:
        """Percentage of students present"""
        if self.total_students == 0:
            return 0.0
        return round((self.present_count / self.total_students) * 100, 2)
    
    recorded_at: datetime
    
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "class_id": "550e8400-e29b-41d4-a716-446655440000",
            "session_year_id": "550e8400-e29b-41d4-a716-446655440001",
            "total_students": 30,
            "date": "2024-03-15",
            "present_count": 28,
            "absent_count": 1,
            "late_count": 1,
            "excused_count": 0,
            "present_percentage": 93.33,
            "recorded_at": "2024-03-15T10:30:00"
        }
    })
