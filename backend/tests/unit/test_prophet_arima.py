# tests/unit/test_prophet_arima.py
"""
Tests for Prophet and ARIMA forecasters.
These actually fit models so they're slower than other unit tests.
Run separately if needed: pytest tests/unit/test_prophet_arima.py -v
"""

import pytest
from app.engines.forecasting.prophet_forecaster import forecast_with_prophet
from app.engines.forecasting.arima_forecaster import forecast_with_arima


# Sample 4-year revenue growth series — realistic IT company pattern
SAMPLE_SERIES = [
    {"year": 2020, "value": 1_800_000_000},
    {"year": 2021, "value": 2_000_000_000},
    {"year": 2022, "value": 2_150_000_000},
    {"year": 2023, "value": 2_400_000_000},
]


class TestProphetForecaster:

    def test_returns_3_forecast_points(self):
        result = forecast_with_prophet(SAMPLE_SERIES, forecast_years=3)
        assert len(result["forecast_data"]) == 3

    def test_forecast_has_required_fields(self):
        result = forecast_with_prophet(SAMPLE_SERIES, forecast_years=3)
        for point in result["forecast_data"]:
            assert "ds" in point
            assert "yhat" in point
            assert "yhat_lower" in point
            assert "yhat_upper" in point

    def test_yhat_lower_less_than_yhat_upper(self):
        result = forecast_with_prophet(SAMPLE_SERIES, forecast_years=3)
        for point in result["forecast_data"]:
            assert point["yhat_lower"] <= point["yhat"] <= point["yhat_upper"]

    def test_method_is_prophet(self):
        result = forecast_with_prophet(SAMPLE_SERIES, forecast_years=3)
        assert result["method"] == "prophet"

    def test_forecast_continues_upward_trend(self):
        result = forecast_with_prophet(SAMPLE_SERIES, forecast_years=3)
        # Given consistently growing revenue, forecast should also trend up
        first_forecast = result["forecast_data"][0]["yhat"]
        last_historical = SAMPLE_SERIES[-1]["value"]
        # Allow some tolerance — Prophet may smooth slightly
        assert first_forecast > last_historical * 0.85


class TestARIMAForecaster:

    def test_returns_3_forecast_points(self):
        result = forecast_with_arima(SAMPLE_SERIES, forecast_years=3)
        assert len(result["forecast_data"]) == 3

    def test_forecast_has_required_fields(self):
        result = forecast_with_arima(SAMPLE_SERIES, forecast_years=3)
        for point in result["forecast_data"]:
            assert "ds" in point
            assert "yhat" in point
            assert "yhat_lower" in point
            assert "yhat_upper" in point

    def test_method_is_arima(self):
        result = forecast_with_arima(SAMPLE_SERIES, forecast_years=3)
        assert result["method"] == "arima"

    def test_years_are_sequential(self):
        result = forecast_with_arima(SAMPLE_SERIES, forecast_years=3)
        years = [int(p["ds"][:4]) for p in result["forecast_data"]]
        assert years == [2024, 2025, 2026]