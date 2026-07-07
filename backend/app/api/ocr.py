from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.extracted_text import ExtractedText
from app.services.ocr_service import OCRService
from app.services.report_service import ReportService
from app.services.extracted_text_service import ExtractedTextService

router = APIRouter(
    prefix="/reports",
    tags=["OCR"],
)


@router.post("/{report_id}/extract-text")
def extract_text(
    report_id: int,
    db: Session = Depends(get_db),
):
    report = ReportService.get_by_id(db, report_id)

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    existing = ExtractedTextService.get_by_report_id(
        db,
        report_id,
        )

    if existing:
        return {
            "message": "Text already extracted.",
            "text": existing.extracted_text,
        }

    file_path = ReportService.get_file_path(report)

    text = OCRService.extract_text(file_path)

    extracted = ExtractedText(
        report_id=report.id,
        extracted_text=text,
    )

    db.add(extracted)
    db.commit()
    db.refresh(extracted)

    return {
        "message": "Text extracted successfully.",
        "text": text,
    }