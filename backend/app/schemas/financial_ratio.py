from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class FinancialRatioResponse(BaseModel):

    id: int

    report_id: int

    current_ratio: float | None
    quick_ratio: float | None
    cash_ratio: float | None

    roa: float | None
    roe: float | None
    gross_margin: float | None
    operating_margin: float | None
    net_margin: float | None

    asset_turnover: float | None
    inventory_turnover: float | None
    receivables_turnover: float | None

    debt_to_equity: float | None
    debt_to_assets: float | None
    interest_coverage: float | None

    eps: float | None
    book_value_per_share: float | None
    pe_ratio: float | None
    price_to_book: float | None
    dividend_yield: float | None

    health_score: float | None

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )