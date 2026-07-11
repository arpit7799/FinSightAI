from pydantic import BaseModel
from typing import List, Optional


class ForecastPrediction(BaseModel):
    ds: str
    yhat: float
    yhat_lower: float
    yhat_upper: float


class BacktestMetrics(BaseModel):
    mae: Optional[float] = None
    mape: Optional[float] = None
    mase: Optional[float] = None   # Mean Absolute Scaled Error (vs naive baseline)
    n_folds: int = 0
    message: Optional[str] = None


class ForecastResponse(BaseModel):
    forecast: List[ForecastPrediction]
    backtest_metrics: Optional[BacktestMetrics] = None