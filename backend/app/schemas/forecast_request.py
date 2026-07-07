from pydantic import BaseModel
from typing import List


class ForecastDataPoint(BaseModel):
    Date: str
    Close: float


class ForecastRequest(BaseModel):
    history: List[ForecastDataPoint]
    days: int = 30