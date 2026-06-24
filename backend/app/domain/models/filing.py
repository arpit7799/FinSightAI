# app/domain/models/filing.py
"""
Filing model — represents a single uploaded financial document (PDF).
Central entity that all analysis results link back to.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger, Enum, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.enums import FilingType, ProcessingStatus
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.domain.models.user import User
    from app.domain.models.company import Company
    from app.domain.models.document_chunk import DocumentChunk
    from app.domain.models.financial_statement import FinancialStatement
    from app.domain.models.financial_ratio import FinancialRatio
    from app.domain.models.nlp_insight import NLPInsight
    from app.domain.models.risk_prediction import RiskPrediction
    from app.domain.models.fraud_assessment import FraudAssessment
    from app.domain.models.forecast import Forecast
    from app.domain.models.chat import ChatSession
    from app.domain.models.report import GeneratedReport


class Filing(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Represents a single uploaded financial filing (PDF document).

    This is the central entity in FinSight AI. Every AI output —
    NLP insights, embeddings, ratio analysis, risk scores, forecasts —
    is linked back to a specific Filing record via foreign key.

    Processing lifecycle is tracked via processing_status.
    """
    __tablename__ = "filings"

    # ── Document identity ─────────────────────────────────────────────────
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    filing_type: Mapped[FilingType] = mapped_column(
        Enum(FilingType, name="filing_type", create_type=True),
        nullable=False,
    )

    # ── Fiscal period ─────────────────────────────────────────────────────
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_period: Mapped[str] = mapped_column(
        String(10), nullable=False, default="FY", server_default="FY"
    )  # FY, Q1, Q2, Q3, Q4

    # ── File metadata ─────────────────────────────────────────────────────
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Processing pipeline ───────────────────────────────────────────────
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status", create_type=True),
        nullable=False,
        default=ProcessingStatus.PENDING,
        server_default=ProcessingStatus.PENDING.value,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────
    company: Mapped["Company"] = relationship("Company", back_populates="filings")
    uploader: Mapped["User"] = relationship(
        "User", back_populates="filings", foreign_keys=[uploaded_by]
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="filing", cascade="all, delete-orphan"
    )
    financial_statements: Mapped[list["FinancialStatement"]] = relationship(
        "FinancialStatement", back_populates="filing", cascade="all, delete-orphan"
    )
    financial_ratios: Mapped[list["FinancialRatio"]] = relationship(
        "FinancialRatio", back_populates="filing", cascade="all, delete-orphan"
    )
    nlp_insight: Mapped["NLPInsight | None"] = relationship(
        "NLPInsight", back_populates="filing", uselist=False,
        cascade="all, delete-orphan"
    )
    risk_prediction: Mapped["RiskPrediction | None"] = relationship(
        "RiskPrediction", back_populates="filing", uselist=False,
        cascade="all, delete-orphan"
    )
    fraud_assessment: Mapped["FraudAssessment | None"] = relationship(
        "FraudAssessment", back_populates="filing", uselist=False,
        cascade="all, delete-orphan"
    )
    forecasts: Mapped[list["Forecast"]] = relationship(
        "Forecast", back_populates="filing", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="filing", cascade="all, delete-orphan"
    )
    generated_reports: Mapped[list["GeneratedReport"]] = relationship(
        "GeneratedReport", back_populates="filing", cascade="all, delete-orphan"
    )

    # ── Constraints and indexes ───────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "company_id", "fiscal_year", "fiscal_period", "filing_type",
            name="uq_filing_per_company_year_period_type",
        ),
        Index("idx_filings_company_id", "company_id"),
        Index("idx_filings_status", "processing_status"),
        Index("idx_filings_fiscal_year", "company_id", "fiscal_year"),
        Index("idx_filings_created_at", "created_at"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.processing_status is None:
            self.processing_status = ProcessingStatus.PENDING

    def __repr__(self) -> str:
        return (
            f"<Filing id={self.id} company_id={self.company_id} "
            f"year={self.fiscal_year} status={self.processing_status}>"
        )
