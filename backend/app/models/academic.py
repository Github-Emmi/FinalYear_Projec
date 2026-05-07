"""Academic structure models: Department, SessionYear, ClassRoom, Subject."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Department(BaseModel):
    __tablename__ = "departments"

    name = Column(String(255), unique=True, nullable=False, index=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    staff_profiles = relationship("StaffProfile", back_populates="department")
    classrooms = relationship("ClassRoom", back_populates="department")


class SessionYear(BaseModel):
    __tablename__ = "session_years"

    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    is_current = Column(Boolean, default=False, nullable=False, server_default="false")

    # ── Relationships ──────────────────────────────────────────────────────────
    student_profiles = relationship("StudentProfile", back_populates="session_year")


class ClassRoom(BaseModel):
    __tablename__ = "classrooms"

    name = Column(String(255), nullable=False, index=True)
    department_id = Column(
        Uuid, ForeignKey("departments.id"), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    department = relationship("Department", back_populates="classrooms")
    students = relationship("StudentProfile", back_populates="classroom")
    subjects = relationship("Subject", back_populates="classroom")
    attendance_sessions = relationship(
        "AttendanceSession", back_populates="classroom"
    )


class Subject(BaseModel):
    __tablename__ = "subjects"

    name = Column(String(255), nullable=False, index=True)
    classroom_id = Column(
        Uuid, ForeignKey("classrooms.id"), nullable=False
    )
    staff_id = Column(
        Uuid, ForeignKey("staff_profiles.id"), nullable=True
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    classroom = relationship("ClassRoom", back_populates="subjects")
    staff = relationship("StaffProfile", back_populates="subjects")
    quizzes = relationship("Quiz", back_populates="subject")
    assignments = relationship("Assignment", back_populates="subject")
    attendance_sessions = relationship(
        "AttendanceSession", back_populates="subject"
    )
    timetable_entries = relationship("TimetableEntry", back_populates="subject")


class TimetableEntry(BaseModel):
    """A single slot in a class timetable (subject × staff × day × time)."""

    __tablename__ = "timetable_entries"

    classroom_id = Column(Uuid, ForeignKey("classrooms.id"), nullable=False)
    subject_id = Column(Uuid, ForeignKey("subjects.id"), nullable=False)
    staff_id = Column(Uuid, ForeignKey("staff_profiles.id"), nullable=False)
    session_year_id = Column(Uuid, ForeignKey("session_years.id"), nullable=False)
    # 0 = Monday … 6 = Sunday
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(String(5), nullable=False)  # "08:00"
    end_time = Column(String(5), nullable=False)    # "09:00"
    period_number = Column(Integer, nullable=True)
    notes = Column(String(500), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    classroom = relationship("ClassRoom")
    subject = relationship("Subject", back_populates="timetable_entries")
    staff = relationship("StaffProfile")
    session_year = relationship("SessionYear")
