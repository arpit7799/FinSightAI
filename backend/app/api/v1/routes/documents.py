# app/api/v1/routes/documents.py
"""
API routes for document upload and management.

Endpoints:
    POST   /companies              - Create a company
    GET    /companies              - List all companies
    POST   /documents/upload       - Upload a PDF filing
    GET    /documents/{filing_id}/status     - Check processing status
    GET    /documents/{filing_id}/statements - Get extracted financials
    GET    /documents/             - List my filings
    DELETE /documents/{filing_id}  - Soft delete a filing
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.domain.models.enums import ProcessingStatus
from app.domain.schemas.document import (
    CompanyCreate,
    CompanyResponse,
    FilingResponse,
    FilingStatusResponse,
    StatementResponse,
)
from app.repositories.filing_repository import FilingRepository
from app.repositories.statement_repository import StatementRepository
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


# ── Company endpoints ─────────────────────────────────────────────────────────

@router.post("/companies", response_model=CompanyResponse)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN", "ANALYST")),
):
    """Create a new company to associate filings with."""
    service = DocumentService(db)
    return service.create_company(
        name=payload.name,
        ticker=payload.ticker,
        sector=payload.sector,
        created_by_id=str(current_user.id),
    )


@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all companies."""
    from app.repositories.company_repository import CompanyRepository
    return CompanyRepository(db).get_all()


# ── Filing endpoints ──────────────────────────────────────────────────────────

@router.post("/upload", response_model=FilingResponse)
async def upload_filing(
    file: UploadFile = File(...),
    company_id: str = Form(...),
    fiscal_year: int = Form(...),
    filing_type: str = Form(default="ANNUAL_REPORT"),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN", "ANALYST")),
):
    """
    Upload a PDF annual report or financial filing.

    The file is saved to disk and a background task is queued
    to extract text, tables, and financial data.

    Use the /status endpoint to poll processing progress.
    """
    service = DocumentService(db)
    filing = await service.upload_filing(
        file=file,
        company_id=company_id,
        fiscal_year=fiscal_year,
        filing_type=filing_type,
        uploaded_by_id=str(current_user.id),
    )
    return filing


@router.get("/{filing_id}/status", response_model=FilingStatusResponse)
def get_filing_status(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Check the processing status of a filing.
    Poll this endpoint every few seconds after uploading.
    """
    # Admins can see any filing, analysts only their own
    if current_user.role.value == "ADMIN":
        filing = FilingRepository(db).get_by_id(filing_id)
    else:
        service = DocumentService(db)
        filing = service.get_filing_status(filing_id, str(current_user.id))

    if not filing:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Filing not found")

    # Human-readable progress message
    progress_messages = {
        ProcessingStatus.PENDING: "Waiting to start...",
        ProcessingStatus.EXTRACTING: "Extracting text from PDF...",
        ProcessingStatus.EXTRACTED: "Text extracted. Detecting tables...",
        ProcessingStatus.ANALYZING: "Analyzing financial statements...",
        ProcessingStatus.COMPLETE: "Processing complete!",
        ProcessingStatus.FAILED: f"Processing failed: {filing.processing_error}",
    }

    return FilingStatusResponse(
        filing_id=filing.id,
        status=filing.processing_status,
        progress_message=progress_messages.get(filing.processing_status, "Processing..."),
    )


@router.get("/{filing_id}/statements", response_model=list[StatementResponse])
def get_statements(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get extracted financial statements for a filing.
    Returns Balance Sheet, Income Statement, and Cash Flow data.
    """
    statements = StatementRepository(db).get_by_filing_id(filing_id)

    if not statements:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail="No financial statements found. Processing may still be running.",
        )

    return [
        StatementResponse(
            statement_type=s.statement_type.value,
            normalized_data=s.normalized_data,
            extraction_confidence=float(s.extraction_confidence) if s.extraction_confidence else None,
            currency=s.currency,
        )
        for s in statements
    ]


@router.get("/", response_model=list[FilingResponse])
def list_my_filings(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all filings uploaded by the current user."""
    return FilingRepository(db).get_all_for_user(
        str(current_user.id), skip=skip, limit=limit
    )


@router.delete("/{filing_id}")
def delete_filing(
    filing_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("ADMIN", "ANALYST")),
):
    """Soft delete a filing (marks as deleted, data is preserved)."""
    success = FilingRepository(db).soft_delete(filing_id)

    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Filing not found")

    return {"message": "Filing deleted successfully"}
