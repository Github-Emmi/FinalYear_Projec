"""
Staff models: Staffs (teacher profiles), AdminHOD (administrator profile)
"""

from sqlalchemy import Integer, Float, Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin


class Staff(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin):
    """
    Staff member (teacher) profile.
    Links to CustomUser and extends with staff-specific information.
    """
    __tablename__ = "staff"

    # User link (one-to-one)
    user_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, unique=True, index=True)
    
    # Professional info
    qualification = Column(String(255), nullable=True)  # e.g., "B.Sc. Mathematics"
    specialization = Column(String(255), nullable=True)
    years_of_experience = Column(Integer, default=0, nullable=False)
    
    # Contact
    address: Text = Column(Text, nullable=True)
    phone_number = Column(String(20), nullable=True)
    
    # Academic assignment
    session_year_id = Column(UUID(as_uuid=True), ForeignKey("session_year.id"), nullable=False, index=True)
    
    # Relationships
    user = relationship("CustomUser", backref="staff_profile")
    session_year = relationship("SessionYear")

    __table_args__ = (
        Index("ix_staff_user", "user_id"),
        Index("ix_staff_session_year", "session_year_id"),
    )

    def __str__(self):
        return f"Staff: {self.user.first_name} {self.user.last_name}"


class AdminHOD(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin):
    """
    Administrator/Head of Department profile.
    Links to CustomUser for admin-level users.
    """
    __tablename__ = "admin_hod"

    # User link (one-to-one)
    user_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, unique=True, index=True)
    
    # Admin info
    title = Column(String(100), nullable=True)  # e.g., "HOD", "Principal", "Vice Principal"
    office_location = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    
    # Relationships
    user = relationship("CustomUser", backref="admin_profile")

    __table_args__ = (
        Index("ix_admin_hod_user", "user_id"),
    )

    def __str__(self):
        return f"Admin: {self.user.first_name} {self.user.last_name}"
