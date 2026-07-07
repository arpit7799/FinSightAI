from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CompanyBase(BaseModel):
    company_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )

    ticker_symbol: Optional[str] = Field(
        default=None,
        max_length=20,
    )

    industry: Optional[str] = None

    sector: Optional[str] = None

    country: Optional[str] = None

    exchange: Optional[str] = None

    website: Optional[HttpUrl] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    company_name: Optional[str] = None
    ticker_symbol: Optional[str] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    exchange: Optional[str] = None
    website: Optional[HttpUrl] = None


class CompanyResponse(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)