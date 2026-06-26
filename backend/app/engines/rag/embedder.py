# app/engines/rag/embedder.py
"""
Generates vector embeddings using BGE Base model.

BGE Base (BAAI/bge-base-en-v1.5) produces 768-dimensional vectors.
It runs locally via sentence-transformers — no API calls, no cost.
Compared to bge-large (1024-dim, ~1.3GB), bge-base (768-dim, ~440MB)
uses ~65% less memory with only ~1% quality difference on MTEB benchmarks.

BGE models need a special instruction prefix for queries (not for documents):
  - Documents: embed as-is
  - Queries:   prepend "Represent this sentence for searching relevant passages: "
"""

from sentence_transformers import SentenceTransformer
from app.core.config import settings

# BGE query instruction prefix — improves retrieval quality significantly
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class EmbeddingGenerator:
    """
    Wraps the BGE Base model for generating embeddings.

    The model is loaded once when the class is instantiated.
    Loading takes ~3-5 seconds the first time (downloads ~440MB).
    After that it's cached locally by huggingface.

    Usage:
        embedder = EmbeddingGenerator()
        doc_vectors = embedder.embed_documents(["text1", "text2"])
        query_vector = embedder.embed_query("what are the risks?")
    """

    def __init__(self):
        print(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        print("Embedding model loaded.")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of document chunks.
        Returns a list of 768-dimensional vectors.
        No prefix needed for documents.
        """
        if not texts:
            return []

        # encode() returns numpy arrays — convert to plain Python lists
        vectors = self.model.encode(
            texts,
            batch_size=32,           # process 32 chunks at a time
            show_progress_bar=True,  # shows progress for large documents
            normalize_embeddings=True,  # normalize for cosine similarity
        )

        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a single search query.
        BGE requires the instruction prefix for queries.
        """
        prefixed_query = BGE_QUERY_PREFIX + query

        vector = self.model.encode(
            prefixed_query,
            normalize_embeddings=True,
        )

        return vector.tolist()