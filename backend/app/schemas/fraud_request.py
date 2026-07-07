from pydantic import BaseModel


class FraudPredictionRequest(BaseModel):
    text: str