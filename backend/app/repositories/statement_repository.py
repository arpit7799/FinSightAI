# app/repositories/statement_repository.py
"""
Database operations for FinancialStatement records.
"""

from sqlalchemy.orm import Session

from app.domain.models.financial_statement import FinancialStatement
from app.domain.models.enums import StatementType


class StatementRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_filing_id(self, filing_id: str) -> list[FinancialStatement]:
        """Get all financial statements for a filing."""
        return (
            self.db.query(FinancialStatement)
            .filter(FinancialStatement.filing_id == filing_id)
            .all()
        )

    def get_by_type(self, filing_id: str, statement_type: StatementType) -> FinancialStatement | None:
        """Get a specific statement type for a filing."""
        return (
            self.db.query(FinancialStatement)
            .filter(
                FinancialStatement.filing_id == filing_id,
                FinancialStatement.statement_type == statement_type,
            )
            .first()
        )

    def get_normalized_data(self, filing_id: str) -> dict:
        """
        Get all normalized financial data for a filing as a flat dict.
        Merges all statement types together — useful for ratio calculation.
        """
        statements = self.get_by_filing_id(filing_id)

        merged = {}
        for stmt in statements:
            if stmt.normalized_data:
                merged.update(stmt.normalized_data)

        return merged
