# app/domain/models/enums.py
"""
All PostgreSQL ENUM types used across FinSight AI models.
Defined once here; imported by every model that needs them.
Using Python's native enum.Enum ensures type safety at both
the Python and PostgreSQL levels.
"""

import enum


class ProcessingStatus(str, enum.Enum):
    """
    Lifecycle states for a filing as it moves through the processing pipeline.
    Order reflects the actual pipeline sequence.
    """
    PENDING       = "PENDING"        # Uploaded, not yet processed
    EXTRACTING    = "EXTRACTING"     # PDF text/table extraction running
    EXTRACTED     = "EXTRACTED"      # Extraction complete
    NLP_PROCESSING = "NLP_PROCESSING" # FinBERT + DeBERTa NLP running
    NLP_COMPLETE  = "NLP_COMPLETE"   # NLP pipeline complete
    EMBEDDING     = "EMBEDDING"      # BGE chunking + Qdrant indexing running
    INDEXED       = "INDEXED"        # All chunks embedded and stored in Qdrant
    ANALYZING     = "ANALYZING"      # Financial ratio + ML risk analysis running
    ANALYZED      = "ANALYZED"       # All analysis complete
    COMPLETE      = "COMPLETE"       # Fully processed — available to users
    FAILED        = "FAILED"         # Unrecoverable error; see processing_error


class FilingType(str, enum.Enum):
    """Type of financial document uploaded."""
    ANNUAL_REPORT      = "ANNUAL_REPORT"
    FORM_10K           = "10K"
    FORM_10Q           = "10Q"
    BALANCE_SHEET      = "BALANCE_SHEET"
    INCOME_STATEMENT   = "INCOME_STATEMENT"
    CASH_FLOW          = "CASH_FLOW"


class StatementType(str, enum.Enum):
    """Type of financial statement extracted from a filing."""
    BALANCE_SHEET        = "BALANCE_SHEET"
    INCOME_STATEMENT     = "INCOME_STATEMENT"
    CASH_FLOW_STATEMENT  = "CASH_FLOW_STATEMENT"


class RatioCategory(str, enum.Enum):
    """Category grouping for financial ratios."""
    LIQUIDITY     = "LIQUIDITY"
    PROFITABILITY = "PROFITABILITY"
    LEVERAGE      = "LEVERAGE"
    EFFICIENCY    = "EFFICIENCY"
    MARKET        = "MARKET"


class RatioSignal(str, enum.Enum):
    """
    Traffic-light health signal for a computed financial ratio
    relative to its industry benchmark.
    """
    GOOD     = "GOOD"     # Ratio within or better than benchmark
    WARNING  = "WARNING"  # Ratio approaching concerning territory
    CRITICAL = "CRITICAL" # Ratio significantly outside safe range
    NEUTRAL  = "NEUTRAL"  # Insufficient benchmark data to classify


class RiskClass(str, enum.Enum):
    """ML model risk classification output."""
    LOW      = "LOW"      # Risk score 0–29
    MEDIUM   = "MEDIUM"   # Risk score 30–59
    HIGH     = "HIGH"     # Risk score 60–79
    CRITICAL = "CRITICAL" # Risk score 80–100


class FraudRiskClass(str, enum.Enum):
    """Beneish M-Score and overall fraud risk classification."""
    SAFE         = "SAFE"         # No manipulation signals
    GREY_ZONE    = "GREY_ZONE"    # Ambiguous; requires investigation
    MANIPULATOR  = "MANIPULATOR"  # Strong manipulation signals detected


class AltmanZone(str, enum.Enum):
    """Altman Z-Score bankruptcy risk zone."""
    SAFE     = "SAFE"     # Z > 2.99 — unlikely to go bankrupt
    GREY     = "GREY"     # 1.81 < Z < 2.99 — uncertain
    DISTRESS = "DISTRESS" # Z < 1.81 — high bankruptcy risk


class SentimentLabel(str, enum.Enum):
    """FinBERT sentiment classification output."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL  = "NEUTRAL"


class UserRole(str, enum.Enum):
    """RBAC roles for access control."""
    ADMIN   = "ADMIN"   # Full system access
    ANALYST = "ANALYST" # Can upload, analyze, view all
    VIEWER  = "VIEWER"  # Read-only access


class MessageRole(str, enum.Enum):
    """Role of a message in the RAG chat conversation."""
    USER      = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM    = "SYSTEM"


class SectionType(str, enum.Enum):
    """
    Document section classification for chunks.
    Used to filter RAG retrieval by section.
    """
    COVER                 = "COVER"
    MD_AND_A              = "MD_AND_A"              # Management Discussion & Analysis
    RISK_FACTORS          = "RISK_FACTORS"
    FINANCIAL_STATEMENTS  = "FINANCIAL_STATEMENTS"
    NOTES_TO_FINANCIALS   = "NOTES_TO_FINANCIALS"
    AUDITOR_REPORT        = "AUDITOR_REPORT"
    APPENDIX              = "APPENDIX"
    UNKNOWN               = "UNKNOWN"


class ForecastMetric(str, enum.Enum):
    """Financial metrics available for forecasting."""
    REVENUE              = "REVENUE"
    NET_PROFIT           = "NET_PROFIT"
    EBITDA               = "EBITDA"
    OPERATING_CASH_FLOW  = "OPERATING_CASH_FLOW"


class ForecastModel(str, enum.Enum):
    """Forecasting model used."""
    PROPHET = "PROPHET"
    ARIMA   = "ARIMA"
