from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class FinancialDataResponse(BaseModel):

    id: int

    report_id: int

    revenue: float | None

    net_income: float | None

    operating_income: float | None

    total_assets: float | None

    total_liabilities: float | None

    total_equity: float | None

    cash: float | None

    inventory: float | None

    receivables: float | None

    debt: float | None

    eps: float | None

    operating_cash_flow: float | None

    free_cash_flow: float | None

    shares_outstanding: float | None

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )