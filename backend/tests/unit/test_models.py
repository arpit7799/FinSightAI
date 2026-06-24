# tests/unit/test_models.py
"""
Unit tests for Phase 2 — SQLAlchemy models and enum definitions.
These tests validate model instantiation and enum coverage
without requiring a live database connection.
"""

import uuid
import pytest

from app.domain.models.enums import (
    ProcessingStatus, FilingType, StatementType,
    RatioCategory, RatioSignal, RiskClass,
    FraudRiskClass, AltmanZone, SentimentLabel,
    UserRole, MessageRole, SectionType,
    ForecastMetric, ForecastModel,
)
from app.domain.models.user import User
from app.domain.models.company import Company
from app.domain.models.filing import Filing
from app.domain.models.document_chunk import DocumentChunk
from app.domain.models.financial_statement import FinancialStatement
from app.domain.models.financial_ratio import FinancialRatio
from app.domain.models.nlp_insight import NLPInsight
from app.domain.models.risk_prediction import RiskPrediction
from app.domain.models.fraud_assessment import FraudAssessment
from app.domain.models.forecast import Forecast
from app.domain.models.chat import ChatSession, ChatMessage
from app.domain.models.report import GeneratedReport


class TestEnums:
    """Validate all enum values are correctly defined."""

    def test_processing_status_has_all_pipeline_stages(self):
        stages = [s.value for s in ProcessingStatus]
        assert "PENDING" in stages
        assert "COMPLETE" in stages
        assert "FAILED" in stages
        assert len(stages) == 11

    def test_risk_class_covers_full_range(self):
        classes = [c.value for c in RiskClass]
        assert set(classes) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def test_beneish_fraud_classes(self):
        classes = [c.value for c in FraudRiskClass]
        assert "SAFE" in classes
        assert "MANIPULATOR" in classes

    def test_altman_zones(self):
        zones = [z.value for z in AltmanZone]
        assert set(zones) == {"SAFE", "GREY", "DISTRESS"}

    def test_sentiment_labels(self):
        labels = [l.value for l in SentimentLabel]
        assert set(labels) == {"POSITIVE", "NEGATIVE", "NEUTRAL"}

    def test_section_types_include_mda_and_risk(self):
        types = [t.value for t in SectionType]
        assert "MD_AND_A" in types
        assert "RISK_FACTORS" in types

    def test_forecast_metrics(self):
        metrics = [m.value for m in ForecastMetric]
        assert "REVENUE" in metrics
        assert "NET_PROFIT" in metrics
        assert "EBITDA" in metrics
        assert "OPERATING_CASH_FLOW" in metrics


class TestModelInstantiation:
    """Validate that all models can be instantiated without DB."""

    def test_user_model_instantiation(self):
        user = User(
            email="test@finsight.ai",
            password_hash="hashed_password",
            full_name="Test Analyst",
            role=UserRole.ANALYST,
        )
        assert user.email == "test@finsight.ai"
        assert user.role == UserRole.ANALYST

    def test_company_model_instantiation(self):
        company = Company(
            name="Tata Consultancy Services",
            ticker="TCS",
            sector="Information Technology",
            country="India",
            created_by=uuid.uuid4(),
        )
        assert company.ticker == "TCS"
        assert company.country == "India"

    def test_filing_model_instantiation(self):
        filing = Filing(
            company_id=uuid.uuid4(),
            uploaded_by=uuid.uuid4(),
            filing_type=FilingType.ANNUAL_REPORT,
            fiscal_year=2023,
            fiscal_period="FY",
            file_name="tcs_annual_report_2023.pdf",
            file_path="/uploads/tcs/tcs_annual_report_2023.pdf",
            file_size_bytes=5_242_880,
        )
        assert filing.processing_status == ProcessingStatus.PENDING
        assert filing.fiscal_year == 2023

    def test_document_chunk_instantiation(self):
        chunk = DocumentChunk(
            filing_id=uuid.uuid4(),
            chunk_index=0,
            chunk_text="The company reported strong revenue growth of 15%...",
            page_number=5,
            section_type=SectionType.MD_AND_A,
            token_count=128,
            char_count=512,
        )
        assert chunk.is_embedded is False
        assert chunk.section_type == SectionType.MD_AND_A

    def test_financial_statement_instantiation(self):
        stmt = FinancialStatement(
            filing_id=uuid.uuid4(),
            statement_type=StatementType.INCOME_STATEMENT,
            currency="INR",
            unit_multiplier=10_000_000,
            raw_data={"headers": ["Item", "2023", "2022"]},
            normalized_data={
                "total_revenue": 2_250_000_000,
                "net_income": 380_000_000,
            },
        )
        assert stmt.statement_type == StatementType.INCOME_STATEMENT
        assert stmt.normalized_data["total_revenue"] == 2_250_000_000

    def test_financial_ratio_instantiation(self):
        ratio = FinancialRatio(
            filing_id=uuid.uuid4(),
            ratio_category=RatioCategory.LIQUIDITY,
            ratio_name="Current Ratio",
            formula="Current Assets / Current Liabilities",
            computed_value=1.85,
            benchmark_value=1.5,
            signal=RatioSignal.GOOD,
            interpretation="Strong short-term liquidity position.",
        )
        assert ratio.signal == RatioSignal.GOOD
        assert ratio.computed_value == 1.85

    def test_risk_prediction_instantiation(self):
        pred = RiskPrediction(
            filing_id=uuid.uuid4(),
            risk_score=67.5,
            risk_class=RiskClass.HIGH,
            xgb_score=0.68,
            lgbm_score=0.67,
            feature_vector={"roe": 0.08, "current_ratio": 1.1},
            shap_values={"debt_to_equity": 0.18},
            top_factors=[{"factor": "debt_to_equity", "impact": 0.18}],
            model_version="v1.0",
        )
        assert pred.risk_class == RiskClass.HIGH
        assert pred.risk_score == 67.5

    def test_fraud_assessment_instantiation(self):
        fraud = FraudAssessment(
            filing_id=uuid.uuid4(),
            beneish_score=-1.89,
            beneish_signal=FraudRiskClass.GREY_ZONE,
            altman_score=2.1,
            altman_zone=AltmanZone.GREY,
            fraud_risk_class=FraudRiskClass.GREY_ZONE,
            red_flags=[{"flag": "DSRI > 1.465", "severity": "MEDIUM"}],
            model_version="v1.0",
        )
        assert fraud.altman_zone == AltmanZone.GREY
        assert len(fraud.red_flags) == 1

    def test_forecast_instantiation(self):
        forecast = Forecast(
            filing_id=uuid.uuid4(),
            metric_name=ForecastMetric.REVENUE,
            model_used=ForecastModel.PROPHET,
            historical_data=[
                {"year": 2021, "value": 1_800_000_000},
                {"year": 2022, "value": 2_000_000_000},
                {"year": 2023, "value": 2_250_000_000},
            ],
            data_points_count=3,
            forecast_data=[
                {"ds": "2024-03-31", "yhat": 2_500_000_000,
                 "yhat_lower": 2_300_000_000, "yhat_upper": 2_700_000_000},
            ],
            forecast_years=3,
            trend_direction="UPWARD",
        )
        assert forecast.model_used == ForecastModel.PROPHET
        assert forecast.trend_direction == "UPWARD"

    def test_chat_models_instantiation(self):
        session = ChatSession(
            filing_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="What are the major risks?",
        )
        assert session.message_count == 0

        message = ChatMessage(
            session_id=uuid.uuid4(),
            role=MessageRole.USER,
            content="What are the major risks mentioned in this report?",
        )
        assert message.role == MessageRole.USER

    def test_nlp_insight_instantiation(self):
        nlp = NLPInsight(
            filing_id=uuid.uuid4(),
            sentiment_label=SentimentLabel.POSITIVE,
            sentiment_score=0.82,
            sentiment_section="MD&A",
            risk_sentence_count=12,
            high_risk_count=3,
            overall_tone=SentimentLabel.POSITIVE,
        )
        assert nlp.sentiment_label == SentimentLabel.POSITIVE
        assert nlp.high_risk_count == 3


class TestModelTableNames:
    """Verify all models have correct __tablename__ definitions."""

    def test_all_table_names(self):
        assert User.__tablename__ == "users"
        assert Company.__tablename__ == "companies"
        assert Filing.__tablename__ == "filings"
        assert DocumentChunk.__tablename__ == "document_chunks"
        assert FinancialStatement.__tablename__ == "financial_statements"
        assert FinancialRatio.__tablename__ == "financial_ratios"
        assert NLPInsight.__tablename__ == "nlp_insights"
        assert RiskPrediction.__tablename__ == "risk_predictions"
        assert FraudAssessment.__tablename__ == "fraud_assessments"
        assert Forecast.__tablename__ == "forecasts"
        assert ChatSession.__tablename__ == "chat_sessions"
        assert ChatMessage.__tablename__ == "chat_messages"
        assert GeneratedReport.__tablename__ == "generated_reports"
