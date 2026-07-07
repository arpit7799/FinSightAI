from pydantic import BaseModel


class FraudPredictionResponse(BaseModel):

    prediction: str

    confidence: float

    probabilities: dict