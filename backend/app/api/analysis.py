from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.analysis_request import AnalysisRequest
from app.schemas.analysis_response import AnalysisResponse

from app.services.analysis_service import AnalysisService


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
)


@router.post(
    "/",
    response_model=AnalysisResponse,
)
def analyze(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
):
    return AnalysisService.analyze(
        db=db,
        report_id=request.report_id,
        forecast_days=request.forecast_days,
    )