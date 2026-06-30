# app/engines/forecasting/trend_summarizer.py
"""
Computes trend direction and growth rate summary
from forecast output — used for the dashboard summary cards.
"""


def summarize_trend(historical_data: list[dict], forecast_data: list[dict]) -> dict:
    """
    Compute trend direction and CAGR from historical + forecast data.

    Returns:
        {
            "trend_direction": "UPWARD" | "DOWNWARD" | "STABLE",
            "growth_rate_pct": 12.5,  # projected CAGR over forecast period
        }
    """
    if not historical_data or not forecast_data:
        return {"trend_direction": "INSUFFICIENT_DATA", "growth_rate_pct": None}

    last_historical = historical_data[-1]["value"]
    last_forecast = forecast_data[-1]["yhat"]

    if last_historical == 0:
        return {"trend_direction": "INSUFFICIENT_DATA", "growth_rate_pct": None}

    num_years = len(forecast_data)

    # CAGR = (End/Start)^(1/years) - 1
    if last_historical > 0 and last_forecast > 0:
        cagr = ((last_forecast / last_historical) ** (1 / num_years)) - 1
    else:
        cagr = (last_forecast - last_historical) / abs(last_historical)

    growth_pct = round(cagr * 100, 2)

    if growth_pct > 3:
        direction = "UPWARD"
    elif growth_pct < -3:
        direction = "DOWNWARD"
    else:
        direction = "STABLE"

    return {
        "trend_direction": direction,
        "growth_rate_pct": growth_pct,
    }