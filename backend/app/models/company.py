from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base

from sqlalchemy.orm import relationship

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)

    company_name = Column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )

    ticker_symbol = Column(
        String(20),
        nullable=True,
    )

    industry = Column(
        String(100),
        nullable=True,
    )

    sector = Column(
        String(100),
        nullable=True,
    )

    country = Column(
        String(100),
        nullable=True,
    )

    exchange = Column(
        String(50),
        nullable=True,
    )

    website = Column(
        String(255),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    reports = relationship(
    "Report",
    back_populates="company",
    cascade="all, delete-orphan",
    )