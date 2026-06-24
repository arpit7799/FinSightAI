# app/domain/models/__init__.py
"""
Import all SQLAlchemy models here.

This file MUST import every model so that:
  1. Alembic's --autogenerate can detect all tables.
  2. SQLAlchemy's relationship() can resolve forward references.

Order matters — import parent tables before child tables
to avoid circular import issues at runtime.
"""

from app.domain.models.enums import (  # noqa: F401
    ProcessingStatus,
    FilingType,
    StatementType,
    RatioCategory,
    RatioSignal,
    RiskClass,
    FraudRiskClass,
    AltmanZone,
    SentimentLabel,
    UserRole,
    MessageRole,
    SectionType,
    ForecastMetric,
    ForecastModel,
)

from app.domain.models.user import User                              # noqa: F401
from app.domain.models.company import Company                        # noqa: F401
from app.domain.models.filing import Filing                          # noqa: F401
from app.domain.models.document_chunk import DocumentChunk           # noqa: F401
from app.domain.models.financial_statement import FinancialStatement # noqa: F401
from app.domain.models.financial_ratio import FinancialRatio         # noqa: F401
from app.domain.models.nlp_insight import NLPInsight                 # noqa: F401
from app.domain.models.risk_prediction import RiskPrediction         # noqa: F401
from app.domain.models.fraud_assessment import FraudAssessment       # noqa: F401
from app.domain.models.forecast import Forecast                      # noqa: F401
from app.domain.models.chat import ChatSession, ChatMessage          # noqa: F401
from app.domain.models.report import GeneratedReport                 # noqa: F401

__all__ = [
    "User",
    "Company",
    "Filing",
    "DocumentChunk",
    "FinancialStatement",
    "FinancialRatio",
    "NLPInsight",
    "RiskPrediction",
    "FraudAssessment",
    "Forecast",
    "ChatSession",
    "ChatMessage",
    "GeneratedReport",
]
