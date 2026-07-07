from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.extracted_text_service import ExtractedTextService
from app.services.nlp_analysis_service import NLPAnalysisService
from app.services.nlp_service import NLPService

router = APIRouter(
    prefix="/reports",
    tags=["NLP"],
)


@router.post("/{report_id}/analyze-text")
def analyze_text(
    report_id: int,
    db: Session = Depends(get_db),
):
    extracted = ExtractedTextService.get_by_report_id(
        db,
        report_id,
    )

    if extracted is None:
        raise HTTPException(
            status_code=404,
            detail="Extracted text not found. Run OCR first.",
        )

    existing = NLPAnalysisService.get_by_report_id(
        db,
        report_id,
    )

    if existing:
        return {
            "message": "NLP analysis already exists.",
            "report_id": report_id,
            "statistics": {
                "token_count": len(existing.tokens),
                "lemma_count": len(existing.lemmas),
                "entity_count": len(existing.named_entities),
                "financial_keyword_count": len(existing.financial_keywords),
                "sentence_count": len(existing.processed_sentences),
            },
            "preview": {
                "tokens": existing.tokens[:10],
                "lemmas": existing.lemmas[:10],
                "named_entities": existing.named_entities[:10],
                "financial_keywords": existing.financial_keywords[:10],
                "processed_sentences": existing.processed_sentences[:3],
            },
        }

    result = NLPService.process(
        extracted.extracted_text
    )

    NLPAnalysisService.create(
        db,
        report_id,
        result,
    )

    return {
        "message": "NLP analysis completed successfully.",
        "report_id": report_id,
        "statistics": {
            "token_count": len(result["tokens"]),
            "lemma_count": len(result["lemmas"]),
            "entity_count": len(result["named_entities"]),
            "financial_keyword_count": len(result["financial_keywords"]),
            "sentence_count": len(result["processed_sentences"]),
        },
        "preview": {
            "tokens": result["tokens"][:10],
            "lemmas": result["lemmas"][:10],
            "named_entities": result["named_entities"][:10],
            "financial_keywords": result["financial_keywords"][:10],
            "processed_sentences": result["processed_sentences"][:3],
        },
    }