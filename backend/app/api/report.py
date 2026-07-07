from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

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

@router.get(
    "/",
    response_model=list[ReportResponse],
)
def get_reports(
    db: Session = Depends(get_db),
):
    return ReportService.get_all(db)

@router.get(
    "/{report_id}",
    response_model=ReportResponse,
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
):

    report = ReportService.get_by_id(
        db,
        report_id,
    )

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    return report

@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
):

    deleted = ReportService.delete(
        db,
        report_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )
    