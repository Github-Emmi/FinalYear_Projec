"""
Academic structure models: SessionYear, Department, Class, Subject, TimeTable
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Time, Index, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, time
import uuid

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class SessionYear(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Academic session/year (e.g., 2023-2024, 2024-2025).
    Organizes all academic activities within a time period.
    """
    __tablename__ = "session_year"

    session_name = Column(String(255), nullable=False)  # e.g., "2023-2024"
    session_start_year = Column(DateTime, nullable=False)  # Date format: YYYY-MM-DD HH:MM:SS
    session_end_year = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    
    __table_args__ = (
        Index("ix_session_year_active", "is_active"),
    )

    def __str__(self):
        return self.session_name


class Department(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Department/Faculty (e.g., Science, Arts, Commerce).
    Groups classes and subjects by academic discipline.
    """
    __tablename__ = "department"

    department_name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)

    def __str__(self):
        return self.department_name


class Class(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Class/Grade level (e.g., Form 1, Form 4, Grade 10).
    Organizes students into cohorts.
    """
    __tablename__ = "class"

    class_name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)

    def __str__(self):
        return self.class_name


class Subject(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Subject/Course taught in a class by a staff member.
    Links to class, department, and assigned teacher.
    """
    __tablename__ = "subject"

    subject_name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), nullable=True)  # e.g., "MATH101"
    description = Column(String(500), nullable=True)
    
    # Foreign keys
    class_id = Column(UUID(as_uuid=True), ForeignKey("class.id"), nullable=False, index=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("department.id"), nullable=False, index=True)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, index=True)
    
    # Relationships
    class_obj = relationship("Class")
    department = relationship("Department")
    staff = relationship("CustomUser")

    __table_args__ = (
        UniqueConstraint("class_id", "subject_name", "department_id", name="uq_subject_class_dept"),
        Index("ix_subject_class_dept", "class_id", "department_id"),
    )

    def __str__(self):
        return self.subject_name


class TimeTable(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Weekly timetable/schedule for classes.
    Specifies when and where classes are held.
    """
    __tablename__ = "timetable"

    DAY_CHOICES = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
        ("SAT", "Saturday"),
        ("SUN", "Sunday"),
    ]

    # Subject & teacher
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subject.id"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=True)
    
    # Class & session
    class_id = Column(UUID(as_uuid=True), ForeignKey("class.id"), nullable=False, index=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("department.id"), nullable=False, index=True)
    session_year_id = Column(UUID(as_uuid=True), ForeignKey("session_year.id"), nullable=False, index=True)
    
    # Schedule
    day = Column(String(3), nullable=False)  # MON, TUE, etc.
    start_time: time = Column(Time, nullable=False)
    end_time: time = Column(Time, nullable=False)
    classroom = Column(String(100), nullable=True)
    
    # Relationships
    subject = relationship("Subject")
    teacher = relationship("CustomUser")
    class_obj = relationship("Class")
    department = relationship("Department")
    session_year = relationship("SessionYear")

    __table_args__ = (
        Index("ix_timetable_class_session", "class_id", "session_year_id"),
        Index("ix_timetable_day_time", "day", "start_time"),
    )

    def __str__(self):
        return f"{self.subject.subject_name} - {self.day} {self.start_time}-{self.end_time}"
