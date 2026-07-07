import pandas as pd
from prophet import Prophet


class ForecastPredictor:

    @staticmethod
    def predict(
        history: pd.DataFrame,
        days: int = 30,
    ):

        df = history.copy()

        df = df.rename(
            columns={
                "Date": "ds",
                "Close": "y",
            }
        )

        df["ds"] = pd.to_datetime(df["ds"])

        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
        )

        model.fit(df)

        future = model.make_future_dataframe(
            periods=days,
            freq="D",
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