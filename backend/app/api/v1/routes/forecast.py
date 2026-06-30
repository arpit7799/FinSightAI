# app/api/v1/routes/forecast.py
"""
API routes for the Forecasting Engine.

Endpoints:
    POST /forecast/{filing_id}/run        - Run forecasting for all metrics
    GET  /forecast/{filing_id}             - Get all forecasts for a filing
    GET  /forecast/{filing_id}/{metric}    - Get forecast for one metric
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.domain.models.enums import ForecastMetric
from app.services.forecast_service import ForecastService
from app.repositories.forecast_repository import ForecastRepository

router = APIRouter(prefix="/forecast", tags=["Forecasting"])


@router.post("/{filing_id}/run")
def run_forecast(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN", "ANALYST")),
):
    """
    Run forecasting for Revenue, Net Profit, EBITDA, and Operating Cash Flow.

    Uses ALL filings uploaded for this company to build the historical
    time series — not just this single filing.

    If only 1 year of data exists, returns a simple growth projection
    clearly labeled with a warning. Upload more years for real ML forecasts.
    """
    service = ForecastService(db)
    return service.run_forecast(filing_id)


@router.get("/{filing_id}")
def get_forecasts(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all forecasts (all metrics, all models) for a filing."""
    forecasts = ForecastRepository(db).get_by_filing_id(filing_id)

    if not forecasts:
        from app.services.forecast_service import ForecastService
        service = ForecastService(db)
        return service.run_forecast(filing_id)

    grouped = {}
    for f in forecasts:
        metric = f.metric_name.value
        if metric not in grouped:
            grouped[metric] = []
        grouped[metric].append({
            "model": f.model_used.value,
            "historical_data": f.historical_data,
            "forecast_data": f.forecast_data,
            "trend_direction": f.trend_direction,
            "growth_rate_pct": float(f.growth_rate_pct) if f.growth_rate_pct else None,
            "mae": float(f.mae) if f.mae else None,
            "is_simple_projection": (f.model_params or {}).get("is_simple_projection", False),
        })

    return {"filing_id": filing_id, "forecasts": grouped}


@router.get("/{filing_id}/{metric}")
def get_metric_forecast(
    filing_id: str,
    metric: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get forecast for a single metric.
    metric: REVENUE, NET_PROFIT, EBITDA, or OPERATING_CASH_FLOW
    """
    try:
        metric_enum = ForecastMetric(metric.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric. Must be one of: REVENUE, NET_PROFIT, EBITDA, OPERATING_CASH_FLOW",
        )

    forecasts = ForecastRepository(db).get_by_metric(filing_id, metric_enum)

    if not forecasts:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast found for {metric}. Run /forecast/{filing_id}/run first.",
        )

    return [
        {
            "model": f.model_used.value,
            "historical_data": f.historical_data,
            "forecast_data": f.forecast_data,
            "trend_direction": f.trend_direction,
            "growth_rate_pct": float(f.growth_rate_pct) if f.growth_rate_pct else None,
            "mae": float(f.mae) if f.mae else None,
        }
        for f in forecasts
    ]