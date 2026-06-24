# app/workers/document_tasks.py
"""
Celery task for processing uploaded PDF filings.

This is the main background job that runs when a user uploads a PDF.
It runs all the document intelligence steps in sequence and
updates the filing status in the database as it goes.

The status progression is:
PENDING → EXTRACTING → EXTRACTED → ANALYZING → COMPLETE (or FAILED)
"""

import structlog
from celery import shared_task
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.domain.models.enums import ProcessingStatus, StatementType
from app.domain.models.financial_statement import FinancialStatement
from app.domain.models.document_chunk import DocumentChunk
from app.domain.models.enums import SectionType
from app.engines.document_intelligence.pdf_processor import PDFProcessor
from app.engines.document_intelligence.ocr_processor import OCRProcessor
from app.engines.document_intelligence.table_extractor import TableExtractor
from app.engines.document_intelligence.statement_classifier import classify_all_tables
from app.engines.document_intelligence.data_normalizer import normalize_all_statements
from app.repositories.filing_repository import FilingRepository

logger = structlog.get_logger()


def _update_status(db: Session, filing_id: str, status: ProcessingStatus, error: str = None):
    """Helper to update filing status and log it."""
    repo = FilingRepository(db)
    repo.update_status(filing_id, status, error)
    logger.info("filing_status_updated", filing_id=filing_id, status=status.value)


def _create_chunks_from_pages(pages: list, filing_id: str) -> list:
    """
    Turn extracted pages into DocumentChunk objects for RAG.

    Each page becomes one chunk for now.
    (Phase 6 will implement proper semantic chunking with BGE embeddings)
    """
    chunks = []
    for i, page in enumerate(pages):
        text = page["text"].strip()
        if not text:
            continue  # Skip empty pages

        chunk = DocumentChunk(
            filing_id=filing_id,
            chunk_index=i,
            chunk_text=text,
            page_number=page["page_number"],
            section_type=SectionType.UNKNOWN,  # Section detection in Phase 6
            token_count=len(text.split()),  # Rough token estimate
            char_count=len(text),
            is_embedded=False,  # Embeddings happen in Phase 6
        )
        chunks.append(chunk)

    return chunks


def _create_financial_statements(normalized_data: dict, filing_id: str) -> list:
    """
    Turn normalized table data into FinancialStatement objects.
    """
    # Map string keys to StatementType enum
    type_map = {
        "BALANCE_SHEET": StatementType.BALANCE_SHEET,
        "INCOME_STATEMENT": StatementType.INCOME_STATEMENT,
        "CASH_FLOW_STATEMENT": StatementType.CASH_FLOW_STATEMENT,
    }

    statements = []
    for type_key, data in normalized_data.items():
        stmt_type = type_map.get(type_key)
        if not stmt_type:
            continue

        statement = FinancialStatement(
            filing_id=filing_id,
            statement_type=stmt_type,
            currency="INR",
            unit_multiplier=1,
            raw_data=data["raw_data"],
            normalized_data=data["normalized_data"],
            extraction_confidence=data["extraction_confidence"],
            extraction_method="pdfplumber",
        )
        statements.append(statement)

    return statements


@shared_task(bind=True, max_retries=3)
def process_filing_task(self, filing_id: str, file_path: str):
    """
    Main document processing task.

    Steps:
    1. Extract text from PDF (PyMuPDF)
    2. Run OCR if needed (PaddleOCR)
    3. Extract tables (pdfplumber)
    4. Classify tables (rule-based)
    5. Normalize financial data
    6. Save chunks and statements to database
    7. Mark filing as COMPLETE

    If anything fails, mark filing as FAILED with error message.
    """
    db = SessionLocal()

    try:
        logger.info("document_processing_started", filing_id=filing_id)

        # ── Step 1: Extract text ──────────────────────────────────────────
        _update_status(db, filing_id, ProcessingStatus.EXTRACTING)

        pdf_processor = PDFProcessor(file_path)
        pdf_result = pdf_processor.extract()

        # ── Step 2: OCR if needed ─────────────────────────────────────────
        if pdf_result["needs_ocr"]:
            logger.info("ocr_required", filing_id=filing_id,
                       reason="low_text_density",
                       avg_chars=pdf_result["avg_chars_per_page"])
            ocr_processor = OCRProcessor(file_path)
            pdf_result = ocr_processor.extract()

        _update_status(db, filing_id, ProcessingStatus.EXTRACTED)

        # ── Step 3: Extract tables ────────────────────────────────────────
        table_extractor = TableExtractor(file_path)
        raw_tables = table_extractor.extract()

        logger.info("tables_extracted", filing_id=filing_id, count=len(raw_tables))

        # ── Step 4: Classify tables ───────────────────────────────────────
        classified_tables = classify_all_tables(raw_tables)

        logger.info("tables_classified", filing_id=filing_id,
                   types=[t["statement_type"] for t in classified_tables])

        # ── Step 5: Normalize financial data ──────────────────────────────
        normalized_data = normalize_all_statements(classified_tables)

        # ── Step 6: Save to database ──────────────────────────────────────
        _update_status(db, filing_id, ProcessingStatus.ANALYZING)

        # Save document chunks for RAG (Phase 6 will add embeddings)
        chunks = _create_chunks_from_pages(pdf_result["pages"], filing_id)
        db.add_all(chunks)

        # Save financial statements for ratio analysis (Phase 5)
        statements = _create_financial_statements(normalized_data, filing_id)
        db.add_all(statements)

        # Update filing with page count
        repo = FilingRepository(db)
        repo.update_page_count(filing_id, pdf_result["page_count"])

        db.commit()

        # ── Step 7: Mark complete ─────────────────────────────────────────
        _update_status(db, filing_id, ProcessingStatus.COMPLETE)

        logger.info(
            "document_processing_complete",
            filing_id=filing_id,
            pages=pdf_result["page_count"],
            chunks=len(chunks),
            statements=len(statements),
        )

        return {
            "filing_id": filing_id,
            "status": "COMPLETE",
            "pages": pdf_result["page_count"],
            "chunks_created": len(chunks),
            "statements_found": [s.statement_type.value for s in statements],
        }

    except Exception as e:
        # Mark filing as failed with the error message
        error_msg = str(e)
        logger.error("document_processing_failed",
                    filing_id=filing_id, error=error_msg)
        _update_status(db, filing_id, ProcessingStatus.FAILED, error=error_msg)

        # Retry the task (Celery will wait before retrying)
        raise self.retry(exc=e, countdown=30)

    finally:
        db.close()
