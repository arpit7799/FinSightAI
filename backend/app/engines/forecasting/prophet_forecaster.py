# app/engines/forecasting/prophet_forecaster.py
"""
Prophet-based forecasting.

Prophet (by Meta) handles trend and seasonality automatically,
and is robust to missing data — ideal for annual financial data
which often has gaps.

We use yearly data points (not daily/monthly) since that's what
annual reports provide.
"""

import pandas as pd
from prophet import Prophet
import logging

# Suppress Prophet's verbose cmdstanpy logs
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)


def forecast_with_prophet(series: list[dict], forecast_years: int = 3) -> dict:
    """
    Run Prophet forecast on a historical time series.

    Args:
        series: [{"year": 2021, "value": 1800000000}, ...] sorted ascending
        forecast_years: years to forecast into the future

    Returns:
        {
            "forecast_data": [{"ds": "2024-03-31", "yhat": ..., "yhat_lower": ..., "yhat_upper": ...}],
            "mae": float or None,
            "method": "prophet",
        }
    """
    # Build Prophet's required dataframe format: columns "ds" and "y"
    df = pd.DataFrame([
        {"ds": pd.Timestamp(year=point["year"], month=3, day=31), "y": point["value"]}
        for point in series
    ])

    # Prophet needs at least 2 rows, but works best with 3+
    model = Prophet(
        yearly_seasonality=False,   # we only have 1 data point per year
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.80,        # 80% confidence interval
    )

    model.fit(df)

    # Build future dataframe — yearly intervals
    future = model.make_future_dataframe(periods=forecast_years, freq="YE")
    forecast = model.predict(future)

    # Only keep the future predictions (not historical fit)
    future_only = forecast[forecast["ds"] > df["ds"].max()]

    forecast_data = [
        {
            "ds": row["ds"].strftime("%Y-%m-%d"),
            "yhat": round(float(row["yhat"]), 2),
            "yhat_lower": round(float(row["yhat_lower"]), 2),
            "yhat_upper": round(float(row["yhat_upper"]), 2),
        }
        for _, row in future_only.iterrows()
    ]

    # Compute MAE on historical fit (in-sample error, rough quality indicator)
    historical_fit = forecast[forecast["ds"] <= df["ds"].max()]
    mae = None
    if len(historical_fit) == len(df):
        errors = [
            abs(actual - predicted)
            for actual, predicted in zip(df["y"], historical_fit["yhat"])
        ]
        mae = round(sum(errors) / len(errors), 2)

    return {
        "forecast_data": forecast_data,
        "mae": mae,
        "method": "prophet",
    }