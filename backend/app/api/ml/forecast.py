import pandas as pd

from fastapi import APIRouter

from app.ml.forecast_predictor import ForecastPredictor

from app.schemas.forecast_request import ForecastRequest
from app.schemas.forecast_response import ForecastResponse


router = APIRouter(
    prefix="/ml/forecast",
    tags=["Machine Learning"],
)


@router.post(
    "/",
    response_model=ForecastResponse,
)
def forecast(request: ForecastRequest):

    history = pd.DataFrame(
        [
            item.model_dump()
            for item in request.history
        ]
    )

    # generate the forecast
    result = ForecastPredictor.predict(
        history,
        request.days,
    )

    # run walk-forward backtest so we can report real accuracy metrics
    # (only if we have enough data — backtest handles the edge case internally)
    metrics = ForecastPredictor.backtest(
        history,
        horizon=request.days,
        n_folds=3,
    )

    return {
        "forecast": result,
        "backtest_metrics": metrics,
    }