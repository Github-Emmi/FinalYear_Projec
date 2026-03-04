"""
User models: CustomUser, RememberToken, API tokens, Redis sessions
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from ..core.database import Base
from .base import TimestampMixin, SoftDeleteMixin, UUIDPrimaryKeyMixin, AuditableMixin


class CustomUser(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin):
    """
    Custom user model extending Django-like functionality.
    Single table inheritance for admin, staff, students.
    """
    __tablename__ = "custom_user"

    # User identity
    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(254), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    
    # Profile
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    
    # User type (RBAC)
    user_type = Column(Integer, default=3, nullable=False)  # 1=HOD, 2=Staff, 3=Student
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_staff = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Audit
    last_login = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_custom_user_email_active", "email", "is_active"),
        Index("ix_custom_user_username_active", "username", "is_active"),
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"


class RememberToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Persistent login tokens for 'Remember Me' functionality.
    One token per user at a time (create_or_update pattern).
    """
    __tablename__ = "remember_token"

    user_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, unique=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Relationship
    user = relationship("CustomUser", backref="remember_tokens")

    __table_args__ = (
        Index("ix_remember_token_user_expires", "user_id", "expires_at"),
    )


class ApiToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    API tokens for service-to-service authentication.
    Allows applications/scripts to authenticate without user credentials.
    """
    __tablename__ = "api_token"

    user_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g., "Mobile App", "Integration Service"
    token = Column(String(64), unique=True, nullable=False, index=True)
    
    # Permissions
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    ip_whitelist = Column(Text, nullable=True)  # JSON-serialized list
    
    # Relationship
    user = relationship("CustomUser", backref="api_tokens")

    __table_args__ = (
        Index("ix_api_token_user_active", "user_id", "is_active"),
        Index("ix_api_token_expires", "expires_at"),
    )


class RedisSession(Base, UUIDPrimaryKeyMixin):
    """
    Track active user sessions managed by Redis.
    Cached in Redis, persisted in DB for audit/recovery.
    """
    __tablename__ = "redis_session"

    user_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, index=True)
    session_key = Column(String(64), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 (15) or IPv6 (45)
    user_agent = Column(String(500), nullable=True)
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationship
    user = relationship("CustomUser", backref="sessions")

    __table_args__ = (
        Index("ix_redis_session_user_active", "user_id", "is_active"),
        Index("ix_redis_session_expires", "expires_at"),
    )
