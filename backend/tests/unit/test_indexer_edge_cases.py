# tests/unit/test_indexer_edge_cases.py
"""
Unit tests for QdrantIndexer.
Uses mocked QdrantClient to avoid needing a running Qdrant instance.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from app.engines.rag.indexer import QdrantIndexer
from qdrant_client.models import PayloadSchemaType


@pytest.fixture
def mock_qdrant_client():
    """Create a mocked QdrantClient."""
    with patch("app.engines.rag.indexer.QdrantClient") as MockClient:
        mock_client = MockClient.return_value
        yield mock_client


@pytest.fixture
def indexer(mock_qdrant_client):
    """Create a QdrantIndexer with mocked client."""
    idx = QdrantIndexer()
    return idx


class TestEnsureCollectionExists:

    def test_creates_collection_when_not_exists(self, indexer, mock_qdrant_client):
        """Should create collection when it doesn't exist."""
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])

        indexer.ensure_collection_exists()

        mock_qdrant_client.create_collection.assert_called_once()
        # Verify correct dimension
        call_kwargs = mock_qdrant_client.create_collection.call_args[1]
        assert call_kwargs["vectors_config"].size == 768

    def test_skips_creation_when_exists_with_correct_dim(self, indexer, mock_qdrant_client):
        """Should not recreate if collection exists with correct dimension."""
        mock_collection = MagicMock()
        mock_collection.name = "finsight_chunks"
        mock_qdrant_client.get_collections.return_value = MagicMock(
            collections=[mock_collection]
        )

        # Mock collection info with correct dimension
        mock_info = MagicMock()
        mock_info.config.params.vectors.size = 768
        mock_qdrant_client.get_collection.return_value = mock_info

        indexer.ensure_collection_exists()

        mock_qdrant_client.create_collection.assert_not_called()
        mock_qdrant_client.delete_collection.assert_not_called()

    def test_recreates_on_dimension_mismatch(self, indexer, mock_qdrant_client):
        """Should delete and recreate collection when dimension doesn't match."""
        mock_collection = MagicMock()
        mock_collection.name = "finsight_chunks"
        mock_qdrant_client.get_collections.return_value = MagicMock(
            collections=[mock_collection]
        )

        # Mock collection info with OLD dimension (1024)
        mock_info = MagicMock()
        mock_info.config.params.vectors.size = 1024
        mock_qdrant_client.get_collection.return_value = mock_info

        indexer.ensure_collection_exists()

        mock_qdrant_client.delete_collection.assert_called_once()
        mock_qdrant_client.create_collection.assert_called_once()


class TestPayloadIndexCreation:

    def test_creates_three_payload_indexes(self, indexer, mock_qdrant_client):
        """Should create indexes for filing_id, section_type, chunk_index."""
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])

        indexer.ensure_collection_exists()

        # Should have 3 create_payload_index calls
        assert mock_qdrant_client.create_payload_index.call_count == 3

        # Extract field names from calls
        index_fields = [
            call[1]["field_name"]
            for call in mock_qdrant_client.create_payload_index.call_args_list
        ]
        assert "filing_id" in index_fields
        assert "section_type" in index_fields
        assert "chunk_index" in index_fields

    def test_index_creation_is_idempotent(self, indexer, mock_qdrant_client):
        """Index creation should not crash if index already exists."""
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        # Simulate index already exists error
        mock_qdrant_client.create_payload_index.side_effect = Exception("index already exists")

        # Should not raise
        indexer.ensure_collection_exists()

    def test_filing_id_uses_keyword_type(self, indexer, mock_qdrant_client):
        """filing_id should use KEYWORD index type for exact matching."""
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])

        indexer.ensure_collection_exists()

        # Find the filing_id index creation call
        for call in mock_qdrant_client.create_payload_index.call_args_list:
            if call[1]["field_name"] == "filing_id":
                assert call[1]["field_schema"] == PayloadSchemaType.KEYWORD
                break

    def test_chunk_index_uses_integer_type(self, indexer, mock_qdrant_client):
        """chunk_index should use INTEGER index type for range queries."""
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])

        indexer.ensure_collection_exists()

        for call in mock_qdrant_client.create_payload_index.call_args_list:
            if call[1]["field_name"] == "chunk_index":
                assert call[1]["field_schema"] == PayloadSchemaType.INTEGER
                break


class TestIndexChunks:

    def test_empty_chunks_returns_empty(self, indexer, mock_qdrant_client):
        result = indexer.index_chunks([])
        assert result == []
        mock_qdrant_client.upsert.assert_not_called()

    def test_single_chunk_returns_one_id(self, indexer, mock_qdrant_client):
        chunks = [{
            "chunk_db_id": "db-uuid-1",
            "filing_id": "filing-uuid-1",
            "chunk_text": "Some text",
            "page_number": 1,
            "section_type": "MD_AND_A",
            "chunk_index": 0,
            "vector": [0.1] * 768,
        }]
        result = indexer.index_chunks(chunks)
        assert len(result) == 1
        mock_qdrant_client.upsert.assert_called_once()

    def test_payload_contains_all_fields(self, indexer, mock_qdrant_client):
        chunks = [{
            "chunk_db_id": "db-uuid-1",
            "filing_id": "filing-uuid-1",
            "chunk_text": "Some text",
            "page_number": 5,
            "section_type": "RISK_FACTORS",
            "chunk_index": 3,
            "vector": [0.1] * 768,
        }]
        indexer.index_chunks(chunks)

        # Get the points passed to upsert
        call_kwargs = mock_qdrant_client.upsert.call_args[1]
        point = call_kwargs["points"][0]

        assert point.payload["filing_id"] == "filing-uuid-1"
        assert point.payload["chunk_db_id"] == "db-uuid-1"
        assert point.payload["chunk_text"] == "Some text"
        assert point.payload["page_number"] == 5
        assert point.payload["section_type"] == "RISK_FACTORS"
        assert point.payload["chunk_index"] == 3

    def test_batch_splitting_at_100(self, indexer, mock_qdrant_client):
        """150 chunks should result in 2 upsert calls (100 + 50)."""
        chunks = [
            {
                "chunk_db_id": f"id-{i}",
                "filing_id": "filing-1",
                "chunk_text": f"text {i}",
                "page_number": 1,
                "section_type": "UNKNOWN",
                "chunk_index": i,
                "vector": [0.1] * 768,
            }
            for i in range(150)
        ]
        result = indexer.index_chunks(chunks)
        assert len(result) == 150
        assert mock_qdrant_client.upsert.call_count == 2

    def test_exactly_100_chunks_single_batch(self, indexer, mock_qdrant_client):
        chunks = [
            {
                "chunk_db_id": f"id-{i}",
                "filing_id": "filing-1",
                "chunk_text": f"text {i}",
                "vector": [0.1] * 768,
            }
            for i in range(100)
        ]
        indexer.index_chunks(chunks)
        assert mock_qdrant_client.upsert.call_count == 1

    def test_point_ids_are_unique(self, indexer, mock_qdrant_client):
        chunks = [
            {
                "chunk_db_id": f"id-{i}",
                "filing_id": "filing-1",
                "chunk_text": f"text {i}",
                "vector": [0.1] * 768,
            }
            for i in range(10)
        ]
        result = indexer.index_chunks(chunks)
        assert len(set(result)) == 10  # All IDs unique

    def test_missing_optional_fields_use_defaults(self, indexer, mock_qdrant_client):
        """page_number, section_type, chunk_index should have defaults."""
        chunks = [{
            "chunk_db_id": "id-1",
            "filing_id": "filing-1",
            "chunk_text": "text",
            "vector": [0.1] * 768,
        }]
        indexer.index_chunks(chunks)

        point = mock_qdrant_client.upsert.call_args[1]["points"][0]
        assert point.payload["page_number"] is None
        assert point.payload["section_type"] == "UNKNOWN"
        assert point.payload["chunk_index"] == 0


class TestDeleteFilingVectors:

    def test_calls_delete_with_correct_filter(self, indexer, mock_qdrant_client):
        indexer.delete_filing_vectors("test-filing-id")

        mock_qdrant_client.delete.assert_called_once()
        call_kwargs = mock_qdrant_client.delete.call_args[1]
        assert call_kwargs["collection_name"] == "finsight_chunks"

        # Verify the filter matches filing_id
        filter_obj = call_kwargs["points_selector"]
        assert filter_obj.must[0].key == "filing_id"
        assert filter_obj.must[0].match.value == "test-filing-id"
