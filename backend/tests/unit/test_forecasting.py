# tests/unit/test_forecasting.py
"""
Unit tests for the Forecasting Engine.
No database, Prophet, or ARIMA model fitting needed for most tests —
those are tested separately with real small datasets.
"""

import pytest
from app.engines.forecasting.data_builder import (
    build_historical_series,
    has_enough_data_for_real_forecast,
)
from app.engines.forecasting.simple_projector import project_simple_growth
from app.engines.forecasting.trend_summarizer import summarize_trend


# ── Data Builder Tests ────────────────────────────────────────────────────────

class TestDataBuilder:

    def test_builds_series_from_filings(self):
        filings = [
            {"fiscal_year": 2021, "normalized_data": {"total_revenue": 1_000_000}},
            {"fiscal_year": 2022, "normalized_data": {"total_revenue": 1_200_000}},
            {"fiscal_year": 2023, "normalized_data": {"total_revenue": 1_400_000}},
        ]
        series = build_historical_series(filings, "REVENUE")
        assert len(series) == 3
        assert series[0]["year"] == 2021
        assert series[0]["value"] == 1_000_000

    def test_series_sorted_ascending(self):
        filings = [
            {"fiscal_year": 2023, "normalized_data": {"total_revenue": 1_400_000}},
            {"fiscal_year": 2021, "normalized_data": {"total_revenue": 1_000_000}},
            {"fiscal_year": 2022, "normalized_data": {"total_revenue": 1_200_000}},
        ]
        series = build_historical_series(filings, "REVENUE")
        years = [s["year"] for s in series]
        assert years == [2021, 2022, 2023]

    def test_skips_filings_without_metric(self):
        filings = [
            {"fiscal_year": 2021, "normalized_data": {"total_revenue": 1_000_000}},
            {"fiscal_year": 2022, "normalized_data": {}},  # missing revenue
        ]
        series = build_historical_series(filings, "REVENUE")
        assert len(series) == 1

    def test_invalid_metric_returns_empty(self):
        filings = [{"fiscal_year": 2021, "normalized_data": {"total_revenue": 1_000_000}}]
        series = build_historical_series(filings, "INVALID_METRIC")
        assert series == []

    def test_maps_net_profit_correctly(self):
        filings = [{"fiscal_year": 2021, "normalized_data": {"net_income": 500_000}}]
        series = build_historical_series(filings, "NET_PROFIT")
        assert series[0]["value"] == 500_000

    def test_has_enough_data_true_for_3_points(self):
        series = [{"year": y, "value": 100} for y in [2021, 2022, 2023]]
        assert has_enough_data_for_real_forecast(series) is True

    def test_has_enough_data_false_for_2_points(self):
        series = [{"year": y, "value": 100} for y in [2022, 2023]]
        assert has_enough_data_for_real_forecast(series) is False

    def test_has_enough_data_false_for_1_point(self):
        series = [{"year": 2023, "value": 100}]
        assert has_enough_data_for_real_forecast(series) is False


# ── Simple Projector Tests ────────────────────────────────────────────────────

class TestSimpleProjector:

    def test_returns_3_years_by_default(self):
        series = [{"year": 2023, "value": 1_000_000}]
        result = project_simple_growth(series)
        assert len(result["forecast_data"]) == 3

    def test_single_point_uses_default_growth(self):
        series = [{"year": 2023, "value": 1_000_000}]
        result = project_simple_growth(series)
        assert result["growth_rate_used"] == 0.08
        assert result["confidence"] == "LOW"

    def test_two_points_uses_actual_growth(self):
        series = [
            {"year": 2022, "value": 1_000_000},
            {"year": 2023, "value": 1_100_000},  # 10% growth
        ]
        result = project_simple_growth(series)
        assert abs(result["growth_rate_used"] - 0.10) < 0.001
        assert result["confidence"] == "MEDIUM"

    def test_forecast_values_increase_with_positive_growth(self):
        series = [{"year": 2023, "value": 1_000_000}]
        result = project_simple_growth(series)
        values = [f["yhat"] for f in result["forecast_data"]]
        assert values[0] < values[1] < values[2]  # increasing trend

    def test_forecast_years_are_sequential(self):
        series = [{"year": 2023, "value": 1_000_000}]
        result = project_simple_growth(series, forecast_years=3)
        years = [f["ds"][:4] for f in result["forecast_data"]]
        assert years == ["2024", "2025", "2026"]

    def test_confidence_interval_widens_over_time(self):
        series = [{"year": 2023, "value": 1_000_000}]
        result = project_simple_growth(series)
        spreads = [
            f["yhat_upper"] - f["yhat_lower"]
            for f in result["forecast_data"]
        ]
        # Each subsequent year's interval should be wider
        assert spreads[0] < spreads[1] < spreads[2]

    def test_empty_series_returns_insufficient_data(self):
        result = project_simple_growth([])
        assert result["method"] == "insufficient_data"
        assert result["forecast_data"] == []

    def test_extreme_growth_is_clamped(self):
        # A 500% growth jump should be clamped to max 50%
        series = [
            {"year": 2022, "value": 100_000},
            {"year": 2023, "value": 600_000},  # 500% growth
        ]
        result = project_simple_growth(series)
        assert result["growth_rate_used"] <= 0.50

    def test_extreme_decline_is_clamped(self):
        series = [
            {"year": 2022, "value": 1_000_000},
            {"year": 2023, "value": 100_000},  # -90% decline
        ]
        result = project_simple_growth(series)
        assert result["growth_rate_used"] >= -0.30


# ── Trend Summarizer Tests ────────────────────────────────────────────────────

class TestTrendSummarizer:

    def test_upward_trend_detected(self):
        historical = [{"year": 2023, "value": 1_000_000}]
        forecast = [
            {"yhat": 1_100_000}, {"yhat": 1_200_000}, {"yhat": 1_300_000}
        ]
        result = summarize_trend(historical, forecast)
        assert result["trend_direction"] == "UPWARD"

    def test_downward_trend_detected(self):
        historical = [{"year": 2023, "value": 1_000_000}]
        forecast = [
            {"yhat": 900_000}, {"yhat": 800_000}, {"yhat": 700_000}
        ]
        result = summarize_trend(historical, forecast)
        assert result["trend_direction"] == "DOWNWARD"

    def test_stable_trend_detected(self):
        historical = [{"year": 2023, "value": 1_000_000}]
        forecast = [
            {"yhat": 1_005_000}, {"yhat": 1_010_000}, {"yhat": 1_015_000}
        ]
        result = summarize_trend(historical, forecast)
        assert result["trend_direction"] == "STABLE"

    def test_empty_data_returns_insufficient(self):
        result = summarize_trend([], [])
        assert result["trend_direction"] == "INSUFFICIENT_DATA"
        assert result["growth_rate_pct"] is None

    def test_zero_historical_value_handled(self):
        historical = [{"year": 2023, "value": 0}]
        forecast = [{"yhat": 100_000}]
        result = summarize_trend(historical, forecast)
        assert result["trend_direction"] == "INSUFFICIENT_DATA"

    def test_growth_rate_is_percentage(self):
        historical = [{"year": 2023, "value": 1_000_000}]
        forecast = [{"yhat": 1_100_000}, {"yhat": 1_200_000}, {"yhat": 1_331_000}]
        result = summarize_trend(historical, forecast)
        assert result["growth_rate_pct"] is not None
        assert isinstance(result["growth_rate_pct"], float)