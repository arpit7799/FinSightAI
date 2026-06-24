# app/domain/models/company.py
"""
Company model — represents a publicly listed or private company
whose financial filings are uploaded to FinSight AI.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.domain.models.user import User
    from app.domain.models.filing import Filing


class Company(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Represents a company whose annual reports are analyzed by FinSight AI.

    One company can have many filings (one per fiscal year / quarter).
    The ticker symbol is optional — private companies may not have one.
    """
    __tablename__ = "companies"

    # ── Identity ─────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ticker: Mapped[str | None] = mapped_column(
        String(20), nullable=True, unique=True
    )

    # ── Classification ────────────────────────────────────────────────────
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(
        String(100), nullable=False, default="India", server_default="India"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Ownership ─────────────────────────────────────────────────────────
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────
    creator: Mapped["User"] = relationship(
        "User", back_populates="companies", foreign_keys=[created_by]
    )
    filings: Mapped[list["Filing"]] = relationship(
        "Filing", back_populates="company", cascade="all, delete-orphan"
    )

    # ── Table-level constraints and indexes ───────────────────────────────
    __table_args__ = (
        Index("idx_companies_ticker", "ticker", postgresql_where="is_deleted = false"),
        Index("idx_companies_sector", "sector"),
        Index(
            "idx_companies_name_fts",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name} ticker={self.ticker}>"
