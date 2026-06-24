# app/domain/models/financial_ratio.py
"""
FinancialRatio model — stores one computed ratio per row.
18 ratios per filing across 5 categories.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum, ForeignKey, Index, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.enums import RatioCategory, RatioSignal
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.filing import Filing


class FinancialRatio(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    One computed financial ratio for a specific filing.

    Each ratio includes:
      - computed_value: the actual calculated value
      - benchmark_value: industry average / standard threshold
      - signal: GOOD / WARNING / CRITICAL based on comparison
      - interpretation: human-readable explanation of the value
      - risk_note: specific risk implication if signal is WARNING/CRITICAL

    18 ratios are computed per filing:
      Liquidity (3):    Current Ratio, Quick Ratio, Cash Ratio
      Profitability (5): ROE, ROA, Gross Margin, EBITDA Margin, Net Margin
      Leverage (3):     Debt-to-Equity, Debt-to-Assets, Interest Coverage
      Efficiency (3):   Asset Turnover, Inventory Turnover, Receivable Turnover
      Market (4):       EPS, P/E, P/B, Dividend Yield
    """
    __tablename__ = "financial_ratios"

    # ── Document reference ────────────────────────────────────────────────
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Ratio identity ────────────────────────────────────────────────────
    ratio_category: Mapped[RatioCategory] = mapped_column(
        Enum(RatioCategory, name="ratio_category", create_type=True),
        nullable=False,
    )
    ratio_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "Current Ratio", "Return on Equity"

    # ── Computed values ───────────────────────────────────────────────────
    formula: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # e.g. "Current Assets / Current Liabilities"
    computed_value: Mapped[float | None] = mapped_column(
        Numeric(20, 6), nullable=True
    )  # None if required inputs were not found in the financial statement

    # ── Benchmark comparison ──────────────────────────────────────────────
    benchmark_value: Mapped[float | None] = mapped_column(
        Numeric(20, 6), nullable=True
    )
    benchmark_source: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # e.g. "Industry average — IT Services India 2023"

    # ── Signal and interpretation ─────────────────────────────────────────
    signal: Mapped[RatioSignal] = mapped_column(
        Enum(RatioSignal, name="ratio_signal", create_type=True),
        nullable=False,
        default=RatioSignal.NEUTRAL,
        server_default=RatioSignal.NEUTRAL.value,
    )
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    filing: Mapped["Filing"] = relationship(
        "Filing", back_populates="financial_ratios"
    )

    # ── Constraints and indexes ───────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "filing_id", "ratio_name",
            name="uq_ratio_name_per_filing",
        ),
        Index("idx_ratios_filing_id", "filing_id"),
        Index("idx_ratios_category", "filing_id", "ratio_category"),
        Index("idx_ratios_signal", "signal"),
    )

    def __repr__(self) -> str:
        return (
            f"<FinancialRatio id={self.id} name={self.ratio_name} "
            f"value={self.computed_value} signal={self.signal}>"
        )
