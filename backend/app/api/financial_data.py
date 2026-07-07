from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.extracted_text_service import ExtractedTextService
from app.services.financial_data_service import FinancialDataService
from app.services.financial_extraction_service import (
    FinancialExtractionService,
)

router = APIRouter(
    prefix="/reports",
    tags=["Financial Data"],
)


@router.post("/{report_id}/extract-financial-data")
def extract_financial_data(
    report_id: int,
    db: Session = Depends(get_db),
):
    extracted = ExtractedTextService.get_by_report_id(
        db,
        report_id,
    )

    if extracted is None:
        raise HTTPException(
            status_code=404,
            detail="Run OCR first.",
        )

    existing = FinancialDataService.get_by_report_id(
        db,
        report_id,
    )

    if existing:

        return {
            "message": "Financial data already exists.",
            "report_id": report_id,
            "financial_data": {
                "revenue": existing.revenue,
                "net_income": existing.net_income,
                "operating_income": existing.operating_income,
                "total_assets": existing.total_assets,
                "total_liabilities": existing.total_liabilities,
                "total_equity": existing.total_equity,
                "cash": existing.cash,
                "inventory": existing.inventory,
                "receivables": existing.receivables,
                "debt": existing.debt,
                "eps": existing.eps,
                "operating_cash_flow": existing.operating_cash_flow,
                "free_cash_flow": existing.free_cash_flow,
                "shares_outstanding": existing.shares_outstanding,
            },
        }

    data = FinancialExtractionService.extract(
        extracted.extracted_text
    )

    FinancialDataService.create(
        db,
        report_id,
        data,
    )

    return {
        "message": "Financial data extracted successfully.",
        "report_id": report_id,
        "financial_data": data,
    }