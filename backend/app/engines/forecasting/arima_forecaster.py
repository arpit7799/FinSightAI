# app/engines/forecasting/arima_forecaster.py
"""
ARIMA-based forecasting using statsmodels.

ARIMA (AutoRegressive Integrated Moving Average) is a classic
time-series model. We use it as a secondary/comparison forecast
alongside Prophet.

For small datasets (annual financial data, typically 3-5 points),
we use a simple ARIMA(1,1,0) order — higher orders need more data
than we typically have.
"""

import warnings
import numpy as np
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore")  # statsmodels is noisy with small datasets


def forecast_with_arima(series: list[dict], forecast_years: int = 3) -> dict:
    """
    Run ARIMA forecast on a historical time series.

    Args:
        series: [{"year": 2021, "value": 1800000000}, ...] sorted ascending
        forecast_years: years to forecast into the future

    Returns:
        {
            "forecast_data": [...],
            "mae": float or None,
            "method": "arima",
        }
    """
    values = [point["value"] for point in series]
    last_year = series[-1]["year"]

    # ARIMA(1,1,0): 1 autoregressive term, 1 differencing, 0 moving average
    # Simple order chosen because we typically have very few data points
    model = ARIMA(values, order=(1, 1, 0))
    fitted = model.fit()

    # Forecast with confidence intervals
    forecast_result = fitted.get_forecast(steps=forecast_years)
    predicted_mean = forecast_result.predicted_mean
    conf_int = forecast_result.conf_int(alpha=0.20)  # 80% confidence interval

    forecast_data = []
    for i in range(forecast_years):
        forecast_year = last_year + i + 1
        forecast_data.append({
            "ds": f"{forecast_year}-03-31",
            "yhat": round(float(predicted_mean[i]), 2),
            "yhat_lower": round(float(conf_int[i][0]), 2),
            "yhat_upper": round(float(conf_int[i][1]), 2),
        })

    # In-sample MAE from fitted values
    mae = None
    try:
        fitted_values = fitted.fittedvalues
        # ARIMA with differencing skips the first value
        actual_compare = values[-len(fitted_values):]
        errors = [abs(a - f) for a, f in zip(actual_compare, fitted_values)]
        if errors:
            mae = round(sum(errors) / len(errors), 2)
    except Exception:
        mae = None

    return {
        "forecast_data": forecast_data,
        "mae": mae,
        "method": "arima",
    }