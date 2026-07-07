from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.report_service import ReportService

from app.services.ocr_service import OCRService
from app.services.extracted_text_service import ExtractedTextService

from app.services.nlp_service import NLPService
from app.services.nlp_analysis_service import NLPAnalysisService

from app.services.financial_extraction_service import FinancialExtractionService
from app.services.financial_data_service import FinancialDataService

from app.services.ratio_calculation_service import RatioCalculationService
from app.services.financial_ratio_service import FinancialRatioService


class AnalysisService:

    @staticmethod
    def analyze(
        db: Session,
        report_id: int,
        forecast_days: int = 30,
    ):

        # ----------------------------
        # Validate report
        # ----------------------------
        report = ReportService.get_by_id(
            db,
            report_id,
        )

        if report is None:
            raise HTTPException(
                status_code=404,
                detail="Report not found.",
            )

        # ----------------------------
        # OCR
        # ----------------------------
        existing_text = ExtractedTextService.get_by_report_id(
            db,
            report_id,
        )

        if existing_text:

            extracted_text = existing_text.extracted_text

        else:

            file_path = ReportService.get_file_path(
                report
            )

            extracted_text = OCRService.extract_text(
                file_path
            )

            ExtractedTextService.create(
                db,
                report_id,
                extracted_text,
            )

        # ----------------------------
        # NLP
        # ----------------------------
        existing_nlp = NLPAnalysisService.get_by_report_id(
            db,
            report_id,
        )

        if existing_nlp:

            nlp_result = {
                "tokens": existing_nlp.tokens,
                "lemmas": existing_nlp.lemmas,
                "named_entities": existing_nlp.named_entities,
                "financial_keywords": existing_nlp.financial_keywords,
                "processed_sentences": existing_nlp.processed_sentences,
            }

        else:

            nlp_result = NLPService.process(
                extracted_text
            )

            NLPAnalysisService.create(
                db,
                report_id,
                nlp_result,
            )

        # ----------------------------
        # Financial Data Extraction
        # ----------------------------

        existing_financial_data = FinancialDataService.get_by_report_id(
            db,
            report_id,
        )

        if existing_financial_data:

            financial_data = {
                "revenue": existing_financial_data.revenue,
                "net_income": existing_financial_data.net_income,
                "operating_income": existing_financial_data.operating_income,
                "total_assets": existing_financial_data.total_assets,
                "total_liabilities": existing_financial_data.total_liabilities,
                "total_equity": existing_financial_data.total_equity,
                "cash": existing_financial_data.cash,
                "inventory": existing_financial_data.inventory,
                "receivables": existing_financial_data.receivables,
                "debt": existing_financial_data.debt,
                "eps": existing_financial_data.eps,
                "operating_cash_flow": existing_financial_data.operating_cash_flow,
                "free_cash_flow": existing_financial_data.free_cash_flow,
                "shares_outstanding": existing_financial_data.shares_outstanding,
            }

        else:

            financial_data = FinancialExtractionService.extract(
                extracted_text
            )

            FinancialDataService.create(
                db,
                report_id,
                financial_data,
            )

        # ----------------------------
        # Response
        # ----------------------------
        return {
            "report_id": report_id,

            "extracted_text": extracted_text,

            "nlp_analysis": {
                "token_count": len(
                    nlp_result["tokens"]
                ),
                "lemma_count": len(
                    nlp_result["lemmas"]
                ),
                "entity_count": len(
                    nlp_result["named_entities"]
                ),
                "financial_keyword_count": len(
                    nlp_result["financial_keywords"]
                ),
                "sentence_count": len(
                    nlp_result["processed_sentences"]
                ),
            },

            "financial_data": financial_data,

            "financial_ratios": None,

            "risk_prediction": None,

            "fraud_prediction": None,

            "forecast": None,
        }