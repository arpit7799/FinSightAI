from fastapi import APIRouter

from app.ml.fraud_predictor import FraudPredictor

from app.schemas.fraud_request import FraudPredictionRequest
from app.schemas.fraud_response import FraudPredictionResponse


router = APIRouter(
    prefix="/ml/fraud",
    tags=["Machine Learning"],
)


@router.post(
    "/",
    response_model=FraudPredictionResponse,
)
def predict_fraud(
    request: FraudPredictionRequest,
):

    return FraudPredictor.predict(
        request.text
    )