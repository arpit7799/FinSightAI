from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Text

from sqlalchemy.orm import relationship

from app.core.database import Base


class ExtractedText(Base):
    __tablename__ = "extracted_text"

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

    extracted_text = Column(
        Text,
        nullable=False,
    )

    extraction_date = Column(
        DateTime,
        default=datetime.utcnow,
    )

    report = relationship(
        "Report",
        back_populates="ocr_result",
    )