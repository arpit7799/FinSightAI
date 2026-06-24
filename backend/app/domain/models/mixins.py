# app/domain/models/mixins.py
"""
Reusable SQLAlchemy column mixins.
Inherit these into models to avoid repeating common columns.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    """
    Adds a UUID primary key generated at the database level.
    All FinSight entities use UUID PKs to avoid sequential ID enumeration.
    """
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )


class TimestampMixin:
    """
    Adds created_at and updated_at columns with automatic management.
    updated_at is refreshed on every UPDATE via onupdate.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        onupdate=utcnow,
    )


class SoftDeleteMixin:
    """
    Adds soft delete support.
    Records are never physically deleted — is_deleted marks them inactive.
    This preserves audit trails required for financial data.
    """
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
