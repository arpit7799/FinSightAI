# app/domain/models/risk_prediction.py
"""
RiskPrediction model — stores ML risk scoring results
from XGBoost + LightGBM ensemble with SHAP explanations.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.enums import RiskClass
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.filing import Filing


class RiskPrediction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    ML-based financial risk prediction for a single filing.
    One RiskPrediction record per filing (1:1 relationship).

    Pipeline:
      1. FeatureEngineer builds a vector from the 8 financial ratios.
      2. XGBoost and LightGBM each produce a bankruptcy probability (0–1).
      3. Weighted average → final risk_score (0–100).
      4. SHAPExplainer produces per-feature contribution values.
      5. Llama 3 generates a natural-language narrative from the SHAP output.

    JSONB schema for feature_vector:
        {"roe": 0.12, "roa": 0.08, "debt_to_equity": 1.4,
         "current_ratio": 1.1, "quick_ratio": 0.9,
         "revenue_growth": -0.05, "cash_flow_margin": 0.07,
         "interest_coverage": 2.3}

    JSONB schema for shap_values:
        {"debt_to_equity": 0.18, "current_ratio": -0.12,
         "revenue_growth": 0.09, ...}

    JSONB schema for top_factors:
        [{"factor": "debt_to_equity", "direction": "increases_risk",
          "impact": 0.18, "label": "High Debt Ratio"},
         ...]
    """
    __tablename__ = "risk_predictions"

    # ── Document reference ────────────────────────────────────────────────
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Composite risk score ──────────────────────────────────────────────
    risk_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )  # 0.00 to 100.00
    risk_class: Mapped[RiskClass] = mapped_column(
        Enum(RiskClass, name="risk_class", create_type=True),
        nullable=False,
    )

    # ── Individual model scores ───────────────────────────────────────────
    xgb_score: Mapped[float | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )  # XGBoost raw probability 0.0000–1.0000
    lgbm_score: Mapped[float | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )  # LightGBM raw probability 0.0000–1.0000
    xgb_weight: Mapped[float] = mapped_column(
        Numeric(4, 3), nullable=False, default=0.6, server_default="0.6"
    )
    lgbm_weight: Mapped[float] = mapped_column(
        Numeric(4, 3), nullable=False, default=0.4, server_default="0.4"
    )

    # ── Feature vector ────────────────────────────────────────────────────
    feature_vector: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # ── SHAP explainability ───────────────────────────────────────────────
    shap_values: Mapped[dict] = mapped_column(JSONB, nullable=False)
    shap_base_value: Mapped[float | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    top_factors: Mapped[list] = mapped_column(JSONB, nullable=False)

    # ── LIME secondary explanation ────────────────────────────────────────
    lime_explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── AI narrative (Llama 3) ────────────────────────────────────────────
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="llama3", server_default="llama3"
    )

    # ── Model versioning ──────────────────────────────────────────────────
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────
    filing: Mapped["Filing"] = relationship(
        "Filing", back_populates="risk_prediction"
    )

    # ── Constraints and indexes ───────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("filing_id", name="uq_risk_prediction_per_filing"),
        Index("idx_risk_filing_id", "filing_id"),
        Index("idx_risk_class", "risk_class"),
        Index("idx_risk_score_desc", "risk_score"),
        Index(
            "idx_risk_shap_gin",
            "shap_values",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<RiskPrediction id={self.id} filing_id={self.filing_id} "
            f"score={self.risk_score} class={self.risk_class}>"
        )
