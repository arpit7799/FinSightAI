# app/services/forecast_service.py
"""
Orchestrates the forecasting pipeline.

For each metric (Revenue, Net Profit, EBITDA, Operating Cash Flow):
1. Build historical time series across all filings for the company
2. If 3+ data points: run Prophet AND ARIMA
3. If <3 data points: use simple growth projection (clearly labeled)
4. Save results to DB
"""

import structlog
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.domain.models.forecast import Forecast
from app.domain.models.enums import ForecastMetric, ForecastModel
from app.engines.forecasting.data_builder import (
    build_historical_series,
    has_enough_data_for_real_forecast,
)
from app.engines.forecasting.prophet_forecaster import forecast_with_prophet
from app.engines.forecasting.arima_forecaster import forecast_with_arima
from app.engines.forecasting.simple_projector import project_simple_growth
from app.engines.forecasting.trend_summarizer import summarize_trend
from app.repositories.filing_repository import FilingRepository
from app.repositories.statement_repository import StatementRepository
from app.repositories.forecast_repository import ForecastRepository

logger = structlog.get_logger()

FORECAST_METRICS = ["REVENUE", "NET_PROFIT", "EBITDA", "OPERATING_CASH_FLOW"]
FORECAST_YEARS = 3


class ForecastService:

    def __init__(self, db: Session):
        self.db = db
        self.filing_repo = FilingRepository(db)
        self.statement_repo = StatementRepository(db)
        self.forecast_repo = ForecastRepository(db)

    def run_forecast(self, filing_id: str) -> dict:
        """
        Run forecasting for all 4 metrics for the company this filing belongs to.
        Uses ALL filings for the company (not just this one) to build the time series.
        """
        filing = self.filing_repo.get_by_id(filing_id)
        if not filing:
            raise HTTPException(status_code=404, detail="Filing not found")

        # Get all filings for this company, sorted by fiscal year
        company_filings = self.filing_repo.get_all_for_company(str(filing.company_id))

        if not company_filings:
            raise HTTPException(status_code=404, detail="No filings found for company")

        # Build {fiscal_year, normalized_data} for each filing
        filings_with_data = []
        for f in sorted(company_filings, key=lambda x: x.fiscal_year):
            normalized = self.statement_repo.get_normalized_data(str(f.id))
            if normalized:
                filings_with_data.append({
                    "fiscal_year": f.fiscal_year,
                    "normalized_data": normalized,
                })

        if not filings_with_data:
            raise HTTPException(
                status_code=422,
                detail="No financial data found. Run document processing first.",
            )

        logger.info(
            "forecast_started",
            filing_id=filing_id,
            company_id=str(filing.company_id),
            years_available=len(filings_with_data),
        )

        results = {}

        for metric in FORECAST_METRICS:
            metric_result = self._forecast_single_metric(
                filing_id=filing_id,
                metric=metric,
                filings_with_data=filings_with_data,
            )
            results[metric] = metric_result

        logger.info("forecast_complete", filing_id=filing_id, metrics=list(results.keys()))

        return {
            "filing_id": filing_id,
            "years_of_data_used": len(filings_with_data),
            "forecasts": results,
        }

    def _forecast_single_metric(
        self,
        filing_id: str,
        metric: str,
        filings_with_data: list[dict],
    ) -> dict:
        """Run forecasting for one metric (e.g. REVENUE) and save results."""

        series = build_historical_series(filings_with_data, metric)

        if not series:
            return {
                "status": "no_data",
                "message": f"No {metric} data found across available filings",
            }

        enough_data = has_enough_data_for_real_forecast(series)

        if enough_data:
            # Run BOTH Prophet and ARIMA, save both
            results_saved = []

            try:
                prophet_result = forecast_with_prophet(series, FORECAST_YEARS)
                self._save_forecast(
                    filing_id, metric, "PROPHET", series, prophet_result
                )
                results_saved.append("PROPHET")
            except Exception as e:
                logger.warning("prophet_failed", metric=metric, error=str(e))
                prophet_result = None

            try:
                arima_result = forecast_with_arima(series, FORECAST_YEARS)
                self._save_forecast(
                    filing_id, metric, "ARIMA", series, arima_result
                )
                results_saved.append("ARIMA")
            except Exception as e:
                logger.warning("arima_failed", metric=metric, error=str(e))
                arima_result = None

            primary_result = prophet_result or arima_result

            if not primary_result:
                return {"status": "failed", "message": "Both Prophet and ARIMA failed"}

            trend = summarize_trend(series, primary_result["forecast_data"])

            return {
                "status": "success",
                "method": "ml_forecast",
                "models_used": results_saved,
                "historical_data": series,
                "forecast_data": primary_result["forecast_data"],
                "trend_direction": trend["trend_direction"],
                "growth_rate_pct": trend["growth_rate_pct"],
                "confidence": "HIGH" if len(series) >= 4 else "MEDIUM",
            }

        else:
            # Not enough data for real ML — use simple projection
            simple_result = project_simple_growth(series, FORECAST_YEARS)

            self._save_forecast(
                filing_id, metric, "PROPHET",  # we label it PROPHET slot but mark method as simple
                series, simple_result,
                is_simple=True,
            )

            trend = summarize_trend(series, simple_result["forecast_data"])

            return {
                "status": "success",
                "method": "simple_projection",
                "warning": (
                    f"Only {len(series)} year(s) of data available. "
                    "This is a rough growth-rate estimate, not a true ML forecast. "
                    "Upload more years of filings for accurate Prophet/ARIMA predictions."
                ),
                "historical_data": series,
                "forecast_data": simple_result["forecast_data"],
                "growth_rate_used": simple_result["growth_rate_used"],
                "trend_direction": trend["trend_direction"],
                "growth_rate_pct": trend["growth_rate_pct"],
                "confidence": simple_result["confidence"],
            }

    def _save_forecast(
        self,
        filing_id: str,
        metric: str,
        model_used: str,
        series: list[dict],
        result: dict,
        is_simple: bool = False,
    ) -> None:
        """Save a forecast result to the database."""

        trend = summarize_trend(series, result["forecast_data"])

        forecast = Forecast(
            filing_id=filing_id,
            metric_name=ForecastMetric(metric),
            model_used=ForecastModel(model_used),
            historical_data=series,
            data_points_count=len(series),
            forecast_data=result["forecast_data"],
            forecast_years=FORECAST_YEARS,
            model_params={"is_simple_projection": is_simple, "method": result.get("method")},
            mae=result.get("mae"),
            mape=None,  # could compute if needed
            trend_direction=trend["trend_direction"],
            growth_rate_pct=trend["growth_rate_pct"],
        )

        self.forecast_repo.save(forecast)

    def get_forecasts(self, filing_id: str) -> list[Forecast]:
        """Get existing forecasts, or run if not yet done."""
        forecasts = self.forecast_repo.get_by_filing_id(filing_id)
        if not forecasts:
            self.run_forecast(filing_id)
            forecasts = self.forecast_repo.get_by_filing_id(filing_id)
        return forecasts