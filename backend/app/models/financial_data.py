from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class FinancialData(Base):
    __tablename__ = "financial_data"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    report_id = Column(
        Integer,
        ForeignKey("reports.id"),
        unique=True,
        nullable=False,
    )

    revenue = Column(Float)

    net_income = Column(Float)

    operating_income = Column(Float)

    total_assets = Column(Float)

    total_liabilities = Column(Float)

    total_equity = Column(Float)

    cash = Column(Float)

    inventory = Column(Float)

    receivables = Column(Float)

    debt = Column(Float)

    eps = Column(Float)

    operating_cash_flow = Column(Float)

    free_cash_flow = Column(Float)

    shares_outstanding = Column(Float)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    report = relationship(
        "Report",
        back_populates="financial_data",
    )