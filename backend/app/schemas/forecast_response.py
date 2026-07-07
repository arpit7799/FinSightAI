from pydantic import BaseModel
from typing import List


class ForecastPrediction(BaseModel):
    ds: str
    yhat: float
    yhat_lower: float
    yhat_upper: float


class ForecastResponse(BaseModel):
    forecast: List[ForecastPrediction]