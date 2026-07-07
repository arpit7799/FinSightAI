from sqlalchemy.orm import Session

from app.models.financial_data import FinancialData


class FinancialDataService:

    @staticmethod
    def get_by_report_id(
        db: Session,
        report_id: int,
    ):
        return (
            db.query(FinancialData)
            .filter(
                FinancialData.report_id == report_id
            )
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        report_id: int,
        data: dict,
    ):
        financial_data = FinancialData(
            report_id=report_id,
            **data,
        )

        db.add(financial_data)
        db.commit()
        db.refresh(financial_data)

        return financial_data