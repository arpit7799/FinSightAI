# tests/unit/test_embedder_edge_cases.py
"""
Unit tests for the EmbeddingGenerator.
Uses mocked SentenceTransformer to avoid downloading the model.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from app.engines.rag.embedder import EmbeddingGenerator, BGE_QUERY_PREFIX


@pytest.fixture
def mock_embedder():
    """Create an EmbeddingGenerator with a mocked SentenceTransformer."""
    with patch("app.engines.rag.embedder.SentenceTransformer") as MockModel:
        mock_model = MockModel.return_value

        # Mock encode to return fake 768-dim vectors
        def fake_encode(texts, **kwargs):
            if isinstance(texts, str):
                return np.random.rand(768).astype(np.float32)
            return np.random.rand(len(texts), 768).astype(np.float32)

        mock_model.encode = MagicMock(side_effect=fake_encode)
        embedder = EmbeddingGenerator()
        yield embedder, mock_model


class TestEmbedDocuments:

    def test_empty_list_returns_empty(self, mock_embedder):
        embedder, _ = mock_embedder
        result = embedder.embed_documents([])
        assert result == []

    def test_single_text_returns_correct_dimension(self, mock_embedder):
        embedder, _ = mock_embedder
        result = embedder.embed_documents(["test text"])
        assert len(result) == 1
        assert len(result[0]) == 768

    def test_multiple_texts_returns_correct_count(self, mock_embedder):
        embedder, _ = mock_embedder
        texts = ["text1", "text2", "text3"]
        result = embedder.embed_documents(texts)
        assert len(result) == 3

    def test_returns_python_lists_not_numpy(self, mock_embedder):
        embedder, _ = mock_embedder
        result = embedder.embed_documents(["test"])
        assert isinstance(result, list)
        assert isinstance(result[0], list)
        assert isinstance(result[0][0], float)

    def test_batch_size_passed_to_model(self, mock_embedder):
        embedder, mock_model = mock_embedder
        embedder.embed_documents(["test"])
        mock_model.encode.assert_called_once()
        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs["batch_size"] == 32

    def test_normalization_enabled(self, mock_embedder):
        embedder, mock_model = mock_embedder
        embedder.embed_documents(["test"])
        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs["normalize_embeddings"] is True

    def test_large_batch_processes(self, mock_embedder):
        embedder, _ = mock_embedder
        texts = [f"text {i}" for i in range(200)]
        result = embedder.embed_documents(texts)
        assert len(result) == 200

    def test_special_characters_dont_crash(self, mock_embedder):
        embedder, _ = mock_embedder
        texts = [
            "Revenue was ₹1,25,000",
            "Growth rate: 15.7% (year-over-year)",
            "Ñoño's café résumé — \"quoted\"",
            "",  # empty string
        ]
        result = embedder.embed_documents(texts)
        assert len(result) == 4


class TestEmbedQuery:

    def test_query_prefix_prepended(self, mock_embedder):
        embedder, mock_model = mock_embedder
        embedder.embed_query("what are the risks?")

        # Check that the model received the prefixed query
        call_args = mock_model.encode.call_args[0][0]
        assert call_args.startswith(BGE_QUERY_PREFIX)
        assert "what are the risks?" in call_args

    def test_returns_flat_list(self, mock_embedder):
        embedder, _ = mock_embedder
        result = embedder.embed_query("test query")
        assert isinstance(result, list)
        assert len(result) == 768

    def test_returns_python_floats(self, mock_embedder):
        embedder, _ = mock_embedder
        result = embedder.embed_query("test")
        assert all(isinstance(v, float) for v in result)

    def test_normalization_enabled_for_query(self, mock_embedder):
        embedder, mock_model = mock_embedder
        embedder.embed_query("test")
        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs["normalize_embeddings"] is True

    def test_empty_query(self, mock_embedder):
        """Empty query should still work (prefix only)."""
        embedder, mock_model = mock_embedder
        result = embedder.embed_query("")
        call_args = mock_model.encode.call_args[0][0]
        assert call_args == BGE_QUERY_PREFIX
        assert len(result) == 768
