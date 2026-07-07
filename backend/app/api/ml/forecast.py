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

    result = ForecastPredictor.predict(
        history,
        request.days,
    )

    return {
        "forecast": result
    }