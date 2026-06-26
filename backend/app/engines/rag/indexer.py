# app/engines/rag/indexer.py
"""
Stores and manages vectors in Qdrant.

Each chunk gets stored as a Qdrant point with:
  - id: UUID (same as DocumentChunk.embedding_id in PostgreSQL)
  - vector: 768-dim BGE Base embedding
  - payload: metadata for filtering and citation rendering

The payload stored in Qdrant:
    {
        "filing_id": "uuid",
        "chunk_db_id": "uuid",   # links back to DocumentChunk in PostgreSQL
        "chunk_text": "...",
        "page_number": 5,
        "section_type": "RISK_FACTORS",
        "chunk_index": 12,
    }

Payload indexes are created on commonly filtered fields (filing_id,
section_type, chunk_index) to improve filtered search performance
from O(n) full-scan to O(log n) indexed lookup.
"""

import uuid
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)
from app.core.config import settings

logger = structlog.get_logger()


class QdrantIndexer:
    """
    Handles all Qdrant operations — collection setup, inserting vectors,
    and deleting vectors when a filing is removed.

    Usage:
        indexer = QdrantIndexer()
        indexer.ensure_collection_exists()
        indexer.index_chunks(chunks_with_vectors)
    """

    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )
        self.collection = settings.QDRANT_COLLECTION_NAME

    def ensure_collection_exists(self) -> None:
        """
        Create the Qdrant collection if it doesn't exist yet, or recreate
        it if the vector dimension has changed (e.g., after model swap).

        Also creates payload indexes on commonly filtered fields for
        faster filtered search performance.

        Safe to call multiple times — checks before creating.
        """
        existing = [c.name for c in self.client.get_collections().collections]

        if self.collection in existing:
            # Validate dimension matches current config
            collection_info = self.client.get_collection(self.collection)
            current_dim = collection_info.config.params.vectors.size

            if current_dim != settings.EMBEDDING_DIMENSION:
                logger.warning(
                    "qdrant_dimension_mismatch",
                    collection=self.collection,
                    existing_dim=current_dim,
                    expected_dim=settings.EMBEDDING_DIMENSION,
                    action="recreating_collection",
                )
                self.client.delete_collection(self.collection)
            else:
                logger.info(
                    "qdrant_collection_exists",
                    collection=self.collection,
                    dimension=current_dim,
                )
                # Ensure payload indexes exist even on existing collections
                self._create_payload_indexes()
                return

        # Create collection with current embedding dimension
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSION,  # 768 for BGE Base
                distance=Distance.COSINE,           # cosine similarity
            ),
        )
        logger.info(
            "qdrant_collection_created",
            collection=self.collection,
            dimension=settings.EMBEDDING_DIMENSION,
        )

        # Create payload indexes for filtered search performance
        self._create_payload_indexes()

    def _create_payload_indexes(self) -> None:
        """
        Create payload indexes on commonly filtered fields.

        Without indexes, Qdrant scans all payloads during filtered
        queries — O(n). With indexes, filtered search is O(log n).

        Idempotent — safe to call multiple times. If an index already
        exists, Qdrant silently ignores the request.
        """
        indexes = [
            ("filing_id", PayloadSchemaType.KEYWORD),
            ("section_type", PayloadSchemaType.KEYWORD),
            ("chunk_index", PayloadSchemaType.INTEGER),
        ]

        for field_name, field_type in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field_name,
                    field_schema=field_type,
                )
                logger.info(
                    "qdrant_payload_index_created",
                    collection=self.collection,
                    field=field_name,
                    type=field_type.value,
                )
            except Exception as e:
                # Index may already exist — that's fine
                logger.debug(
                    "qdrant_payload_index_skipped",
                    collection=self.collection,
                    field=field_name,
                    reason=str(e),
                )

    def index_chunks(self, chunks: list[dict]) -> list[str]:
        """
        Insert a list of chunks with their vectors into Qdrant.

        Input chunks format:
            [{
                "chunk_db_id": "uuid-from-postgres",
                "filing_id": "uuid",
                "chunk_text": "...",
                "page_number": 5,
                "section_type": "RISK_FACTORS",
                "chunk_index": 12,
                "vector": [0.1, 0.2, ...],  # 768-dim
            }]

        Returns list of Qdrant point IDs (same as embedding_ids to store in PostgreSQL).
        """
        if not chunks:
            return []

        points = []
        point_ids = []

        for chunk in chunks:
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=chunk["vector"],
                    payload={
                        "filing_id": chunk["filing_id"],
                        "chunk_db_id": chunk["chunk_db_id"],
                        "chunk_text": chunk["chunk_text"],
                        "page_number": chunk.get("page_number"),
                        "section_type": chunk.get("section_type", "UNKNOWN"),
                        "chunk_index": chunk.get("chunk_index", 0),
                    },
                )
            )

        # Upsert in batches of 100 to avoid memory issues
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection,
                points=batch,
            )

        return point_ids

    def delete_filing_vectors(self, filing_id: str) -> None:
        """
        Delete all vectors for a filing from Qdrant.
        Called when a filing is soft-deleted or re-indexed.
        """
        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="filing_id",
                        match=MatchValue(value=filing_id),
                    )
                ]
            ),
        )