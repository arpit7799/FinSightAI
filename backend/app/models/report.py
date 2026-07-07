from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from app.core.database import Base
from sqlalchemy.orm import relationship

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
    )

    original_filename = Column(
        String(255),
        nullable=False,
    )

    stored_filename = Column(
        String(255),
        nullable=False,
        unique=True,
    )

    file_type = Column(
        String(20),
        nullable=False,
    )

    file_size = Column(
        Integer,
        nullable=False,
    )

    upload_date = Column(
        DateTime,
        default=datetime.utcnow,
    )

    company = relationship(
    "Company",
    back_populates="reports",
    )

    ocr_result = relationship(
    "ExtractedText",
    back_populates="report",
    uselist=False,
    cascade="all, delete-orphan",
    )

    nlp_result = relationship(
    "NLPAnalysis",
    back_populates="report",
    uselist=False,
    cascade="all, delete-orphan",
    )