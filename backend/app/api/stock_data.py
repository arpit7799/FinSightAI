import os
import glob

import numpy as np
import pandas as pd

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/stock-data",
    tags=["Stock Data"],
)

# path to the datasets/forecasting folder (relative to backend/)
DATASETS_DIR = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..",
        "datasets", "forecasting",
    )
)


def _load_and_combine_all_csvs():
    """
    Load every CSV in the forecasting folder, normalize each stock's
    prices so they all start at 100 (makes them comparable despite
    wildly different dollar values), then average across stocks per date.

    This gives us a "market composite index" — one clean time series
    that captures the common patterns across all 11 stocks.

    Why normalize?
    - Amazon trades at ~$3400, Apple at ~$130, Treasury bills at ~$0.04
    - If we just averaged raw prices, Amazon would dominate everything
    - Normalizing to base-100 means each stock contributes equally
    """

    csv_files = glob.glob(os.path.join(DATASETS_DIR, "*.csv"))

    if len(csv_files) == 0:
        return pd.DataFrame(columns=["Date", "Close"])

    all_normalized = []

    for csv_path in csv_files:
        df = pd.read_csv(csv_path)

        # we only need Date and Close columns
        df = df[["Date", "Close"]].copy()
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)

        # skip if empty or has bad data
        if len(df) == 0 or df["Close"].iloc[0] == 0:
            continue

        # normalize: divide every price by the first price, then multiply by 100
        # so each stock starts at 100 on its first day
        first_price = df["Close"].iloc[0]
        df["Close"] = (df["Close"] / first_price) * 100.0

        # add a ticker column so we can track which stock it came from
        ticker_name = os.path.basename(csv_path).replace("_stock.csv", "").replace(".csv", "")
        df["ticker"] = ticker_name

        all_normalized.append(df)

    if len(all_normalized) == 0:
        return pd.DataFrame(columns=["Date", "Close"])

    # stack all the normalized dataframes together
    big_df = pd.concat(all_normalized, ignore_index=True)

    # for each date, take the AVERAGE normalized price across all stocks
    # this creates our "market composite index"
    composite = (
        big_df
        .groupby("Date")["Close"]
        .mean()
        .reset_index()
    )

    composite = composite.sort_values("Date").reset_index(drop=True)

    # convert Date back to string for the API response
    composite["Date"] = composite["Date"].dt.strftime("%Y-%m-%d")
    composite["Close"] = composite["Close"].round(4)

    return composite


@router.get("/combined")
def get_combined_stock_data():
    """
    Return a combined 'market composite' built from ALL stock CSVs.
    Each stock is normalized to base-100 and then averaged per date.
    This gives the forecast model way more signal to learn from
    compared to a single stock.
    """

    composite = _load_and_combine_all_csvs()

    if len(composite) == 0:
        raise HTTPException(
            status_code=404,
            detail="No CSV files found in datasets/forecasting/",
        )

    result = composite.to_dict(orient="records")

    return {
        "ticker": "combined",
        "num_stocks": len(glob.glob(os.path.join(DATASETS_DIR, "*.csv"))),
        "history": result,
    }


@router.get("/{ticker}")
def get_stock_data(ticker: str):
    """
    Return historical price data for a given ticker.
    Reads from datasets/forecasting/{ticker}_stock.csv
    and returns a list of {Date, Close} dicts.
    """

    # build the csv file name — user sends "apple", we look for "apple_stock.csv"
    filename = f"{ticker.lower()}_stock.csv"
    filepath = os.path.normpath(
        os.path.join(DATASETS_DIR, filename)
    )

    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=404,
            detail=f"No data file found for ticker '{ticker}'.",
        )

    df = pd.read_csv(filepath)

    # only send the columns the forecast model needs
    result = df[["Date", "Close"]].to_dict(orient="records")

    return {"ticker": ticker, "history": result}
