from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.financial_data_service import FinancialDataService
from app.services.financial_ratio_service import FinancialRatioService
from app.services.ratio_calculation_service import RatioCalculationService

router = APIRouter(
    prefix="/reports",
    tags=["Financial Ratios"],
)


@router.post("/{report_id}/calculate-ratios")
def calculate_ratios(
    report_id: int,
    db: Session = Depends(get_db),
):

    financial_data = FinancialDataService.get_by_report_id(
        db,
        report_id,
    )

    if financial_data is None:
        raise HTTPException(
            status_code=404,
            detail="Financial data not found. Run financial extraction first.",
        )

    existing = FinancialRatioService.get_by_report_id(
        db,
        report_id,
    )

    if existing:

        return {
            "message": "Financial ratios already exist.",
            "report_id": report_id,
            "ratios": {
                "current_ratio": existing.current_ratio,
                "quick_ratio": existing.quick_ratio,
                "cash_ratio": existing.cash_ratio,
                "roa": existing.roa,
                "roe": existing.roe,
                "gross_margin": existing.gross_margin,
                "operating_margin": existing.operating_margin,
                "net_margin": existing.net_margin,
                "asset_turnover": existing.asset_turnover,
                "inventory_turnover": existing.inventory_turnover,
                "receivables_turnover": existing.receivables_turnover,
                "debt_to_equity": existing.debt_to_equity,
                "debt_to_assets": existing.debt_to_assets,
                "interest_coverage": existing.interest_coverage,
                "eps": existing.eps,
                "book_value_per_share": existing.book_value_per_share,
                "pe_ratio": existing.pe_ratio,
                "price_to_book": existing.price_to_book,
                "dividend_yield": existing.dividend_yield,
                "health_score": existing.health_score,
            },
        }

    ratios = RatioCalculationService.calculate(
        financial_data
    )

    FinancialRatioService.create(
        db,
        report_id,
        ratios,
    )

    return {
        "message": "Financial ratios calculated successfully.",
        "report_id": report_id,
        "ratios": ratios,
    }