from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    report_id: int
    forecast_days: int = 30