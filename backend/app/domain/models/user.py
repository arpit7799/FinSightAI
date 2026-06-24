# app/domain/models/user.py
"""
User model — authentication and RBAC.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.enums import UserRole
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.domain.models.company import Company
    from app.domain.models.filing import Filing
    from app.domain.models.chat import ChatSession
    from app.domain.models.report import GeneratedReport


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Represents an authenticated user of FinSight AI.

    Roles:
        ADMIN   — full access including user management
        ANALYST — upload documents, run analysis, view all results
        VIEWER  — read-only access to analysis results
    """
    __tablename__ = "users"

    # ── Identity ─────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Access Control ────────────────────────────────────────────────────
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_type=True),
        nullable=False,
        default=UserRole.ANALYST,
        server_default=UserRole.ANALYST.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────
    companies: Mapped[list["Company"]] = relationship(
        "Company", back_populates="creator", foreign_keys="Company.created_by"
    )
    filings: Mapped[list["Filing"]] = relationship(
        "Filing", back_populates="uploader", foreign_keys="Filing.uploaded_by"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="user"
    )
    generated_reports: Mapped[list["GeneratedReport"]] = relationship(
        "GeneratedReport", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
