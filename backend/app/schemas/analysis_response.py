from pydantic import BaseModel
from typing import Any


class AnalysisResponse(BaseModel):

    report_id: int

    extracted_text: Any

    nlp_analysis: Any

    financial_data: Any

    financial_ratios: Any

    risk_prediction: Any

    fraud_prediction: Any

    forecast: Any | None = None