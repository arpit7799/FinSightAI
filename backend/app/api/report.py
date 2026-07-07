from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.report import ReportResponse
from app.services.report_service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.post(
    "/upload",
    response_model=ReportResponse,
)
def upload_report(
    company_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return ReportService.upload_report(
        db=db,
        company_id=company_id,
        file=file,
    )