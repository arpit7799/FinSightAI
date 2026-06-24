# app/domain/models/report.py
"""
GeneratedReport model — tracks PDF executive reports
generated from filing analysis results.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.filing import Filing
    from app.domain.models.user import User


class GeneratedReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A PDF report generated from a filing's complete analysis.

    included_sections tracks which analysis components were
    included in this report version.

    JSONB schema for included_sections:
        ["FINANCIAL_RATIOS", "RISK_PREDICTION", "FRAUD_ASSESSMENT",
         "FORECASTS", "NLP_INSIGHTS", "COMPETITOR_BENCHMARK"]
    """
    __tablename__ = "generated_reports"

    # ── References ────────────────────────────────────────────────────────
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Report metadata ───────────────────────────────────────────────────
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="EXECUTIVE_PDF",
        server_default="EXECUTIVE_PDF"
    )
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    included_sections: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    # ── Generation status ─────────────────────────────────────────────────
    generation_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", server_default="PENDING"
    )  # PENDING, GENERATING, COMPLETE, FAILED
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    filing: Mapped["Filing"] = relationship(
        "Filing", back_populates="generated_reports"
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="generated_reports"
    )

    # ── Indexes ───────────────────────────────────────────────────────────
    __table_args__ = (
        Index("idx_reports_filing_id", "filing_id"),
        Index("idx_reports_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<GeneratedReport id={self.id} filing_id={self.filing_id} "
            f"status={self.generation_status}>"
        )
