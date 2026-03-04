"""
Feedback models: FeedbackStudent, FeedbackStaff
"""

from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class FeedbackStudent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Student feedback/message to admin.
    Admin can reply with feedback_reply.
    """
    __tablename__ = "feedback_student"

    student_id = Column(UUID(as_uuid=True), ForeignKey("student.id"), nullable=False, index=True)
    
    # Messages
    feedback: Text = Column(Text, nullable=False)  # Student's message
    feedback_reply: Text = Column(Text, nullable=True)  # Admin's reply
    
    # Relationships
    student = relationship("Student", backref="feedbacks")

    __table_args__ = (
        Index("ix_feedback_student_student", "student_id"),
    )

    def __str__(self):
        return f"Feedback from {self.student.user.username}"


class FeedbackStaff(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Staff feedback/message to admin.
    Admin can reply with feedback_reply.
    """
    __tablename__ = "feedback_staff"

    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False, index=True)
    
    # Messages
    feedback: Text = Column(Text, nullable=False)  # Staff's message
    feedback_reply: Text = Column(Text, nullable=True)  # Admin's reply
    
    # Relationships
    staff = relationship("Staff", backref="feedbacks")

    __table_args__ = (
        Index("ix_feedback_staff_staff", "staff_id"),
    )

    def __str__(self):
        return f"Feedback from {self.staff.user.username}"
