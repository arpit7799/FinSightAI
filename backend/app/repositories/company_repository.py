# app/repositories/company_repository.py
"""
Database operations for Company records.
"""

from sqlalchemy.orm import Session
from app.domain.models.company import Company


class CompanyRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, company: Company) -> Company:
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company

    def get_by_id(self, company_id: str) -> Company | None:
        return (
            self.db.query(Company)
            .filter(Company.id == company_id, Company.is_deleted == False)
            .first()
        )

    def get_by_ticker(self, ticker: str) -> Company | None:
        return (
            self.db.query(Company)
            .filter(Company.ticker == ticker.upper(), Company.is_deleted == False)
            .first()
        )

    def get_all(self, skip: int = 0, limit: int = 50) -> list[Company]:
        return (
            self.db.query(Company)
            .filter(Company.is_deleted == False)
            .order_by(Company.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_by_name(self, name: str) -> list[Company]:
        return (
            self.db.query(Company)
            .filter(
                Company.name.ilike(f"%{name}%"),
                Company.is_deleted == False,
            )
            .all()
        )
