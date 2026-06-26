# app/engines/rag/retriever.py
"""
Hybrid retrieval — combines dense (BGE) and sparse (BM25) search.

Why hybrid?
  - Dense search (BGE vectors): finds semantically similar chunks
    even when the exact words don't match. Good for conceptual questions.
  - Sparse search (BM25): finds chunks with exact keyword matches.
    Good for specific terms like "DSRI", "Altman Z-Score", ratio names.

We combine both using Reciprocal Rank Fusion (RRF):
  - Each method returns a ranked list
  - RRF combines the ranks (not scores) into a final ranking
  - Top-5 chunks from fused ranking are returned
"""

from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.engines.rag.embedder import EmbeddingGenerator


# How many results to pull from each method before fusing
TOP_K_DENSE = 10
TOP_K_SPARSE = 10

# Final number of chunks to return to LLM
FINAL_TOP_K = 5

# RRF constant — standard value from the paper
RRF_K = 60


def _reciprocal_rank_fusion(
    dense_results: list[dict],
    sparse_results: list[dict],
) -> list[dict]:
    """
    Combine dense and sparse results using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank)) for each result list
    Higher score = better combined rank.
    """
    scores = {}

    # Score from dense results
    for rank, result in enumerate(dense_results):
        chunk_id = result["chunk_db_id"]
        if chunk_id not in scores:
            scores[chunk_id] = {"score": 0, "data": result}
        scores[chunk_id]["score"] += 1 / (RRF_K + rank + 1)

    # Score from sparse results
    for rank, result in enumerate(sparse_results):
        chunk_id = result["chunk_db_id"]
        if chunk_id not in scores:
            scores[chunk_id] = {"score": 0, "data": result}
        scores[chunk_id]["score"] += 1 / (RRF_K + rank + 1)

    # Sort by combined score (highest first)
    sorted_results = sorted(
        scores.values(),
        key=lambda x: x["score"],
        reverse=True,
    )

    return [r["data"] for r in sorted_results[:FINAL_TOP_K]]


class HybridRetriever:
    """
    Retrieves the most relevant chunks for a query using hybrid search.

    Usage:
        retriever = HybridRetriever(embedder)
        chunks = retriever.retrieve(
            query="What are the major risks?",
            filing_id="uuid",
            all_chunks=[...]   # all chunks for BM25 index
        )
    """

    def __init__(self, embedder: EmbeddingGenerator):
        self.embedder = embedder
        self.qdrant = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )
        self.collection = settings.QDRANT_COLLECTION_NAME

    def retrieve(
        self,
        query: str,
        filing_id: str,
        all_chunks: list[dict],
    ) -> list[dict]:
        """
        Run hybrid retrieval for a query against a specific filing.

        Args:
            query: the user's natural language question
            filing_id: filter results to this filing only
            all_chunks: all DB chunks for this filing (needed for BM25 index)

        Returns:
            Top-5 most relevant chunks with metadata for citation.
        """
        # ── Dense retrieval (BGE + Qdrant) ────────────────────────────────
        query_vector = self.embedder.embed_query(query)

        dense_raw = self.qdrant.search(
            collection_name=self.collection,
            query_vector=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="filing_id",
                        match=MatchValue(value=filing_id),
                    )
                ]
            ),
            limit=TOP_K_DENSE,
            with_payload=True,
        )

        dense_results = [
            {
                "chunk_db_id": hit.payload["chunk_db_id"],
                "chunk_text": hit.payload["chunk_text"],
                "page_number": hit.payload.get("page_number"),
                "section_type": hit.payload.get("section_type"),
                "dense_score": hit.score,
            }
            for hit in dense_raw
        ]

        # ── Sparse retrieval (BM25) ───────────────────────────────────────
        sparse_results = self._bm25_search(query, all_chunks)

        # ── Fuse results ──────────────────────────────────────────────────
        if not dense_results:
            return sparse_results[:FINAL_TOP_K]
        if not sparse_results:
            return dense_results[:FINAL_TOP_K]

        return _reciprocal_rank_fusion(dense_results, sparse_results)

    def _bm25_search(self, query: str, chunks: list[dict]) -> list[dict]:
        """
        Run BM25 keyword search over all chunks for a filing.
        BM25 is great for exact term matching — tickers, ratio names, etc.
        """
        if not chunks:
            return []

        # Tokenize all chunk texts
        tokenized_corpus = [
            chunk["chunk_text"].lower().split()
            for chunk in chunks
        ]

        bm25 = BM25Okapi(tokenized_corpus)

        # Tokenize query and get scores
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)

        # Pair each chunk with its BM25 score
        scored = list(zip(chunks, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        return [
            {
                "chunk_db_id": str(chunk["id"]),
                "chunk_text": chunk["chunk_text"],
                "page_number": chunk.get("page_number"),
                "section_type": str(chunk.get("section_type", "UNKNOWN")),
                "bm25_score": float(score),
            }
            for chunk, score in scored[:TOP_K_SPARSE]
            if score > 0  # skip zero-score chunks
        ]