from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import JSON

from sqlalchemy.orm import relationship

from app.core.database import Base


class NLPAnalysis(Base):
    __tablename__ = "nlp_analysis"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    report_id = Column(
        Integer,
        ForeignKey("reports.id"),
        nullable=False,
        unique=True,
    )

    tokens = Column(JSON)

    lemmas = Column(JSON)

    named_entities = Column(JSON)

    financial_keywords = Column(JSON)

    processed_sentences = Column(JSON)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    report = relationship(
        "Report",
        back_populates="nlp_result",
    )