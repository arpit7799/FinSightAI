from sqlalchemy.orm import Session

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


class CompanyService:

    @staticmethod
    def get_all(db: Session):
        return (
            db.query(Company)
            .order_by(Company.company_name)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, company_id: int):
        return (
            db.query(Company)
            .filter(Company.id == company_id)
            .first()
        )

    @staticmethod
    def get_by_name(db: Session, company_name: str):
        return (
            db.query(Company)
            .filter(Company.company_name == company_name)
            .first()
        )

    @staticmethod
    def search(db: Session, keyword: str):
        return (
            db.query(Company)
            .filter(
                Company.company_name.ilike(f"%{keyword}%")
            )
            .all()
        )

    @staticmethod
    def create(db: Session, company: CompanyCreate):

        existing_company = CompanyService.get_by_name(
            db,
            company.company_name,
        )

        if existing_company:
            return None

        new_company = Company(
            company_name=company.company_name,
            ticker_symbol=company.ticker_symbol,
            industry=company.industry,
            country=company.country,
        )

        db.add(new_company)
        db.commit()
        db.refresh(new_company)

        return new_company

    @staticmethod
    def update(
        db: Session,
        company_id: int,
        company_data: CompanyUpdate,
    ):

        company = CompanyService.get_by_id(db, company_id)

        if not company:
            return None

        update_data = company_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(company, field, value)

        db.commit()
        db.refresh(company)

        return company

    @staticmethod
    def delete(db: Session, company_id: int):

        company = CompanyService.get_by_id(db, company_id)

        if not company:
            return False

        db.delete(company)
        db.commit()

        return True