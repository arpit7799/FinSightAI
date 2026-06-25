# app/api/v1/routes/analysis.py
"""
API routes for Financial Analysis Engine.

Endpoints:
    POST  /analysis/{filing_id}/run       - Run ratio analysis
    GET   /analysis/{filing_id}/ratios    - Get all computed ratios
    GET   /analysis/{filing_id}/ratios/{category} - Get ratios by category
    GET   /analysis/company/{company_id}/trends   - Multi-year trend analysis
    GET   /analysis/{filing_id}/summary   - KPI summary for dashboard
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.services.analysis_service import AnalysisService
from app.domain.models.enums import RatioCategory

router = APIRouter(prefix="/analysis", tags=["Financial Analysis"])


@router.post("/{filing_id}/run")
def run_analysis(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN", "ANALYST")),
):
    """
    Trigger ratio analysis for a filing.
    The filing must already be in COMPLETE status (processed by Phase 4).
    """
    service = AnalysisService(db)
    ratios = service.run_ratio_analysis(filing_id)

    return {
        "message": "Analysis complete",
        "filing_id": filing_id,
        "ratios_computed": len(ratios),
    }


@router.get("/{filing_id}/ratios")
def get_ratios(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all 18 computed financial ratios for a filing."""
    service = AnalysisService(db)
    ratios = service.get_ratios(filing_id)

    # Group by category for easier frontend consumption
    grouped = {}
    for r in ratios:
        cat = r.ratio_category.value
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append({
            "ratio_name": r.ratio_name,
            "formula": r.formula,
            "computed_value": float(r.computed_value) if r.computed_value else None,
            "benchmark_value": float(r.benchmark_value) if r.benchmark_value else None,
            "benchmark_source": r.benchmark_source,
            "signal": r.signal.value,
            "interpretation": r.interpretation,
        })

    return {
        "filing_id": filing_id,
        "ratios": grouped,
        "total": len(ratios),
    }


@router.get("/{filing_id}/ratios/{category}")
def get_ratios_by_category(
    filing_id: str,
    category: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get ratios for a specific category: LIQUIDITY, PROFITABILITY, LEVERAGE, EFFICIENCY, MARKET"""
    try:
        ratio_category = RatioCategory(category.upper())
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    from app.repositories.ratio_repository import RatioRepository
    ratios = RatioRepository(db).get_by_category(filing_id, ratio_category)

    return [
        {
            "ratio_name": r.ratio_name,
            "formula": r.formula,
            "computed_value": float(r.computed_value) if r.computed_value else None,
            "benchmark_value": float(r.benchmark_value) if r.benchmark_value else None,
            "signal": r.signal.value,
            "interpretation": r.interpretation,
        }
        for r in ratios
    ]


@router.get("/company/{company_id}/trends")
def get_trends(
    company_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get multi-year trend analysis for all ratios of a company."""
    service = AnalysisService(db)
    return service.get_trend_analysis(company_id)


@router.get("/{filing_id}/summary")
def get_summary(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get a KPI summary for the dashboard.
    Returns key ratios with signal counts — good for the overview cards.
    """
    from app.repositories.ratio_repository import RatioRepository
    ratios = RatioRepository(db).get_by_filing_id(filing_id)

    if not ratios:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No ratios found. Run analysis first.")

    # Count signals
    signal_counts = {"GOOD": 0, "WARNING": 0, "CRITICAL": 0, "NEUTRAL": 0}
    key_metrics = {}

    for r in ratios:
        signal_counts[r.signal.value] += 1

        # Pull out the most important KPIs for the summary cards
        if r.ratio_name in ["Current Ratio", "Return on Equity", "Net Profit Margin",
                             "Debt to Equity", "Interest Coverage", "Asset Turnover"]:
            key_metrics[r.ratio_name] = {
                "value": float(r.computed_value) if r.computed_value else None,
                "signal": r.signal.value,
            }

    # Overall health score: (GOOD * 1 + WARNING * 0.5 + CRITICAL * 0) / total
    total = len([r for r in ratios if r.signal.value != "NEUTRAL"])
    health_score = 0
    if total > 0:
        health_score = round(
            (signal_counts["GOOD"] * 1.0 + signal_counts["WARNING"] * 0.5) / total * 100
        )

    return {
        "filing_id": filing_id,
        "health_score": health_score,
        "signal_counts": signal_counts,
        "key_metrics": key_metrics,
        "total_ratios": len(ratios),
    }