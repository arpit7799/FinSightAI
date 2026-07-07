from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class FinancialRatio(Base):
    __tablename__ = "financial_ratios"

    id = Column(Integer, primary_key=True, index=True)

    report_id = Column(
        Integer,
        ForeignKey("reports.id"),
        unique=True,
        nullable=False,
    )

    current_ratio = Column(Float)

    quick_ratio = Column(Float)

    cash_ratio = Column(Float)

    roa = Column(Float)

    roe = Column(Float)

    gross_margin = Column(Float)

    operating_margin = Column(Float)

    net_margin = Column(Float)

    asset_turnover = Column(Float)

    inventory_turnover = Column(Float)

    receivables_turnover = Column(Float)

    debt_to_equity = Column(Float)

    debt_to_assets = Column(Float)

    interest_coverage = Column(Float)

    eps = Column(Float)

    book_value_per_share = Column(Float)

    pe_ratio = Column(Float)

    price_to_book = Column(Float)

    dividend_yield = Column(Float)

    health_score = Column(Float)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    report = relationship(
        "Report",
        back_populates="financial_ratio",
    )