from sqlalchemy.orm import Session

from app.models.financial_ratio import FinancialRatio


class FinancialRatioService:

    @staticmethod
    def get_by_report_id(
        db: Session,
        report_id: int,
    ):
        return (
            db.query(FinancialRatio)
            .filter(
                FinancialRatio.report_id == report_id
            )
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        report_id: int,
        ratios: dict,
    ):
        financial_ratio = FinancialRatio(
            report_id=report_id,
            **ratios,
        )

        db.add(financial_ratio)
        db.commit()
        db.refresh(financial_ratio)

        return financial_ratio