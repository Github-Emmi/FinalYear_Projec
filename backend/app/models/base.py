"""
Base classes and mixins for SQLAlchemy models.
Provides common patterns like timestamps, soft deletes, UUID primary keys.
"""

from sqlalchemy import Column, DateTime, Boolean, UUID as SQLAUUID, func
from sqlalchemy.orm import declared_attr, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from typing import Optional


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models"""
    __allow_unmapped__ = True  # Allow Column() without Mapped[] type annotations


class UUIDPrimaryKeyMixin:
    """Mixin to add UUID as primary key (PostgreSQL native)"""

    @declared_attr
    def id(cls):
        return Column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            nullable=False,
        )


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps"""

    @declared_attr
    def created_at(cls):
        return Column(
            DateTime,
            server_default=func.now(),
            default=datetime.utcnow,
            nullable=False,
            index=True,
        )

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime,
            server_default=func.now(),
            onupdate=func.now(),
            default=datetime.utcnow,
            nullable=False,
        )


class SoftDeleteMixin:
    """Mixin to add soft delete capability (is_deleted flag)"""

    @declared_attr
    def is_deleted(cls):
        return Column(Boolean, default=False, nullable=False, index=True)

    @declared_attr
    def deleted_at(cls):
        return Column(DateTime, nullable=True, default=None)


class AuditableMixin:
    """Mixin for audit trails (created_by, updated_by)"""

    @declared_attr
    def created_by(cls):
        return Column(UUID(as_uuid=True), nullable=True, index=True)

    @declared_attr
    def updated_by(cls):
        return Column(UUID(as_uuid=True), nullable=True, index=True)
