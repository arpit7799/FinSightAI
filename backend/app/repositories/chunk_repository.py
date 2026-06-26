# app/repositories/chunk_repository.py
"""
Database operations for DocumentChunk records.
"""

from sqlalchemy.orm import Session
from app.domain.models.document_chunk import DocumentChunk


class ChunkRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_filing_id(self, filing_id: str) -> list[DocumentChunk]:
        """Get all chunks for a filing, ordered by chunk index."""
        return (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.filing_id == filing_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

    def get_unembedded(self, filing_id: str) -> list[DocumentChunk]:
        """Get chunks that haven't been embedded in Qdrant yet."""
        return (
            self.db.query(DocumentChunk)
            .filter(
                DocumentChunk.filing_id == filing_id,
                DocumentChunk.is_embedded == False,
            )
            .all()
        )

    def delete_by_filing_id(self, filing_id: str) -> int:
        """
        Delete all chunks for a filing from the database.
        Used during re-indexing to cleanly replace old chunks
        before creating new ones in the same transaction.

        Returns the number of deleted rows.
        Does NOT commit — caller controls the transaction boundary.
        """
        count = (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.filing_id == filing_id)
            .delete(synchronize_session="fetch")
        )
        return count

    def mark_embedded(self, chunk_id: str, embedding_id: str) -> None:
        """Mark a chunk as embedded and store its Qdrant point ID."""
        chunk = self.db.query(DocumentChunk).filter(
            DocumentChunk.id == chunk_id
        ).first()

        if chunk:
            chunk.is_embedded = True
            chunk.embedding_id = embedding_id
            self.db.commit()

    def mark_all_embedded(self, updates: list[dict]) -> None:
        """
        Batch update — mark multiple chunks as embedded at once.
        updates: [{"chunk_id": "uuid", "embedding_id": "qdrant-uuid"}]

        Uses bulk UPDATE for better performance instead of
        individual SELECT + UPDATE per chunk.
        Does NOT commit — caller controls the transaction boundary.
        """
        if not updates:
            return

        for update in updates:
            (
                self.db.query(DocumentChunk)
                .filter(DocumentChunk.id == update["chunk_id"])
                .update(
                    {
                        DocumentChunk.is_embedded: True,
                        DocumentChunk.embedding_id: update["embedding_id"],
                    },
                    synchronize_session="fetch",
                )
            )

    def save_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Save a list of new chunk records."""
        self.db.add_all(chunks)
        self.db.commit()