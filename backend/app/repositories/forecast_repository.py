# app/repositories/forecast_repository.py
"""
Database operations for Forecast records.
"""

from sqlalchemy.orm import Session
from app.domain.models.forecast import Forecast
from app.domain.models.enums import ForecastMetric, ForecastModel


class ForecastRepository:

    def __init__(self, db: Session):
        self.db = db

    def save(self, forecast: Forecast) -> Forecast:
        # Replace existing forecast for same filing + metric + model
        self.db.query(Forecast).filter(
            Forecast.filing_id == forecast.filing_id,
            Forecast.metric_name == forecast.metric_name,
            Forecast.model_used == forecast.model_used,
        ).delete()

        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast

    def get_by_filing_id(self, filing_id: str) -> list[Forecast]:
        return (
            self.db.query(Forecast)
            .filter(Forecast.filing_id == filing_id)
            .all()
        )

    def get_by_metric(
        self, filing_id: str, metric: ForecastMetric
    ) -> list[Forecast]:
        return (
            self.db.query(Forecast)
            .filter(
                Forecast.filing_id == filing_id,
                Forecast.metric_name == metric,
            )
            .all()
        )