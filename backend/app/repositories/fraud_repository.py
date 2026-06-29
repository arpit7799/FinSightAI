# app/repositories/fraud_repository.py
"""
Database operations for FraudAssessment records.
"""

from sqlalchemy.orm import Session
from app.domain.models.fraud_assessment import FraudAssessment
from app.domain.models.enums import FraudRiskClass


class FraudRepository:

    def __init__(self, db: Session):
        self.db = db

    def save(self, assessment: FraudAssessment) -> FraudAssessment:
        # Delete existing assessment for this filing
        self.db.query(FraudAssessment).filter(
            FraudAssessment.filing_id == assessment.filing_id
        ).delete()

        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    def get_by_filing_id(self, filing_id: str) -> FraudAssessment | None:
        return (
            self.db.query(FraudAssessment)
            .filter(FraudAssessment.filing_id == filing_id)
            .first()
        )

    def get_high_risk_filings(self, limit: int = 10) -> list[FraudAssessment]:
        """Get filings with GREY_ZONE or MANIPULATOR fraud signals."""
        return (
            self.db.query(FraudAssessment)
            .filter(FraudAssessment.fraud_risk_class.in_([
                FraudRiskClass.GREY_ZONE,
                FraudRiskClass.MANIPULATOR,
            ]))
            .order_by(FraudAssessment.overall_fraud_score.desc())
            .limit(limit)
            .all()
        )