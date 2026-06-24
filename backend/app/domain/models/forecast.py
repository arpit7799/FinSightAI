# app/domain/models/forecast.py
"""
Forecast model — Prophet / ARIMA time-series forecast results
for revenue, profit, EBITDA, and cash flow.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.enums import ForecastMetric, ForecastModel
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.filing import Filing


class Forecast(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Time-series forecast for a single metric and model combination.

    One filing can have multiple Forecast rows:
      - REVENUE × PROPHET
      - REVENUE × ARIMA
      - NET_PROFIT × PROPHET
      - etc.

    historical_data: the data points used to train the model.
    JSONB schema: [{"year": 2021, "value": 125000000}, ...]

    forecast_data: the predicted future values with confidence intervals.
    Prophet JSONB schema:
        [{"ds": "2024-03-31", "yhat": 145000000,
          "yhat_lower": 130000000, "yhat_upper": 160000000}, ...]
    """
    __tablename__ = "forecasts"

    # ── Document reference ────────────────────────────────────────────────
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Forecast configuration ────────────────────────────────────────────
    metric_name: Mapped[ForecastMetric] = mapped_column(
        Enum(ForecastMetric, name="forecast_metric", create_type=True),
        nullable=False,
    )
    model_used: Mapped[ForecastModel] = mapped_column(
        Enum(ForecastModel, name="forecast_model", create_type=True),
        nullable=False,
    )

    # ── Training data ─────────────────────────────────────────────────────
    historical_data: Mapped[list] = mapped_column(JSONB, nullable=False)
    data_points_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Forecast output ───────────────────────────────────────────────────
    forecast_data: Mapped[list] = mapped_column(JSONB, nullable=False)
    forecast_years: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )

    # ── Model parameters and quality metrics ──────────────────────────────
    model_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mae: Mapped[float | None] = mapped_column(
        Numeric(20, 4), nullable=True
    )  # Mean Absolute Error on validation set
    mape: Mapped[float | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )  # Mean Absolute Percentage Error

    # ── Trend summary ─────────────────────────────────────────────────────
    trend_direction: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # 'UPWARD', 'DOWNWARD', 'STABLE'
    growth_rate_pct: Mapped[float | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # Projected CAGR as percentage

    # ── Relationships ─────────────────────────────────────────────────────
    filing: Mapped["Filing"] = relationship("Filing", back_populates="forecasts")

    # ── Constraints and indexes ───────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "filing_id", "metric_name", "model_used",
            name="uq_forecast_per_filing_metric_model",
        ),
        Index("idx_forecasts_filing_id", "filing_id"),
        Index("idx_forecasts_metric", "metric_name"),
        Index(
            "idx_forecasts_data_gin",
            "forecast_data",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Forecast id={self.id} filing_id={self.filing_id} "
            f"metric={self.metric_name} model={self.model_used}>"
        )
