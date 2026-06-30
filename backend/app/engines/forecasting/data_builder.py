# app/engines/forecasting/data_builder.py
"""
Builds historical time-series data for forecasting.

Pulls financial values across all filings for a company,
sorted by fiscal year, ready to feed into Prophet/ARIMA.
"""

# Maps our forecast metrics to normalized_data keys (from Phase 4)
METRIC_KEY_MAP = {
    "REVENUE":              "total_revenue",
    "NET_PROFIT":            "net_income",
    "EBITDA":                "ebitda",
    "OPERATING_CASH_FLOW":   "operating_cash_flow",
}


def build_historical_series(filings_with_data: list[dict], metric: str) -> list[dict]:
    """
    Build a historical data series for one metric across multiple filings.

    Args:
        filings_with_data: list of {"fiscal_year": 2023, "normalized_data": {...}}
                            sorted oldest to newest
        metric: one of REVENUE, NET_PROFIT, EBITDA, OPERATING_CASH_FLOW

    Returns:
        [{"year": 2021, "value": 1800000000}, {"year": 2022, "value": 2000000000}, ...]
        Only includes years where the value was actually found.
    """
    key = METRIC_KEY_MAP.get(metric)
    if not key:
        return []

    series = []
    for filing in filings_with_data:
        value = filing["normalized_data"].get(key)
        if value is not None:
            series.append({
                "year": filing["fiscal_year"],
                "value": float(value),
            })

    # Sort by year ascending — required for time series models
    series.sort(key=lambda x: x["year"])

    return series


def has_enough_data_for_real_forecast(series: list[dict]) -> bool:
    """
    Prophet/ARIMA need at least 3 data points to produce a meaningful trend.
    Below that, we fall back to simple growth projection.
    """
    return len(series) >= 3