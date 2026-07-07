from sqlalchemy.orm import Session

from app.models.nlp_analysis import NLPAnalysis


class NLPAnalysisService:

    @staticmethod
    def get_by_report_id(
        db: Session,
        report_id: int,
    ):
        return (
            db.query(NLPAnalysis)
            .filter(
                NLPAnalysis.report_id == report_id
            )
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        report_id: int,
        result: dict,
    ):
        analysis = NLPAnalysis(
            report_id=report_id,
            tokens=result["tokens"],
            lemmas=result["lemmas"],
            named_entities=result["named_entities"],
            financial_keywords=result["financial_keywords"],
            processed_sentences=result["processed_sentences"],
        )

        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return analysis