from pathlib import Path
import shutil

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.report import Report
from app.utils.file_utils import allowed_file, generate_filename


UPLOAD_DIR = Path("uploads/reports")


class ReportService:

    @staticmethod
    def upload_report(
        db: Session,
        company_id: int,
        file: UploadFile,
    ):

        company = (
            db.query(Company)
            .filter(Company.id == company_id)
            .first()
        )

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found.",
            )

        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type.",
            )

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        stored_filename = generate_filename(file.filename)

        file_path = UPLOAD_DIR / stored_filename

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        report = Report(
            company_id=company_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_type=Path(file.filename).suffix.lower(),
            file_size=file_path.stat().st_size,
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        return report

    @staticmethod
    def get_all(db: Session):
        return (
            db.query(Report)
            .order_by(Report.upload_date.desc())
            .all()
        )

    @staticmethod
    def get_by_id(
        db: Session,
        report_id: int,
    ):
        return (
            db.query(Report)
            .filter(Report.id == report_id)
            .first()
        )

    @staticmethod
    def delete(
        db: Session,
        report_id: int,
    ):

        report = ReportService.get_by_id(
            db,
            report_id,
        )

        if not report:
            return False

        file_path = UPLOAD_DIR / report.stored_filename

        if file_path.exists():
            file_path.unlink()

        db.delete(report)
        db.commit()

        return True