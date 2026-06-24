# app/domain/models/document_chunk.py
"""
DocumentChunk model — stores semantic chunks of a filing for RAG retrieval.
Each chunk maps to exactly one Qdrant vector point via embedding_id.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, Enum, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.enums import SectionType
from app.domain.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.filing import Filing


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single semantic chunk of text extracted from a filing PDF.

    Chunks are the atomic unit of the RAG pipeline:
      1. SemanticChunker splits the filing text into these chunks.
      2. EmbeddingGenerator (BGE Large) produces a vector for each chunk.
      3. QdrantIndexer stores the vector in Qdrant, referenced by embedding_id.
      4. HybridRetriever queries Qdrant and returns matching chunks by ID.
      5. LLMGenerator uses chunk_text as context for Llama 3.

    embedding_id links this DB record to its Qdrant vector point,
    enabling us to resolve retrieved Qdrant IDs back to full chunk text,
    page number, and section for citation rendering.
    """
    __tablename__ = "document_chunks"

    # ── Document reference ────────────────────────────────────────────────
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Chunk content ─────────────────────────────────────────────────────
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Sequential position within the filing
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_type: Mapped[SectionType] = mapped_column(
        Enum(SectionType, name="section_type", create_type=True),
        nullable=False,
        default=SectionType.UNKNOWN,
        server_default=SectionType.UNKNOWN.value,
    )
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Qdrant linkage ────────────────────────────────────────────────────
    embedding_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # UUID string of the Qdrant point
    is_embedded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # ── Relationships ─────────────────────────────────────────────────────
    filing: Mapped["Filing"] = relationship("Filing", back_populates="chunks")

    # ── Constraints and indexes ───────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "filing_id", "chunk_index",
            name="uq_chunk_index_per_filing",
        ),
        Index("idx_chunks_filing_id", "filing_id"),
        Index("idx_chunks_section", "filing_id", "section_type"),
        Index("idx_chunks_page", "filing_id", "page_number"),
        # Partial index — only un-embedded chunks, for the embedding worker queue
        Index(
            "idx_chunks_not_embedded",
            "is_embedded",
            postgresql_where="is_embedded = false",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk id={self.id} filing_id={self.filing_id} "
            f"index={self.chunk_index} page={self.page_number}>"
        )
