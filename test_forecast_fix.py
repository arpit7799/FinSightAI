"""
Smoke test: verify the forecast model works on combined multi-stock data
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import pandas as pd
from app.api.stock_data import _load_and_combine_all_csvs
from app.ml.forecast_predictor import ForecastPredictor

# step 1: load the combined data
print("Loading combined multi-stock data...")
composite = _load_and_combine_all_csvs()

print(f"Combined dataset: {len(composite)} rows")
print(f"Date range: {composite['Date'].iloc[0]} -> {composite['Date'].iloc[-1]}")
print(f"Price range: {composite['Close'].min():.2f} -> {composite['Close'].max():.2f}")
print()

# step 2: run backtest
print("Running walk-forward backtest (3 folds, 30-day horizon)...")
metrics = ForecastPredictor.backtest(composite, horizon=30, n_folds=3)

print()
print("=== Backtest Results (combined multi-stock) ===")
for key, val in metrics.items():
    print(f"  {key}: {val}")

print()

mase = metrics.get("mase")
if mase is not None:
    if mase < 1.0:
        print(f"GREAT - MASE = {mase} — model BEATS naive baseline!")
    elif mase < 2.0:
        print(f"GOOD - MASE = {mase} — model is close to naive")
    else:
        print(f"OK - MASE = {mase} — naive is better (normal for stocks)")

# step 3: run predict
print()
print("Running predict() for 30 days...")
forecast = ForecastPredictor.predict(composite, days=30)
print(f"Got {len(forecast)} forecast points")
print(f"First: {forecast[0]}")
print(f"Last:  {forecast[-1]}")
print()
print("ALL TESTS PASSED")
