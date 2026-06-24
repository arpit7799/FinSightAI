# app/services/document_service.py
"""
Business logic for document uploads.

The service layer sits between the API route and the repository.
The route handles HTTP stuff, the service handles business logic,
the repository handles database stuff.
"""

import os
import uuid
import aiofiles
import structlog

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.models.filing import Filing
from app.domain.models.company import Company
from app.domain.models.enums import FilingType, ProcessingStatus
from app.repositories.filing_repository import FilingRepository
from app.repositories.company_repository import CompanyRepository

logger = structlog.get_logger()

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Convert MB to bytes


class DocumentService:

    def __init__(self, db: Session):
        self.db = db
        self.filing_repo = FilingRepository(db)
        self.company_repo = CompanyRepository(db)

    async def upload_filing(
        self,
        file: UploadFile,
        company_id: str,
        fiscal_year: int,
        filing_type: str,
        uploaded_by_id: str,
    ) -> Filing:
        """
        Handle a PDF upload:
        1. Validate the file
        2. Create or verify the company exists
        3. Save the file to disk
        4. Create a Filing record in the database
        5. Kick off the background processing task
        """

        # ── Validate file ─────────────────────────────────────────────────
        self._validate_file(file)

        # ── Check company exists ──────────────────────────────────────────
        company = self.company_repo.get_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # ── Save file to disk ─────────────────────────────────────────────
        file_path = await self._save_file(file, company_id)

        # ── Get file size ─────────────────────────────────────────────────
        file_size = os.path.getsize(file_path)

        # ── Create Filing record ──────────────────────────────────────────
        try:
            filing_type_enum = FilingType(filing_type)
        except ValueError:
            filing_type_enum = FilingType.ANNUAL_REPORT

        filing = Filing(
            company_id=company_id,
            uploaded_by=uploaded_by_id,
            filing_type=filing_type_enum,
            fiscal_year=fiscal_year,
            fiscal_period="FY",
            file_name=file.filename,
            file_path=file_path,
            file_size_bytes=file_size,
            processing_status=ProcessingStatus.PENDING,
        )

        filing = self.filing_repo.create(filing)

        logger.info(
            "filing_created",
            filing_id=str(filing.id),
            company_id=company_id,
            fiscal_year=fiscal_year,
            file_name=file.filename,
        )

        # ── Enqueue background task ───────────────────────────────────────
        # Import here to avoid circular imports
        from app.workers.document_tasks import process_filing_task

        process_filing_task.delay(str(filing.id), file_path)

        logger.info("processing_task_queued", filing_id=str(filing.id))

        return filing

    def _validate_file(self, file: UploadFile) -> None:
        """Check file type. Size is checked after saving."""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        extension = os.path.splitext(file.filename)[1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are allowed. Got: {extension}",
            )

    async def _save_file(self, file: UploadFile, company_id: str) -> str:
        """
        Save the uploaded file to disk.
        Creates a folder per company: uploads/{company_id}/
        """
        # Create company upload directory
        company_dir = os.path.join(settings.UPLOAD_DIR, company_id)
        os.makedirs(company_dir, exist_ok=True)

        # Generate unique filename to avoid collisions
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{unique_id}_{file.filename}"
        file_path = os.path.join(company_dir, safe_filename)

        # Write file to disk asynchronously
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()

            # Check size after reading
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB}MB",
                )

            await f.write(content)

        logger.info("file_saved", path=file_path, size_bytes=len(content))
        return file_path

    def get_filing_status(self, filing_id: str, user_id: str) -> Filing:
        """Get filing and verify the user owns it."""
        filing = self.filing_repo.get_by_id(filing_id)

        if not filing:
            raise HTTPException(status_code=404, detail="Filing not found")

        # Users can only see their own filings (admins can see all - handled in route)
        if str(filing.uploaded_by) != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return filing

    def create_company(
        self,
        name: str,
        ticker: str | None,
        sector: str | None,
        created_by_id: str,
    ) -> Company:
        """Create a new company record."""

        # Check if ticker already exists
        if ticker:
            existing = self.company_repo.get_by_ticker(ticker)
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Company with ticker {ticker} already exists",
                )

        company = Company(
            name=name,
            ticker=ticker.upper() if ticker else None,
            sector=sector,
            created_by=created_by_id,
        )

        return self.company_repo.create(company)
