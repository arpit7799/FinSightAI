# app/services/analysis_service.py
"""
Business logic for the Financial Analysis Engine.

This service:
1. Fetches normalized financial data from the database
2. Runs the ratio calculator
3. Saves ratio results back to the database
4. Runs trend analysis across multiple filings
"""

import structlog
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.domain.models.financial_ratio import FinancialRatio
from app.domain.models.enums import ProcessingStatus
from app.engines.financial.ratio_calculator import RatioCalculator
from app.engines.financial.trend_analyzer import analyze_trends
from app.repositories.filing_repository import FilingRepository
from app.repositories.statement_repository import StatementRepository
from app.repositories.ratio_repository import RatioRepository

logger = structlog.get_logger()


class AnalysisService:

    def __init__(self, db: Session):
        self.db = db
        self.filing_repo = FilingRepository(db)
        self.statement_repo = StatementRepository(db)
        self.ratio_repo = RatioRepository(db)

    def run_ratio_analysis(self, filing_id: str) -> list[FinancialRatio]:
        """
        Run the full ratio analysis for a filing.

        Steps:
        1. Load normalized financial data from DB
        2. Run RatioCalculator
        3. Convert results to FinancialRatio model objects
        4. Save to DB
        5. Return saved ratios
        """
        # Check filing exists
        filing = self.filing_repo.get_by_id(filing_id)
        if not filing:
            raise HTTPException(status_code=404, detail="Filing not found")

        # Get merged financial data from all statements
        normalized_data = self.statement_repo.get_normalized_data(filing_id)

        if not normalized_data:
            raise HTTPException(
                status_code=422,
                detail="No financial data found. Make sure the filing has been processed first.",
            )

        logger.info("ratio_analysis_started", filing_id=filing_id,
                   data_keys=list(normalized_data.keys()))

        # Run the calculator
        calculator = RatioCalculator(normalized_data)
        ratio_dicts = calculator.calculate_all()

        # Convert to model objects
        ratio_objects = [
            FinancialRatio(
                filing_id=filing_id,
                ratio_category=r["ratio_category"],
                ratio_name=r["ratio_name"],
                formula=r["formula"],
                computed_value=r["computed_value"],
                benchmark_value=r["benchmark_value"],
                benchmark_source=r["benchmark_source"],
                signal=r["signal"],
                interpretation=r["interpretation"],
            )
            for r in ratio_dicts
        ]

        # Save to DB
        self.ratio_repo.save_ratios(ratio_objects)

        logger.info("ratio_analysis_complete", filing_id=filing_id,
                   ratios_computed=len(ratio_objects))

        return ratio_objects

    def get_ratios(self, filing_id: str) -> list[FinancialRatio]:
        """Get existing ratios for a filing. Runs analysis if not yet done."""
        ratios = self.ratio_repo.get_by_filing_id(filing_id)

        if not ratios:
            # Auto-run analysis if not done yet
            ratios = self.run_ratio_analysis(filing_id)

        return ratios

    def get_trend_analysis(self, company_id: str) -> dict:
        """
        Get trend analysis across all filings for a company.
        Requires at least 2 filings (years) to show trends.
        """
        filings = self.filing_repo.get_all_for_company(company_id)

        if len(filings) < 2:
            return {
                "message": "At least 2 years of filings needed for trend analysis",
                "filings_found": len(filings),
                "trends": {},
            }

        # Build yearly ratio data
        yearly_ratios = []
        for filing in filings:
            ratios = self.ratio_repo.get_by_filing_id(str(filing.id))
            if ratios:
                yearly_ratios.append({
                    "fiscal_year": filing.fiscal_year,
                    "ratios": [
                        {"ratio_name": r.ratio_name, "computed_value": float(r.computed_value) if r.computed_value else None}
                        for r in ratios
                    ],
                })

        trends = analyze_trends(yearly_ratios)

        return {
            "company_id": company_id,
            "years_analyzed": len(yearly_ratios),
            "trends": trends,
        }