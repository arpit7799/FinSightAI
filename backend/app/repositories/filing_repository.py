# app/repositories/filing_repository.py
"""
Database operations for Filing records.
Follows the same Repository Pattern as user_repository.py from Phase 3.
"""

import uuid
from sqlalchemy.orm import Session

from app.domain.models.filing import Filing
from app.domain.models.enums import ProcessingStatus


class FilingRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, filing: Filing) -> Filing:
        self.db.add(filing)
        self.db.commit()
        self.db.refresh(filing)
        return filing

    def get_by_id(self, filing_id: str) -> Filing | None:
        return (
            self.db.query(Filing)
            .filter(Filing.id == filing_id, Filing.is_deleted == False)
            .first()
        )

    def get_all_for_user(self, user_id: str, skip: int = 0, limit: int = 20) -> list[Filing]:
        """Get all filings uploaded by a specific user, newest first."""
        return (
            self.db.query(Filing)
            .filter(Filing.uploaded_by == user_id, Filing.is_deleted == False)
            .order_by(Filing.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_for_company(self, company_id: str) -> list[Filing]:
        """Get all filings for a company, ordered by fiscal year."""
        return (
            self.db.query(Filing)
            .filter(Filing.company_id == company_id, Filing.is_deleted == False)
            .order_by(Filing.fiscal_year.desc())
            .all()
        )

    def update_status(
        self,
        filing_id: str,
        status: ProcessingStatus,
        error: str = None,
    ) -> Filing | None:
        filing = self.get_by_id(filing_id)
        if not filing:
            return None

        filing.processing_status = status
        if error:
            filing.processing_error = error

        self.db.commit()
        self.db.refresh(filing)
        return filing

    def update_page_count(self, filing_id: str, page_count: int) -> None:
        filing = self.get_by_id(filing_id)
        if filing:
            filing.page_count = page_count
            self.db.commit()

    def soft_delete(self, filing_id: str) -> bool:
        """Soft delete — sets is_deleted=True, never removes from DB."""
        filing = self.get_by_id(filing_id)
        if not filing:
            return False

        filing.is_deleted = True
        self.db.commit()
        return True
