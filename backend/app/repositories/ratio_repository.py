# app/repositories/ratio_repository.py
"""
Database operations for FinancialRatio records.
"""

from sqlalchemy.orm import Session
from app.domain.models.financial_ratio import FinancialRatio
from app.domain.models.enums import RatioCategory


class RatioRepository:

    def __init__(self, db: Session):
        self.db = db

    def save_ratios(self, ratios: list[FinancialRatio]) -> None:
        """Save a batch of ratio records, replacing existing ones for the filing."""
        if not ratios:
            return

        filing_id = ratios[0].filing_id

        # Delete existing ratios for this filing before inserting new ones
        self.db.query(FinancialRatio).filter(
            FinancialRatio.filing_id == filing_id
        ).delete()

        self.db.add_all(ratios)
        self.db.commit()

    def get_by_filing_id(self, filing_id: str) -> list[FinancialRatio]:
        return (
            self.db.query(FinancialRatio)
            .filter(FinancialRatio.filing_id == filing_id)
            .order_by(FinancialRatio.ratio_category, FinancialRatio.ratio_name)
            .all()
        )

    def get_by_category(self, filing_id: str, category: RatioCategory) -> list[FinancialRatio]:
        return (
            self.db.query(FinancialRatio)
            .filter(
                FinancialRatio.filing_id == filing_id,
                FinancialRatio.ratio_category == category,
            )
            .all()
        )

    def get_by_name(self, filing_id: str, ratio_name: str) -> FinancialRatio | None:
        return (
            self.db.query(FinancialRatio)
            .filter(
                FinancialRatio.filing_id == filing_id,
                FinancialRatio.ratio_name == ratio_name,
            )
            .first()
        )