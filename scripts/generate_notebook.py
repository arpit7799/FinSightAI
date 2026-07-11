"""
Script to generate the forecasting.ipynb notebook.
Run this once to create the notebook, then open it in Jupyter.
"""
import json
import os

cells = []

def md(source):
    lines = source.strip().split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            new_lines.append(line + '\n')
        else:
            new_lines.append(line)
    cells.append({
        'cell_type': 'markdown',
        'metadata': {},
        'source': new_lines
    })

def code(source):
    lines = source.strip().split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            new_lines.append(line + '\n')
        else:
            new_lines.append(line)
    cells.append({
        'cell_type': 'code',
        'metadata': {},
        'source': new_lines,
        'outputs': [],
        'execution_count': None
    })


# ============================================================
# TITLE
# ============================================================
md("""# 📈 FinSightAI — Stock Price Forecasting (Multi-Stock Prophet)
---

**What this notebook does:**
1. Load ALL 11 stock CSV files (Apple, Amazon, Tesla, Nvidia, etc.)
2. Explore & visualize each stock individually
3. Normalize prices (base-100) so all stocks are comparable
4. Combine into a "market composite index"
5. Train a Prophet model on the combined data
6. Run walk-forward backtesting (proper evaluation)
7. Compare Prophet vs a naive baseline
8. Generate future forecasts
9. Save the trained model

> This is the training pipeline for the production forecast endpoint
> in our FastAPI backend (`/ml/forecast/`).""")


# ============================================================
# STEP 1: IMPORTS
# ============================================================
md("## Step 1: Import Libraries")

code("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import os
import warnings
import joblib

from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# make plots look nice
plt.style.use("seaborn-v0_8-darkgrid")
sns.set_palette("husl")
plt.rcParams["figure.figsize"] = (14, 6)
plt.rcParams["font.size"] = 12

# suppress prophet's noisy logs
warnings.filterwarnings("ignore")

print("All imports done!")""")


# ============================================================
# STEP 2: LOAD ALL CSVs
# ============================================================
md("""## Step 2: Load All Stock CSV Files

We have 11 different financial instruments in `datasets/forecasting/`:
- **Stocks:** Apple, Amazon, Tesla, Nvidia, Meta, Microsoft, Adobe, Qualcomm
- **Crypto:** Bitcoin
- **Commodities:** Gold
- **Bonds:** Treasury Bill""")

code("""# find all csv files in the forecasting folder
csv_dir = "../datasets/forecasting/"
csv_files = sorted(glob.glob(os.path.join(csv_dir, "*.csv")))

print(f"Found {len(csv_files)} CSV files:\\n")

for f in csv_files:
    name = os.path.basename(f)
    df_temp = pd.read_csv(f)
    print(f"  {name:30s} -> {len(df_temp)} rows")""")

code("""# load all csvs into a dictionary
stock_data = {}

for csv_path in csv_files:
    # get a clean name like "apple", "amazon", etc.
    name = os.path.basename(csv_path).replace("_stock.csv", "").replace(".csv", "")

    df = pd.read_csv(csv_path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    stock_data[name] = df

print(f"Loaded {len(stock_data)} stocks: {list(stock_data.keys())}")""")


# ============================================================
# STEP 3: EDA
# ============================================================
md("""## Step 3: Exploratory Data Analysis (EDA)

### 3.1 Basic Info for Each Stock""")

code("""# show basic info for each stock
for name, df in stock_data.items():
    date_range = f"{df['Date'].iloc[0].date()} to {df['Date'].iloc[-1].date()}"
    price_range = f"${df['Close'].min():.2f} - ${df['Close'].max():.2f}"
    print(f"{name:15s} | {len(df):4d} rows | {date_range} | Close: {price_range}")""")

md("### 3.2 Check for Missing Values")

code("""# check for missing values
print("Missing values per stock:\\n")

for name, df in stock_data.items():
    missing = df[["Date", "Close"]].isnull().sum().sum()
    print(f"  {name:15s}: {missing} missing values")

all_clean = all(
    df[["Date", "Close"]].isnull().sum().sum() == 0
    for df in stock_data.values()
)
print("\\nAll clean!" if all_clean else "\\nSome stocks have missing data!")""")

md("### 3.3 Plot Each Stock's Closing Price")

code("""# plot all stocks in a grid
fig, axes = plt.subplots(4, 3, figsize=(18, 16))
axes = axes.flatten()

for i, (name, df) in enumerate(stock_data.items()):
    ax = axes[i]
    ax.plot(df["Date"], df["Close"], linewidth=1.5)
    ax.set_title(f"{name.title()} Close Price", fontsize=11, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price ($)")
    ax.grid(True, alpha=0.3)

# hide extra subplots
for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)

plt.suptitle("All Stock Closing Prices (Raw)", fontsize=16, fontweight="bold", y=1.02)
plt.tight_layout()
plt.show()""")

md("### 3.4 Summary Statistics")

code("""# build a summary table
summary_rows = []

for name, df in stock_data.items():
    summary_rows.append({
        "Stock": name.title(),
        "Rows": len(df),
        "Start Price": round(df["Close"].iloc[0], 2),
        "End Price": round(df["Close"].iloc[-1], 2),
        "Min": round(df["Close"].min(), 2),
        "Max": round(df["Close"].max(), 2),
        "Mean": round(df["Close"].mean(), 2),
        "Std": round(df["Close"].std(), 2),
        "Return %": round((df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100, 1),
    })

summary_df = pd.DataFrame(summary_rows).sort_values("Return %", ascending=False)
summary_df""")


# ============================================================
# STEP 4: NORMALIZE
# ============================================================
md("""## Step 4: Normalize Prices (Base-100)

**Problem:** Each stock has a totally different price scale.
- Amazon = ~$3,400 | Apple = ~$130 | Treasury Bill = ~$0.04

**Solution:** Normalize so first price = 100.

`normalized = (price / first_price) * 100`""")

code("""# normalize each stock to base-100
normalized_stocks = {}

for name, df in stock_data.items():
    norm_df = df[["Date", "Close"]].copy()

    first_price = norm_df["Close"].iloc[0]
    norm_df["Close_Normalized"] = (norm_df["Close"] / first_price) * 100.0

    normalized_stocks[name] = norm_df

# show before vs after
print("Before vs After normalization:\\n")
for name in ["apple", "amazon", "tesla", "gold"]:
    raw_first = stock_data[name]["Close"].iloc[0]
    raw_last = stock_data[name]["Close"].iloc[-1]
    norm_first = normalized_stocks[name]["Close_Normalized"].iloc[0]
    norm_last = normalized_stocks[name]["Close_Normalized"].iloc[-1]
    print(f"  {name:10s}: ${raw_first:>10.2f} -> {norm_first:>7.2f}  |  ${raw_last:>10.2f} -> {norm_last:>7.2f}")""")

code("""# plot all stocks AFTER normalization
plt.figure(figsize=(14, 7))

for name, df in normalized_stocks.items():
    plt.plot(df["Date"], df["Close_Normalized"], linewidth=1.5, label=name.title(), alpha=0.8)

plt.axhline(y=100, color="gray", linestyle="--", alpha=0.5, label="Starting Point (100)")
plt.title("All Stocks Normalized to Base-100", fontsize=16, fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Normalized Price (started at 100)")
plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=9)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()""")


# ============================================================
# STEP 5: COMBINE
# ============================================================
md("""## Step 5: Combine into Market Composite Index

Average the normalized prices across ALL stocks for each date.
This gives us one clean time series that captures common patterns.""")

code("""# stack all normalized frames and average by date
all_frames = []

for name, df in normalized_stocks.items():
    temp = df[["Date", "Close_Normalized"]].copy()
    temp = temp.rename(columns={"Close_Normalized": "Close"})
    temp["ticker"] = name
    all_frames.append(temp)

big_df = pd.concat(all_frames, ignore_index=True)

# group by date -> average
composite = big_df.groupby("Date")["Close"].mean().reset_index()
composite = composite.sort_values("Date").reset_index(drop=True)

print(f"Combined dataset: {len(composite)} rows")
print(f"Date range: {composite['Date'].iloc[0].date()} to {composite['Date'].iloc[-1].date()}")
print(f"Price range: {composite['Close'].min():.2f} to {composite['Close'].max():.2f}")
print(f"Stocks included: {len(normalized_stocks)}")""")

code("""# plot the composite
plt.figure(figsize=(14, 6))

plt.fill_between(composite["Date"], composite["Close"], alpha=0.3, color="#7C3AED")
plt.plot(composite["Date"], composite["Close"], linewidth=2, color="#7C3AED")

plt.title("Market Composite Index (Avg of 11 Normalized Stocks)", fontsize=16, fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Composite Index Value")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()""")


# ============================================================
# STEP 6: PREPARE FOR PROPHET
# ============================================================
md("""## Step 6: Prepare Data for Prophet

Prophet needs: `ds` (date) and `y` (value).""")

code("""# rename for prophet
prophet_df = composite[["Date", "Close"]].copy()
prophet_df.columns = ["ds", "y"]
prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])

print(f"Prophet DataFrame: {prophet_df.shape}")
prophet_df.head()""")


# ============================================================
# STEP 7: SIMPLE 80/20 SPLIT
# ============================================================
md("""## Step 7: Simple Train/Test Split (80/20)

Start with a basic split to see if the model works at all.""")

code("""# 80/20 split
split_idx = int(len(prophet_df) * 0.8)

train_df = prophet_df.iloc[:split_idx].copy()
test_df = prophet_df.iloc[split_idx:].copy()

print(f"Training: {len(train_df)} rows ({train_df['ds'].iloc[0].date()} to {train_df['ds'].iloc[-1].date()})")
print(f"Testing:  {len(test_df)} rows ({test_df['ds'].iloc[0].date()} to {test_df['ds'].iloc[-1].date()})")""")


# ============================================================
# STEP 8: TRAIN PROPHET
# ============================================================
md("""## Step 8: Train the Prophet Model

**Settings:**
- `yearly_seasonality=False` — only ~2 years of data, would overfit
- `weekly_seasonality=True` — markets have Mon-Fri patterns
- `daily_seasonality=False` — daily data, not hourly
- `changepoint_prior_scale=0.1` — more flexible trend than default""")

code("""# train prophet
model = Prophet(
    daily_seasonality=False,
    weekly_seasonality=True,
    yearly_seasonality=False,
    changepoint_prior_scale=0.1,
)

model.fit(train_df)

print("Prophet model trained!")
print(f"  Training rows: {len(train_df)}")
print(f"  Changepoints: {len(model.changepoints)}")""")


# ============================================================
# STEP 9: PREDICT TEST SET
# ============================================================
md("## Step 9: Predict on Test Set")

code("""# make future dates covering the test period
future = model.make_future_dataframe(periods=len(test_df), freq="B")
forecast = model.predict(future)

# grab test period predictions
preds = forecast.tail(len(test_df))["yhat"].values
actuals = test_df["y"].values

# handle length mismatch
min_len = min(len(preds), len(actuals))
preds = preds[:min_len]
actuals = actuals[:min_len]

print(f"Predictions: {len(preds)} points")
print(f"Actuals:     {len(actuals)} points")""")


# ============================================================
# STEP 10: EVALUATE SIMPLE SPLIT
# ============================================================
md("## Step 10: Evaluate (Simple Split)")

code("""# metrics
mae = mean_absolute_error(actuals, preds)
rmse = np.sqrt(mean_squared_error(actuals, preds))
mape = np.mean(np.abs((actuals - preds) / actuals)) * 100

# naive baseline
naive_val = train_df["y"].iloc[-1]
naive_mae = mean_absolute_error(actuals, np.full(len(actuals), naive_val))
mase = mae / naive_mae if naive_mae > 0 else None

print("=" * 50)
print("   80/20 SPLIT RESULTS")
print("=" * 50)
print(f"   MAE:  {mae:.4f}")
print(f"   RMSE: {rmse:.4f}")
print(f"   MAPE: {mape:.2f}%")
print(f"   MASE: {mase:.4f}")
if mase and mase < 1:
    print("   -> Model BEATS naive!")
else:
    print("   -> Comparable to naive")
print(f"\\n   Naive MAE: {naive_mae:.4f}")
print("=" * 50)""")

code("""# plot actual vs predicted
plt.figure(figsize=(14, 6))

test_dates = test_df["ds"].values[:min_len]
plt.plot(test_dates, actuals, label="Actual", color="#2563EB", linewidth=2)
plt.plot(test_dates, preds, label="Prophet", color="#ef4444", linewidth=2, linestyle="--")
plt.axhline(y=naive_val, color="gray", linestyle=":", alpha=0.5, label=f"Naive ({naive_val:.1f})")

fc_tail = forecast.tail(min_len)
plt.fill_between(test_dates, fc_tail["yhat_lower"].values, fc_tail["yhat_upper"].values,
                 alpha=0.15, color="#ef4444", label="95% Confidence")

plt.title("Prophet vs Actual (80/20 Split)", fontsize=14, fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Composite Value")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()""")


# ============================================================
# STEP 11: PROPHET COMPONENTS
# ============================================================
md("""## Step 11: Prophet Components

Prophet decomposes the series into **trend** + **seasonality**.""")

code("""fig = model.plot_components(forecast)
plt.suptitle("Prophet Components", fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
plt.show()""")


# ============================================================
# STEP 12: WALK-FORWARD BACKTEST
# ============================================================
md("""## Step 12: Walk-Forward Backtesting (Proper Evaluation)

A single 80/20 split can be misleading. Walk-forward backtest:

1. Train on data up to day T
2. Predict next 30 days
3. Slide forward 30 days
4. Repeat N times

Tests the model on **multiple non-overlapping future windows**.""")

code("""def walk_forward_backtest(df, horizon=30, n_folds=5):
    total = len(df)
    min_train = total - (n_folds * horizon)

    if min_train < 30:
        n_folds = max(1, (total - 30) // horizon)
        min_train = total - (n_folds * horizon)

    fold_results = []
    all_preds = []
    all_actuals = []
    all_dates = []

    for fold in range(n_folds):
        train_end = min_train + (fold * horizon)
        test_end = min(train_end + horizon, total)

        fold_train = df.iloc[:train_end].copy()
        fold_test = df.iloc[train_end:test_end].copy()

        if len(fold_test) == 0:
            continue

        m = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=False,
            changepoint_prior_scale=0.1,
        )
        m.fit(fold_train)

        future = m.make_future_dataframe(periods=len(fold_test), freq="B")
        fc = m.predict(future)

        p = fc.tail(len(fold_test))["yhat"].values
        a = fold_test["y"].values
        min_l = min(len(p), len(a))
        p, a = p[:min_l], a[:min_l]

        fold_mae = float(np.mean(np.abs(a - p)))
        fold_mape = float(np.mean(np.abs((a - p) / a)) * 100)
        naive_p = fold_train["y"].iloc[-1]
        fold_naive_mae = float(np.mean(np.abs(a - naive_p)))

        fold_results.append({
            "fold": fold + 1,
            "train_end": str(fold_train["ds"].iloc[-1].date()),
            "test_start": str(fold_test["ds"].iloc[0].date()),
            "test_end": str(fold_test["ds"].iloc[-1].date()),
            "mae": round(fold_mae, 2),
            "mape": round(fold_mape, 2),
            "naive_mae": round(fold_naive_mae, 2),
            "mase": round(fold_mae / fold_naive_mae, 4) if fold_naive_mae > 0 else None,
        })

        all_preds.extend(p)
        all_actuals.extend(a)
        all_dates.extend(fold_test["ds"].values[:min_l])

    all_preds = np.array(all_preds)
    all_actuals = np.array(all_actuals)

    overall_mae = float(np.mean(np.abs(all_actuals - all_preds)))
    overall_mape = float(np.mean(np.abs((all_actuals - all_preds) / all_actuals)) * 100)
    avg_naive = float(np.mean([f["naive_mae"] for f in fold_results]))
    overall_mase = overall_mae / avg_naive if avg_naive > 0 else None

    return {
        "overall": {
            "mae": round(overall_mae, 2),
            "mape": round(overall_mape, 2),
            "mase": round(overall_mase, 4) if overall_mase else None,
            "n_folds": len(fold_results),
        },
        "folds": fold_results,
        "predictions": all_preds,
        "actuals": all_actuals,
        "dates": all_dates,
    }

print("Walk-forward backtest function defined!")""")

code("""# run backtest with 5 folds
print("Running walk-forward backtest (5 folds x 30 days)...")
print("Training 5 separate Prophet models, please wait...\\n")

bt = walk_forward_backtest(prophet_df, horizon=30, n_folds=5)""")

code("""# per-fold results
print("Per-Fold Results:")
print("=" * 90)
print(f"{'Fold':>5} | {'Train End':>12} | {'Test Range':>27} | {'MAE':>8} | {'MAPE':>8} | {'MASE':>8}")
print("-" * 90)

for row in bt["folds"]:
    mase_str = f"{row['mase']:.4f}" if row["mase"] else "N/A"
    marker = " <-GOOD" if row["mase"] and row["mase"] < 1 else ""
    print(f"{row['fold']:>5} | {row['train_end']:>12} | {row['test_start']} to {row['test_end']} | {row['mae']:>8.2f} | {row['mape']:>7.2f}% | {mase_str:>8}{marker}")

print("=" * 90)
o = bt["overall"]
print(f"\\nOverall: MAE={o['mae']}, MAPE={o['mape']}%, MASE={o['mase']}")
if o["mase"] and o["mase"] < 1:
    print("\\nModel BEATS naive baseline!")
else:
    print("\\nComparable to naive (normal for financial data)")""")

code("""# plot backtest predictions vs actuals
plt.figure(figsize=(14, 6))

bt_dates = pd.to_datetime(bt["dates"])

plt.plot(bt_dates, bt["actuals"], label="Actual", color="#2563EB", linewidth=2)
plt.plot(bt_dates, bt["predictions"], label="Prophet (walk-forward)", color="#ef4444", linewidth=2, linestyle="--")

# shade each fold
colors = ["#FFE4E1", "#E0FFE0", "#E0E0FF", "#FFFFE0", "#FFE0FF"]
for i, row in enumerate(bt["folds"]):
    plt.axvspan(pd.Timestamp(row["test_start"]), pd.Timestamp(row["test_end"]),
                alpha=0.15, color=colors[i % len(colors)], label=f"Fold {row['fold']}")

plt.title("Walk-Forward Backtest Results", fontsize=14, fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Composite Value")
plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()""")

code("""# scatter: predicted vs actual
plt.figure(figsize=(7, 7))

plt.scatter(bt["actuals"], bt["predictions"], alpha=0.6, color="#7C3AED", edgecolors="white", s=50)

lo = min(bt["actuals"].min(), bt["predictions"].min())
hi = max(bt["actuals"].max(), bt["predictions"].max())
plt.plot([lo, hi], [lo, hi], "k--", linewidth=1, label="Perfect prediction")

plt.title("Predicted vs Actual (Scatter)", fontsize=14, fontweight="bold")
plt.xlabel("Actual")
plt.ylabel("Predicted")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()""")


# ============================================================
# STEP 13: ERROR ANALYSIS
# ============================================================
md("## Step 13: Error Distribution")

code("""errors = bt["actuals"] - bt["predictions"]
pct_errors = (errors / bt["actuals"]) * 100

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].hist(errors, bins=20, color="#2563EB", alpha=0.7, edgecolor="white")
axes[0].axvline(x=0, color="red", linestyle="--")
axes[0].set_title("Error Distribution", fontweight="bold")
axes[0].set_xlabel("Error (Actual - Predicted)")

axes[1].hist(pct_errors, bins=20, color="#7C3AED", alpha=0.7, edgecolor="white")
axes[1].axvline(x=0, color="red", linestyle="--")
axes[1].set_title("Percentage Error Distribution", fontweight="bold")
axes[1].set_xlabel("Error (%)")

plt.tight_layout()
plt.show()

print(f"Mean Error:    {np.mean(errors):.2f} (bias)")
print(f"Std of Errors: {np.std(errors):.2f}")
print(f"Mean % Error:  {np.mean(pct_errors):.2f}%")""")


# ============================================================
# STEP 14: TRAIN FINAL MODEL ON ALL DATA
# ============================================================
md("""## Step 14: Train Final Model on ALL Data

Now that backtesting is done, train the production model on
the complete dataset for the best possible forecast.""")

code("""# train on everything
final_model = Prophet(
    daily_seasonality=False,
    weekly_seasonality=True,
    yearly_seasonality=False,
    changepoint_prior_scale=0.1,
)

final_model.fit(prophet_df)

print("Final model trained on ALL data!")
print(f"  Rows: {len(prophet_df)}")
print(f"  Range: {prophet_df['ds'].iloc[0].date()} to {prophet_df['ds'].iloc[-1].date()}")
print(f"  Changepoints: {len(final_model.changepoints)}")""")


# ============================================================
# STEP 15: FUTURE FORECAST
# ============================================================
md("## Step 15: Generate 30-Day Future Forecast")

code("""# forecast 30 business days ahead
future_df = final_model.make_future_dataframe(periods=30, freq="B")
final_forecast = final_model.predict(future_df)

future_preds = final_forecast.tail(30)[["ds", "yhat", "yhat_lower", "yhat_upper"]]

print("30-Day Forecast:\\n")
print(future_preds.to_string(index=False))""")

code("""# plot history + forecast
plt.figure(figsize=(14, 7))

plt.plot(prophet_df["ds"], prophet_df["y"], label="Historical", color="#2563EB", linewidth=1.5)
plt.plot(future_preds["ds"], future_preds["yhat"], label="Forecast", color="#ef4444", linewidth=2.5, linestyle="--")
plt.fill_between(future_preds["ds"], future_preds["yhat_lower"], future_preds["yhat_upper"],
                 alpha=0.2, color="#ef4444", label="95% Confidence")
plt.axvline(x=prophet_df["ds"].iloc[-1], color="gray", linestyle=":", alpha=0.5)

plt.title("Market Composite: History + 30-Day Forecast", fontsize=16, fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Composite Value")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()""")


# ============================================================
# STEP 16: FINAL COMPONENTS
# ============================================================
md("## Step 16: Final Model Components")

code("""fig = final_model.plot_components(final_forecast)
plt.suptitle("Final Model Components", fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
plt.show()""")


# ============================================================
# STEP 17: SAVE MODEL
# ============================================================
md("## Step 17: Save the Trained Model")

code("""# save with joblib
model_path = "../backend/trained_models/prophet_forecast_model.pkl"
os.makedirs(os.path.dirname(model_path), exist_ok=True)

joblib.dump(final_model, model_path)

print(f"Model saved to: {model_path}")
print(f"File size: {os.path.getsize(model_path) / 1024:.1f} KB")""")


# ============================================================
# STEP 18: SUMMARY
# ============================================================
md("## Step 18: Final Summary")

code("""print("=" * 60)
print("   FINSIGHT AI - FORECASTING TRAINING SUMMARY")
print("=" * 60)
print()
print(f"Data:")
print(f"  Stocks combined:    {len(stock_data)}")
print(f"  Total data points:  {len(prophet_df)}")
print(f"  Date range:         {prophet_df['ds'].iloc[0].date()} to {prophet_df['ds'].iloc[-1].date()}")
print()
print(f"Model: Prophet")
print(f"  weekly_seasonality: True")
print(f"  yearly_seasonality: False")
print(f"  changepoint_prior:  0.1")
print(f"  forecast freq:      B (business days)")
print()
o = bt["overall"]
print(f"Backtest ({o['n_folds']} folds, 30-day horizon):")
print(f"  MAE:  {o['mae']}")
print(f"  MAPE: {o['mape']}%")
print(f"  MASE: {o['mase']}")
if o["mase"] and o["mase"] < 1:
    print(f"  Model beats naive baseline!")
print()
print(f"Saved: {model_path}")
print()
print("=" * 60)
print("   TRAINING COMPLETE")
print("=" * 60)""")


# ============================================================
# BUILD NOTEBOOK
# ============================================================
notebook = {
    'nbformat': 4,
    'nbformat_minor': 5,
    'metadata': {
        'kernelspec': {
            'display_name': 'FinsightAI_env',
            'language': 'python',
            'name': 'finsightai_env'
        },
        'language_info': {
            'name': 'python',
            'version': '3.11.0',
            'mimetype': 'text/x-python',
            'codemirror_mode': {'name': 'ipython', 'version': 3},
            'file_extension': '.py',
            'pygments_lexer': 'ipython3',
            'nbconvert_exporter': 'python'
        }
    },
    'cells': cells
}

output_path = os.path.join(os.path.dirname(__file__), '..', 'notebooks', 'forecasting.ipynb')
with open(output_path, 'w') as f:
    json.dump(notebook, f, indent=1)

md_count = sum(1 for c in cells if c['cell_type'] == 'markdown')
code_count = sum(1 for c in cells if c['cell_type'] == 'code')
print(f'Notebook written to {output_path}')
print(f'  {len(cells)} cells total ({md_count} markdown, {code_count} code)')
