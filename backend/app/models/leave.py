"""
Leave models: LeaveReportStudent, LeaveReportStaff
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin


class LeaveReportStudent(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin):
    """
    Student leave request/application.
    Can be approved, rejected, or pending.
    """
    __tablename__ = "leave_report_student"

    student_id = Column(UUID(as_uuid=True), ForeignKey("student.id"), nullable=False, index=True)
    
    # Leave details
    leave_date = Column(String(50), nullable=False)  # Can be a date range or single date
    leave_message: Text = Column(Text, nullable=True)  # Reason for leave
    
    # Status
    leave_status = Column(Integer, default=0, nullable=False, index=True)  # 0=Pending, 1=Approved, -1=Rejected
    
    # When it should be approved by
    deadline_for_approval = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("Student", backref="leave_requests")

    __table_args__ = (
        Index("ix_leave_report_student_status", "leave_status"),
    )

    def __str__(self):
        return f"{self.student.user.username} - {self.leave_date}"
    
    @property
    def status_display(self) -> str:
        statuses = {0: "Pending", 1: "Approved", -1: "Rejected"}
        return statuses.get(self.leave_status, "Unknown")


class LeaveReportStaff(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin):
    """
    Staff leave request/application.
    Can be approved, rejected, or pending.
    """
    __tablename__ = "leave_report_staff"

    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False, index=True)
    
    # Leave details
    leave_date = Column(String(50), nullable=False)  # Can be a date range or single date
    leave_message: Text = Column(Text, nullable=True)  # Reason for leave
    
    # Status
    leave_status = Column(Integer, default=0, nullable=False, index=True)  # 0=Pending, 1=Approved, -1=Rejected
    
    # When it should be approved by
    deadline_for_approval = Column(DateTime, nullable=True)
    
    # Relationships
    staff = relationship("Staff", backref="leave_requests")

    __table_args__ = (
        Index("ix_leave_report_staff_status", "leave_status"),
    )

    def __str__(self):
        return f"{self.staff.user.username} - {self.leave_date}"
    
    @property
    def status_display(self) -> str:
        statuses = {0: "Pending", 1: "Approved", -1: "Rejected"}
        return statuses.get(self.leave_status, "Unknown")
