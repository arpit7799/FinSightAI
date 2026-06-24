# app/domain/schemas/document.py
"""
Pydantic schemas for the documents API.
Request bodies and response shapes.
"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.domain.models.enums import ProcessingStatus, FilingType


class CompanyCreate(BaseModel):
    name: str
    ticker: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str = "India"


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    ticker: str | None
    sector: str | None
    country: str

    model_config = {"from_attributes": True}


class FilingResponse(BaseModel):
    id: UUID
    company_id: UUID
    filing_type: FilingType
    fiscal_year: int
    fiscal_period: str
    file_name: str
    file_size_bytes: int
    page_count: int | None
    processing_status: ProcessingStatus
    processing_error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FilingStatusResponse(BaseModel):
    filing_id: UUID
    status: ProcessingStatus
    progress_message: str

    model_config = {"from_attributes": True}


class StatementResponse(BaseModel):
    statement_type: str
    normalized_data: dict
    extraction_confidence: float | None
    currency: str

    model_config = {"from_attributes": True}
