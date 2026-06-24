# app/domain/models/nlp_insight.py
"""
NLPInsight model — stores outputs from the full NLP pipeline:
  - FinBERT sentiment analysis on the MD&A section
  - DeBERTa NER entity extraction
  - Risk language detection
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.enums import SentimentLabel
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.filing import Filing


class NLPInsight(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    NLP analysis results for a single filing.
    One NLPInsight record per filing (1:1 relationship).

    Three sub-pipelines write to this model:

    1. FinBERT Sentiment (sentiment_* columns):
       Analyzes the tone of the MD&A section.
       sentiment_raw stores per-sentence results for debugging/audit.

    2. DeBERTa NER (entities, entity_summary columns):
       Extracts named entities: company names, monetary amounts, dates.
       entity_summary provides a clean grouped view.

    3. Risk Language Detection (risk_sentences, risk_* columns):
       Identifies sentences that signal financial risk.
       Each risk sentence includes its risk_type and a confidence score.

    JSONB schema for entities:
        [{"text": "Tata Consultancy Services", "label": "ORG",
          "start": 42, "end": 67, "confidence": 0.98}, ...]

    JSONB schema for risk_sentences:
        [{"text": "...", "page": 23, "risk_score": 0.91,
          "risk_type": "LIQUIDITY_RISK"}, ...]
    """
    __tablename__ = "nlp_insights"

    # ── Document reference ────────────────────────────────────────────────
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── FinBERT Sentiment ─────────────────────────────────────────────────
    sentiment_label: Mapped[SentimentLabel | None] = mapped_column(
        Enum(SentimentLabel, name="sentiment_label", create_type=True),
        nullable=True,
    )
    sentiment_score: Mapped[float | None] = mapped_column(
        Numeric(6, 5), nullable=True
    )  # Confidence score 0.00000 to 1.00000
    sentiment_section: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Which section was analyzed e.g. "MD&A"
    sentiment_raw: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # Full per-sentence FinBERT output

    # ── DeBERTa NER ───────────────────────────────────────────────────────
    entities: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # List of entity dicts with text, label, position, confidence
    entity_summary: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # Grouped: {companies: [...], amounts: [...], dates: [...]}

    # ── Risk Language Detection ───────────────────────────────────────────
    risk_sentences: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # List of risk-flagged sentences with scores and types
    risk_sentence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    high_risk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )  # Sentences with risk_score > 0.8

    # ── Overall document tone ─────────────────────────────────────────────
    overall_tone: Mapped[SentimentLabel | None] = mapped_column(
        Enum(SentimentLabel, name="sentiment_label"),
        nullable=True,
    )
    tone_confidence: Mapped[float | None] = mapped_column(
        Numeric(6, 5), nullable=True
    )

    # ── Model versioning ──────────────────────────────────────────────────
    model_versions: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {"finbert": "ProsusAI/finbert", "deberta": "dslim/bert-base-NER"}

    # ── Relationships ─────────────────────────────────────────────────────
    filing: Mapped["Filing"] = relationship(
        "Filing", back_populates="nlp_insight"
    )

    # ── Constraints and indexes ───────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("filing_id", name="uq_nlp_insight_per_filing"),
        Index("idx_nlp_filing_id", "filing_id"),
        Index("idx_nlp_sentiment", "sentiment_label"),
        Index(
            "idx_nlp_entities_gin",
            "entities",
            postgresql_using="gin",
        ),
        Index(
            "idx_nlp_risk_sentences_gin",
            "risk_sentences",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<NLPInsight id={self.id} filing_id={self.filing_id} "
            f"sentiment={self.sentiment_label} risk_count={self.risk_sentence_count}>"
        )
