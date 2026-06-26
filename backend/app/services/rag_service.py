# app/services/rag_service.py
"""
Business logic for the RAG pipeline.

This service orchestrates:
1. Embedding pipeline (chunking + embedding + Qdrant indexing)
2. Q&A pipeline (retrieve + generate + save to chat history)

The embedding pipeline is transactional: if any step fails
(embedding generation, Qdrant indexing), all database changes
are rolled back so neither PostgreSQL nor Qdrant are left in
a partially updated state.
"""

import time
import structlog
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.domain.models.document_chunk import DocumentChunk
from app.domain.models.enums import MessageRole, ProcessingStatus
from app.engines.rag.chunker import chunk_pages
from app.engines.rag.embedder import EmbeddingGenerator
from app.engines.rag.indexer import QdrantIndexer
from app.engines.rag.retriever import HybridRetriever
from app.engines.rag.llm_generator import LLMGenerator
from app.repositories.filing_repository import FilingRepository
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.chat_repository import ChatRepository

logger = structlog.get_logger()


class RAGService:

    def __init__(self, db: Session):
        self.db = db
        self.filing_repo = FilingRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.chat_repo = ChatRepository(db)

    def embed_filing(self, filing_id: str) -> dict:
        """
        Run the full embedding pipeline for a filing.

        Steps:
        1. Load all chunks from DB (created by Phase 4 document processor)
        2. Re-chunk properly using LangChain semantic chunker
        3. Generate BGE Base embeddings
        4. Store vectors in Qdrant
        5. Update chunk records with embedding_ids
        6. Commit only after all steps succeed (transactional)

        This replaces the rough page-level chunks from Phase 4
        with proper semantic chunks.

        TRANSACTIONAL SAFETY:
        - Old DB chunks are deleted, new ones created, but NOT committed
          until Qdrant indexing also succeeds.
        - If Qdrant fails, db.rollback() restores old chunks.
        - If DB commit fails after Qdrant succeeds, Qdrant vectors are
          cleaned up in the exception handler.
        """
        filing = self.filing_repo.get_by_id(filing_id)
        if not filing:
            raise HTTPException(status_code=404, detail="Filing not found")

        logger.info("embedding_pipeline_started", filing_id=filing_id)

        # Get existing chunks from Phase 4
        existing_chunks = self.chunk_repo.get_by_filing_id(filing_id)

        if not existing_chunks:
            raise HTTPException(
                status_code=422,
                detail="No chunks found. Run document processing first.",
            )

        # Build page-like structure from existing chunks for re-chunking
        pages = [
            {
                "page_number": c.page_number,
                "text": c.chunk_text,
                "char_count": c.char_count,
            }
            for c in existing_chunks
        ]

        # Re-chunk with LangChain semantic chunker
        semantic_chunks = chunk_pages(pages)
        logger.info("semantic_chunking_done", filing_id=filing_id,
                   chunk_count=len(semantic_chunks))

        # Generate embeddings
        embedder = EmbeddingGenerator()
        texts = [c["chunk_text"] for c in semantic_chunks]
        vectors = embedder.embed_documents(texts)

        logger.info("embeddings_generated", filing_id=filing_id,
                   vector_count=len(vectors))

        # Setup Qdrant
        indexer = QdrantIndexer()
        indexer.ensure_collection_exists()

        # ── Begin transactional scope ─────────────────────────────────
        # All DB mutations happen without commit until Qdrant succeeds.
        qdrant_indexed = False

        try:
            # Clean up: delete old Qdrant vectors for this filing
            indexer.delete_filing_vectors(filing_id)

            # Clean up: delete old DB chunks for this filing
            deleted_count = self.chunk_repo.delete_by_filing_id(filing_id)
            logger.info("old_chunks_deleted", filing_id=filing_id,
                       db_chunks_deleted=deleted_count)

            # Create new DocumentChunk records (not committed yet)
            chunks_with_vectors = []
            new_chunk_objects = []

            for i, (chunk, vector) in enumerate(zip(semantic_chunks, vectors)):
                db_chunk = DocumentChunk(
                    filing_id=filing_id,
                    chunk_index=i,
                    chunk_text=chunk["chunk_text"],
                    page_number=chunk["page_number"],
                    section_type=chunk["section_type"],
                    token_count=chunk["token_count"],
                    char_count=chunk["char_count"],
                    is_embedded=False,
                )
                self.db.add(db_chunk)
                self.db.flush()  # get the ID without full commit

                chunks_with_vectors.append({
                    "chunk_db_id": str(db_chunk.id),
                    "filing_id": filing_id,
                    "chunk_text": chunk["chunk_text"],
                    "page_number": chunk["page_number"],
                    "section_type": str(chunk["section_type"]),
                    "chunk_index": i,
                    "vector": vector,
                })
                new_chunk_objects.append(db_chunk)

            # Index in Qdrant — the critical external operation
            point_ids = indexer.index_chunks(chunks_with_vectors)
            qdrant_indexed = True

            # Update DB chunks with their Qdrant point IDs (still no commit)
            updates = [
                {"chunk_id": str(chunk.id), "embedding_id": point_id}
                for chunk, point_id in zip(new_chunk_objects, point_ids)
            ]
            self.chunk_repo.mark_all_embedded(updates)

            # Update filing status (still no commit)
            filing.processing_status = ProcessingStatus.INDEXED
            self.db.flush()

            # ── Atomic commit ─────────────────────────────────────────
            # Everything succeeded — commit all DB changes at once
            self.db.commit()

            logger.info("embedding_pipeline_complete", filing_id=filing_id,
                       chunks_indexed=len(point_ids))

            return {
                "filing_id": filing_id,
                "chunks_indexed": len(point_ids),
                "status": "INDEXED",
            }

        except Exception as e:
            # Roll back all DB changes
            self.db.rollback()

            # If Qdrant was already indexed but DB commit failed,
            # clean up the orphan vectors
            if qdrant_indexed:
                try:
                    indexer.delete_filing_vectors(filing_id)
                    logger.info("qdrant_rollback_cleanup", filing_id=filing_id)
                except Exception as cleanup_error:
                    logger.error(
                        "qdrant_rollback_cleanup_failed",
                        filing_id=filing_id,
                        error=str(cleanup_error),
                    )

            logger.error("embedding_pipeline_failed", filing_id=filing_id,
                        error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Embedding pipeline failed: {str(e)}",
            )

    def ask(
        self,
        filing_id: str,
        question: str,
        session_id: str | None,
        user_id: str,
    ) -> dict:
        """
        Answer a question about a filing using RAG.

        Steps:
        1. Get or create chat session
        2. Save user message
        3. Load all chunks for BM25 index
        4. Run hybrid retrieval
        5. Generate answer with Llama 3
        6. Save assistant message with citations
        7. Return answer + citations
        """
        # Get or create session
        if session_id:
            session = self.chat_repo.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Chat session not found")
        else:
            # Auto-title from first question (truncated)
            title = question[:80] + "..." if len(question) > 80 else question
            session = self.chat_repo.create_session(filing_id, user_id, title)

        # Save user message
        self.chat_repo.add_message(
            session_id=str(session.id),
            role=MessageRole.USER,
            content=question,
        )

        # Load all chunks for this filing (needed for BM25)
        all_chunks = self.chunk_repo.get_by_filing_id(filing_id)

        if not all_chunks:
            raise HTTPException(
                status_code=422,
                detail="No indexed content found. Run the embedding pipeline first.",
            )

        # Build retriever and run hybrid search
        embedder = EmbeddingGenerator()
        retriever = HybridRetriever(embedder)

        start_time = time.time()

        relevant_chunks = retriever.retrieve(
            query=question,
            filing_id=filing_id,
            all_chunks=[
                {
                    "id": str(c.id),
                    "chunk_text": c.chunk_text,
                    "page_number": c.page_number,
                    "section_type": c.section_type.value if c.section_type else "UNKNOWN",
                }
                for c in all_chunks
            ],
        )

        # Generate answer
        generator = LLMGenerator()
        result = generator.generate(question, relevant_chunks)

        latency_ms = int((time.time() - start_time) * 1000)

        # Save assistant message with citations
        self.chat_repo.add_message(
            session_id=str(session.id),
            role=MessageRole.ASSISTANT,
            content=result["answer"],
            citations=result["citations"],
            retrieved_chunks=relevant_chunks,
            llm_model=result["model"],
            latency_ms=latency_ms,
        )

        logger.info("rag_query_complete", filing_id=filing_id,
                   latency_ms=latency_ms, chunks_used=len(relevant_chunks))

        return {
            "session_id": str(session.id),
            "answer": result["answer"],
            "citations": result["citations"],
            "chunks_retrieved": len(relevant_chunks),
            "latency_ms": latency_ms,
        }

    def get_history(self, session_id: str) -> list[dict]:
        """Get full conversation history for a session."""
        messages = self.chat_repo.get_messages(session_id)
        return [
            {
                "role": m.role.value,
                "content": m.content,
                "citations": m.citations,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]