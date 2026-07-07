from sqlalchemy.orm import Session

from app.models.extracted_text import ExtractedText


class ExtractedTextService:

    @staticmethod
    def get_by_report_id(
        db: Session,
        report_id: int,
    ):
        return (
            db.query(ExtractedText)
            .filter(
                ExtractedText.report_id == report_id
            )
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        report_id: int,
        text: str,
    ):
        extracted = ExtractedText(
            report_id=report_id,
            extracted_text=text,
        )

        db.add(extracted)
        db.commit()
        db.refresh(extracted)

        return extracted

    @staticmethod
    def delete(
        db: Session,
        report_id: int,
    ):
        extracted = (
            db.query(ExtractedText)
            .filter(
                ExtractedText.report_id == report_id
            )
            .first()
        )

        if extracted:
            db.delete(extracted)
            db.commit()