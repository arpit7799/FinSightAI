# app/engines/forecasting/simple_projector.py
"""
Simple growth-rate projection for when we don't have enough
historical data to run Prophet or ARIMA.

This is NOT a real time-series model — it's a transparent,
honest fallback. We clearly label this in the API response
so users know it's a rough estimate, not an ML forecast.

Logic:
  - 1 data point: assume a conservative 8% YoY growth (industry average)
  - 2 data points: use the actual YoY growth rate observed
"""

DEFAULT_GROWTH_RATE = 0.08  # 8% — conservative industry average assumption


def project_simple_growth(series: list[dict], forecast_years: int = 3) -> dict:
    """
    Generate a simple growth-based projection.

    Args:
        series: [{"year": 2023, "value": 1250000000}]
        forecast_years: how many years to project forward

    Returns:
        {
            "forecast_data": [...],
            "growth_rate_used": 0.08,
            "method": "simple_growth_projection",
            "confidence": "LOW",
        }
    """
    if not series:
        return {
            "forecast_data": [],
            "growth_rate_used": None,
            "method": "insufficient_data",
            "confidence": "NONE",
        }

    last_year = series[-1]["year"]
    last_value = series[-1]["value"]

    # Determine growth rate
    if len(series) >= 2:
        prior_value = series[-2]["value"]
        if prior_value and prior_value != 0:
            growth_rate = (last_value - prior_value) / prior_value
        else:
            growth_rate = DEFAULT_GROWTH_RATE
        confidence = "MEDIUM"
    else:
        growth_rate = DEFAULT_GROWTH_RATE
        confidence = "LOW"

    # Clamp growth rate to a sane range (-30% to +50%) to avoid wild projections
    growth_rate = max(-0.30, min(0.50, growth_rate))

    forecast_data = []
    current_value = last_value

    for i in range(1, forecast_years + 1):
        current_value = current_value * (1 + growth_rate)
        forecast_year = last_year + i

        # Simple uncertainty band: widens each year
        uncertainty = 0.10 + (i * 0.05)  # 15%, 20%, 25%...

        forecast_data.append({
            "ds": f"{forecast_year}-03-31",
            "yhat": round(current_value, 2),
            "yhat_lower": round(current_value * (1 - uncertainty), 2),
            "yhat_upper": round(current_value * (1 + uncertainty), 2),
        })

    return {
        "forecast_data": forecast_data,
        "growth_rate_used": round(growth_rate, 4),
        "method": "simple_growth_projection",
        "confidence": confidence,
    }