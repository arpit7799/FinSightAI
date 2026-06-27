# app/repositories/risk_repository.py
"""
Database operations for RiskPrediction records.
"""

from sqlalchemy.orm import Session
from app.domain.models.risk_prediction import RiskPrediction


class RiskRepository:

    def __init__(self, db: Session):
        self.db = db

    def save(self, prediction: RiskPrediction) -> RiskPrediction:
        # Delete existing prediction for this filing first
        self.db.query(RiskPrediction).filter(
            RiskPrediction.filing_id == prediction.filing_id
        ).delete()

        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def get_by_filing_id(self, filing_id: str) -> RiskPrediction | None:
        return (
            self.db.query(RiskPrediction)
            .filter(RiskPrediction.filing_id == filing_id)
            .first()
        )

    def get_high_risk_filings(self, limit: int = 10) -> list[RiskPrediction]:
        """Get the highest risk filings across all companies."""
        from app.domain.models.enums import RiskClass
        return (
            self.db.query(RiskPrediction)
            .filter(RiskPrediction.risk_class.in_([
                RiskClass.HIGH, RiskClass.CRITICAL
            ]))
            .order_by(RiskPrediction.risk_score.desc())
            .limit(limit)
            .all()
        )