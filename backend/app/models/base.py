"""Base mixins for all SQLAlchemy ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Uuid
from sqlalchemy.orm import declared_attr
from sqlalchemy.sql import func

from app.core.database import Base


class UUIDPrimaryKeyMixin:
    """UUID v4 primary key. All entities use this instead of integer auto-increment."""

    @declared_attr
    def id(cls):
        return Column(
            Uuid,
            primary_key=True,
            default=uuid.uuid4,
            nullable=False,
        )


class TimestampMixin:
    """Adds created_at and updated_at columns to every model that uses it."""

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
    """Adds is_deleted flag. Repositories MUST filter WHERE is_deleted = FALSE."""

    @declared_attr
    def is_deleted(cls):
        return Column(Boolean, default=False, nullable=False, server_default="false")


class BaseModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Concrete base for all application models.
    Inherit from this instead of Base directly.

    Example::

        class User(BaseModel):
            __tablename__ = "users"
            email = Column(String(255), unique=True, nullable=False)
    """

    __abstract__ = True
