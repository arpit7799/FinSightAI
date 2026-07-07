from fastapi import APIRouter

from app.ml.risk_predictor import RiskPredictor

from app.schemas.risk_request import (
    RiskPredictionRequest,
)

from app.schemas.risk_response import (
    RiskPredictionResponse,
)


router = APIRouter(
    prefix="/ml/risk",
    tags=["Machine Learning"],
)


@router.post(
    "/",
    response_model=RiskPredictionResponse,
)
def predict_risk(
    request: RiskPredictionRequest,
):

    return RiskPredictor.predict(
        request.model_dump()
    )