"""
Base classes and mixins for SQLAlchemy models.
Provides common patterns like timestamps, soft deletes, etc.
"""

from sqlalchemy import Column, DateTime, Boolean, UUID, func
from sqlalchemy.orm import declared_attr, DeclarativeBase
from datetime import datetime
import uuid
from typing import Optional


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models"""

    @declared_attr
    def created_at(cls) -> Column[DateTime]:
        return Column(
            DateTime,
            default=datetime.utcnow,
            nullable=False,
            index=True,
        )

    @declared_attr
    def updated_at(cls) -> Column[DateTime]:
        return Column(
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False,
        )


class SoftDeleteMixin:
    """Mixin to add soft delete capability to models"""

    @declared_attr
    def is_deleted(cls) -> Column[Boolean]:
        return Column(Boolean, default=False, nullable=False, index=True)

    @declared_attr
    def deleted_at(cls) -> Column[Optional[DateTime]]:
        return Column(DateTime, nullable=True, default=None)


class UUIDPrimaryKeyMixin:
    """Mixin to add UUID as primary key"""

    @declared_attr
    def id(cls) -> Column[UUID]:
        return Column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            nullable=False,
        )


class AuditableMixin(TimestampMixin):
    """Mixin for models that need audit trails (created_at, updated_at, created_by, updated_by)"""

    @declared_attr
    def created_by(cls) -> Column[Optional[UUID]]:
        return Column(UUID(as_uuid=True), nullable=True, index=True)

    @declared_attr
    def updated_by(cls) -> Column[Optional[UUID]]:
        return Column(UUID(as_uuid=True), nullable=True, index=True)
