from pydantic import BaseModel


class RiskPredictionResponse(BaseModel):

    prediction: str

    confidence: float

    probabilities: dict