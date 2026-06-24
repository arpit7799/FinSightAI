# app/domain/models/financial_statement.py
"""
FinancialStatement model — stores extracted Balance Sheet,
Income Statement, and Cash Flow Statement data from a filing.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum, ForeignKey, Index, Integer,
    Numeric, String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.enums import StatementType
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.filing import Filing


class FinancialStatement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single financial statement extracted from a filing.

    One filing produces up to 3 FinancialStatement rows:
      - BALANCE_SHEET
      - INCOME_STATEMENT
      - CASH_FLOW_STATEMENT

    raw_data: the table as extracted (rows/columns dict) — for debugging.
    normalized_data: key→value dict of standard financial line items.
                     This is what the ratio calculator and ML engines consume.

    Example normalized_data keys:
        total_revenue, gross_profit, net_income, total_assets,
        total_liabilities, total_equity, current_assets,
        current_liabilities, cash_and_equivalents, total_debt,
        operating_cash_flow, ebitda, interest_expense, inventory,
        accounts_receivable, depreciation_amortization
    """
    __tablename__ = "financial_statements"

    # ── Document reference ────────────────────────────────────────────────
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Statement metadata ────────────────────────────────────────────────
    statement_type: Mapped[StatementType] = mapped_column(
        Enum(StatementType, name="statement_type", create_type=True),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="INR", server_default="INR"
    )
    unit_multiplier: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    # unit_multiplier values: 1 (units), 1000 (thousands), 100000 (lakhs),
    # 10000000 (crores), 1000000 (millions)

    # ── Extracted data ────────────────────────────────────────────────────
    raw_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # Raw table structure as extracted by pdfplumber/PyMuPDF
    normalized_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # Standardized key→value financial line items

    # ── Extraction quality ────────────────────────────────────────────────
    extraction_confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )  # 0.0000 to 1.0000 — how confident the extractor is in the values
    extraction_method: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 'pdfplumber', 'pymupdf', 'paddleocr'

    # ── Relationships ─────────────────────────────────────────────────────
    filing: Mapped["Filing"] = relationship(
        "Filing", back_populates="financial_statements"
    )

    # ── Constraints and indexes ───────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "filing_id", "statement_type",
            name="uq_statement_type_per_filing",
        ),
        Index("idx_statements_filing_id", "filing_id"),
        Index("idx_statements_type", "statement_type"),
        # GIN index enables querying inside normalized_data JSONB
        Index(
            "idx_statements_normalized_gin",
            "normalized_data",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FinancialStatement id={self.id} filing_id={self.filing_id} "
            f"type={self.statement_type}>"
        )
