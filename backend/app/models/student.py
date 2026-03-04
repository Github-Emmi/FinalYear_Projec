"""
Student models: Student profile with comprehensive information
"""

from sqlalchemy import Column, String, Integer, ForeignKey, Text, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin


class Student(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin):
    """
    Student profile with comprehensive personal and health information.
    Links to CustomUser and extends with student-specific data.
    """
    __tablename__ = "student"

    # User link (one-to-one)
    user_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, unique=True, index=True)
    
    # ==================== ACADEMIC ====================
    class_id = Column(UUID(as_uuid=True), ForeignKey("class.id"), nullable=False, index=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("department.id"), nullable=False, index=True)
    session_year_id = Column(UUID(as_uuid=True), ForeignKey("session_year.id"), nullable=False, index=True)
    
    # ==================== PERSONAL INFORMATION ====================
    # Demographics
    gender = Column(String(50), nullable=True)  # Male, Female, Other
    date_of_birth = Column(String(50), nullable=True)
    age = Column(String(10), nullable=True)
    
    # Physical
    height = Column(String(10), nullable=True)  # cm
    weight = Column(String(10), nullable=True)  # kg
    eye_color = Column(String(50), nullable=True)
    
    # ==================== ADDRESS INFORMATION ====================
    place_of_birth = Column(String(255), nullable=True)
    home_town = Column(String(255), nullable=True)
    state_of_origin = Column(String(100), nullable=True)
    lga = Column(String(100), nullable=True)  # Local Government Area
    nationality = Column(String(100), nullable=True)
    residential_address: Text = Column(Text, nullable=True)
    bus_stop = Column(String(255), nullable=True)
    religion = Column(String(100), nullable=True)
    
    # ==================== FATHER'S INFORMATION ====================
    father_name = Column(String(255), nullable=True)
    father_address: Text = Column(Text, nullable=True)
    father_occupation = Column(String(255), nullable=True)
    father_position = Column(String(255), nullable=True)
    father_phone_num_1 = Column(String(20), nullable=True)
    father_phone_num_2 = Column(String(20), nullable=True)
    father_email = Column(String(254), nullable=True)
    
    # ==================== MOTHER'S INFORMATION ====================
    mother_name = Column(String(255), nullable=True)
    mother_address: Text = Column(Text, nullable=True)
    mother_occupation = Column(String(255), nullable=True)
    mother_position = Column(String(255), nullable=True)
    mother_phone_num_1 = Column(String(20), nullable=True)
    mother_phone_num_2 = Column(String(20), nullable=True)
    mother_email = Column(String(254), nullable=True)
    
    # ==================== PREVIOUS EDUCATION ====================
    last_class = Column(String(100), nullable=True)
    school_attended_last = Column(String(255), nullable=True)
    
    # ==================== HEALTH INFORMATION ====================
    # Allergies & Conditions
    asthmatic = Column(String(3), default="", nullable=False)  # Yes/No/Unknown
    hypertension = Column(String(3), default="", nullable=False)
    disabilities = Column(String(3), default="", nullable=False)
    epilepsy = Column(String(3), default="", nullable=False)
    blind = Column(String(3), default="", nullable=False)
    mental_illness = Column(String(3), default="", nullable=False)
    tuberculosis = Column(String(3), default="", nullable=False)
    spectacle_use = Column(String(3), default="", nullable=False)
    sickle_cell = Column(String(3), default="", nullable=False)
    
    # Health details
    health_problems: Text = Column(Text, nullable=True)
    medication: Text = Column(Text, nullable=True)
    drug_allergy: Text = Column(Text, nullable=True)
    
    # ==================== MEDIA ====================
    profile_pic = Column(String(500), nullable=True)  # Cloudinary URL
    
    # ==================== RELATIONSHIPS ====================
    user = relationship("CustomUser", backref="student_profile")
    class_obj = relationship("Class")
    department = relationship("Department")
    session_year = relationship("SessionYear")

    __table_args__ = (
        Index("ix_student_user", "user_id"),
        Index("ix_student_class_session", "class_id", "session_year_id"),
        Index("ix_student_department", "department_id"),
        Index("ix_student_email", "residential_address"),
    )

    def __str__(self):
        return f"Student: {self.user.first_name} {self.user.last_name}"
