# app/domain/models/fraud_assessment.py
"""
FraudAssessment model — Beneish M-Score, Altman Z-Score,
and Isolation Forest anomaly detection results.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.enums import AltmanZone, FraudRiskClass
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.filing import Filing


class FraudAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Fraud detection assessment for a single filing.
    One FraudAssessment record per filing (1:1 relationship).

    Three detection methods are combined:

    1. Beneish M-Score (8-variable model):
       Score < -2.22 → SAFE (non-manipulator)
       Score > -2.22 → potential MANIPULATOR
       Variables: DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA

    2. Altman Z-Score (bankruptcy predictor):
       Z > 2.99 → SAFE zone
       1.81 < Z < 2.99 → GREY zone
       Z < 1.81 → DISTRESS zone

    3. Isolation Forest:
       Anomaly detection on the full ratio vector.
       isolation_score < 0 → anomaly (is_anomaly = True)

    JSONB schema for red_flags:
        [{"flag": "DSRI > 1.465", "description": "Days sales receivable
          index elevated — receivables growing faster than revenue",
          "severity": "HIGH"}, ...]
    """
    __tablename__ = "fraud_assessments"

    # ── Document reference ────────────────────────────────────────────────
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Beneish M-Score variables ─────────────────────────────────────────
    dsri: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    gmi: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    aqi: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    sgi: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    depi: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    sgai: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    lvgi: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    tata: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    beneish_score: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    beneish_signal: Mapped[FraudRiskClass | None] = mapped_column(
        Enum(FraudRiskClass, name="fraud_risk_class", create_type=True),
        nullable=True,
    )

    # ── Altman Z-Score variables ──────────────────────────────────────────
    altman_x1: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    # Working Capital / Total Assets
    altman_x2: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    # Retained Earnings / Total Assets
    altman_x3: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    # EBIT / Total Assets
    altman_x4: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    # Market Value of Equity / Total Liabilities
    altman_x5: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    # Revenue / Total Assets
    altman_score: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    altman_zone: Mapped[AltmanZone | None] = mapped_column(
        Enum(AltmanZone, name="altman_zone", create_type=True),
        nullable=True,
    )

    # ── Isolation Forest ──────────────────────────────────────────────────
    isolation_score: Mapped[float | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )  # Anomaly score; negative = anomaly
    is_anomaly: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ── Aggregated output ─────────────────────────────────────────────────
    overall_fraud_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # Composite 0–100 score
    fraud_risk_class: Mapped[FraudRiskClass] = mapped_column(
        Enum(FraudRiskClass, name="fraud_risk_class"),
        nullable=False,
        default=FraudRiskClass.SAFE,
        server_default=FraudRiskClass.SAFE.value,
    )
    red_flags: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Model versioning ──────────────────────────────────────────────────
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────
    filing: Mapped["Filing"] = relationship(
        "Filing", back_populates="fraud_assessment"
    )

    # ── Constraints and indexes ───────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("filing_id", name="uq_fraud_assessment_per_filing"),
        Index("idx_fraud_filing_id", "filing_id"),
        Index("idx_fraud_risk_class", "fraud_risk_class"),
        Index("idx_fraud_beneish_signal", "beneish_signal"),
        Index(
            "idx_fraud_red_flags_gin",
            "red_flags",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FraudAssessment id={self.id} filing_id={self.filing_id} "
            f"beneish={self.beneish_score} altman={self.altman_score} "
            f"class={self.fraud_risk_class}>"
        )
