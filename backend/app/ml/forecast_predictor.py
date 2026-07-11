import numpy as np
import pandas as pd
from prophet import Prophet


class ForecastPredictor:

    @staticmethod
    def predict(
        history: pd.DataFrame,
        days: int = 30,
    ):
        """
        Fit Prophet on historical prices and forecast `days` into the future.

        Key fixes over the old version:
        - use freq="B" (business days) so weekends aren't in the forecast
        - yearly_seasonality turned off — with only ~2 yrs of data, prophet's
          yearly fourier terms overfit and create wild swings in the forecast
        - changepoint_prior_scale=0.1 — slightly more flexible trend to track
          recent momentum better than the default 0.05
        """

        df = history.copy()

        df = df.rename(
            columns={
                "Date": "ds",
                "Close": "y",
            }
        )

        df["ds"] = pd.to_datetime(df["ds"])

        # sort by date just in case the data comes in random order
        df = df.sort_values("ds").reset_index(drop=True)

        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=False,     # off — not enough data for yearly patterns
            changepoint_prior_scale=0.1,  # a bit more flexible than default 0.05
        )

        model.fit(df)

        future = model.make_future_dataframe(
            periods=days,
            freq="B",  # business days only — markets are closed on weekends
        )

        forecast = model.predict(future)

        result = forecast[
            [
                "ds",
                "yhat",
                "yhat_lower",
                "yhat_upper",
            ]
        ].tail(days)

        result["ds"] = result["ds"].dt.strftime("%Y-%m-%d")

        result["yhat"] = result["yhat"].round(2)
        result["yhat_lower"] = result["yhat_lower"].round(2)
        result["yhat_upper"] = result["yhat_upper"].round(2)

        return result.to_dict(
            orient="records",
        )

    @staticmethod
    def backtest(
        history: pd.DataFrame,
        horizon: int = 30,
        n_folds: int = 3,
    ):
        """
        Walk-forward cross-validation.

        How it works:
        1. We split the history into n_folds + 1 chunks.
        2. For each fold we train on everything BEFORE the fold window
           and predict the next `horizon` days.
        3. We compare predicted vs actual and compute MAE, MAPE.
        4. We also compute MASE (Mean Absolute Scaled Error) which compares
           our error against a naive "predict last price" baseline.
           MASE < 1 means the model beats naive, MASE > 1 means naive wins.
        5. Return metrics averaged across all folds.

        NOTE on R²: traditional R² is misleading for short-horizon stock
        forecasting because the variance within each test window is tiny.
        Even a perfect model can get negative R² this way. Instead we report
        MASE which is the standard metric for forecast evaluation.
        """

        df = history.copy()

        df = df.rename(
            columns={
                "Date": "ds",
                "Close": "y",
            }
        )

        df["ds"] = pd.to_datetime(df["ds"])
        df = df.sort_values("ds").reset_index(drop=True)

        total_rows = len(df)

        # we need at least (horizon * 2) rows to do a proper backtest
        if total_rows < horizon * 2:
            return {
                "mae": None,
                "mape": None,
                "mase": None,
                "n_folds": 0,
                "message": "Not enough data for backtest",
            }

        # figure out where each fold's test window starts
        # we reserve the last (n_folds * horizon) rows for testing
        min_train_size = total_rows - (n_folds * horizon)

        if min_train_size < 30:
            # if the minimum training set is too small, reduce folds
            n_folds = max(1, (total_rows - 30) // horizon)
            min_train_size = total_rows - (n_folds * horizon)

        all_mae = []
        all_mape = []
        all_naive_mae = []  # for MASE calculation

        for fold in range(n_folds):

            # train on everything up to the start of this fold's test window
            train_end = min_train_size + (fold * horizon)
            test_end = train_end + horizon

            # make sure we don't go past the data
            test_end = min(test_end, total_rows)

            train_df = df.iloc[:train_end].copy()
            test_df = df.iloc[train_end:test_end].copy()

            if len(test_df) == 0:
                continue

            # fit prophet with the same settings as predict()
            model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=True,
                yearly_seasonality=False,
                changepoint_prior_scale=0.1,
            )

            model.fit(train_df)

            # create future dates for just the test period
            future = model.make_future_dataframe(
                periods=len(test_df),
                freq="B",
            )

            forecast = model.predict(future)

            # get only the test-period predictions
            preds = forecast.tail(len(test_df))["yhat"].values
            actuals = test_df["y"].values

            # make sure arrays are same length (edge case: business day mismatch)
            min_len = min(len(preds), len(actuals))
            preds = preds[:min_len]
            actuals = actuals[:min_len]

            # --- compute metrics ---
            # MAE: average absolute error in dollars
            mae = float(np.mean(np.abs(actuals - preds)))

            # MAPE: average percentage error
            mape = float(np.mean(np.abs((actuals - preds) / actuals)) * 100)

            # Naive baseline MAE (predict last training price for all days)
            naive_pred = train_df["y"].iloc[-1]
            naive_mae = float(np.mean(np.abs(actuals - naive_pred)))

            all_mae.append(mae)
            all_mape.append(mape)
            all_naive_mae.append(naive_mae)

        if len(all_mae) == 0:
            return {
                "mae": None,
                "mape": None,
                "mase": None,
                "n_folds": 0,
                "message": "Could not complete any folds",
            }

        avg_mae = float(np.mean(all_mae))
        avg_naive_mae = float(np.mean(all_naive_mae))

        # MASE: our MAE / naive MAE
        # < 1 means we beat naive, > 1 means naive is better
        mase = round(avg_mae / avg_naive_mae, 4) if avg_naive_mae > 0 else None

        return {
            "mae": round(avg_mae, 2),
            "mape": round(float(np.mean(all_mape)), 2),
            "mase": mase,
            "n_folds": len(all_mae),
        }