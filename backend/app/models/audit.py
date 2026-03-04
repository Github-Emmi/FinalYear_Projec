"""
Audit log model: AuditLog
Tracks all admin/staff actions for compliance and analytics.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime
import uuid

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Audit trail for all important actions (create, update, delete).
    Used for compliance, debugging, and analytics.
    """
    __tablename__ = "audit_log"

    # Actor
    user_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, index=True)
    
    # Action
    action = Column(String(50), nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    resource_type = Column(String(100), nullable=False, index=True)  # Student, Quiz, Assignment, etc.
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Details
    changes: JSON = Column(JSON, nullable=True)  # What changed: {field: [old_value, new_value]}
    description: Text = Column(Text, nullable=True)  # Human-readable description
    
    # Context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)  # Browser info
    status = Column(String(20), default="success", nullable=False)  # success, failed
    error_message: Text = Column(Text, nullable=True)  # If status is failed
    
    # Relationships
    user = relationship("CustomUser")

    __table_args__ = (
        Index("ix_audit_log_action_resource", "action", "resource_type"),
        Index("ix_audit_log_user_timestamp", "user_id", "created_at"),
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
    )

    def __str__(self):
        return f"{self.action} {self.resource_type} {self.resource_id} by {self.user.username}"
