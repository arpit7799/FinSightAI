# tests/unit/test_rag.py
"""
Unit tests for the RAG pipeline components.
No Qdrant, Ollama, or database needed.

Updated for Phase 7: tests work with LangChain-based chunker
while verifying backward compatibility of chunk dict keys.
"""

import pytest
from app.engines.rag.chunker import chunk_pages, _detect_section, _count_tokens
from app.engines.rag.llm_generator import _build_prompt
from app.engines.rag.retriever import _reciprocal_rank_fusion
from app.domain.models.enums import SectionType


# ── Chunker tests ─────────────────────────────────────────────────────────────

class TestChunker:

    def test_chunk_pages_returns_list(self):
        pages = [{"page_number": 1, "text": "Revenue increased by 15% this year. Net profit was strong. The company performed well.", "char_count": 80}]
        chunks = chunk_pages(pages)
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_chunk_has_required_fields(self):
        """Verify backward compatibility — all 6 required fields present."""
        pages = [{"page_number": 1, "text": "Revenue increased by 15% this year. The company showed strong performance.", "char_count": 70}]
        chunks = chunk_pages(pages)
        required = ["chunk_index", "chunk_text", "page_number", "section_type", "token_count", "char_count"]
        for field in required:
            assert field in chunks[0], f"Missing required field: {field}"

    def test_empty_pages_returns_empty(self):
        assert chunk_pages([]) == []

    def test_blank_page_skipped(self):
        pages = [
            {"page_number": 1, "text": "", "char_count": 0},
            {"page_number": 2, "text": "Some actual content here about revenue and profit.", "char_count": 48},
        ]
        chunks = chunk_pages(pages)
        assert len(chunks) > 0
        assert all(c["chunk_text"].strip() for c in chunks)

    def test_chunk_indices_are_sequential(self):
        pages = [
            {"page_number": i, "text": f"Page {i} content with financial data and analysis. " * 20, "char_count": 500}
            for i in range(1, 6)
        ]
        chunks = chunk_pages(pages)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_detect_mda_section(self):
        text = "Management Discussion and Analysis: Revenue grew by 20% this year."
        assert _detect_section(text) == SectionType.MD_AND_A

    def test_detect_risk_section(self):
        text = "Risk Factors: The company faces significant market risks."
        assert _detect_section(text) == SectionType.RISK_FACTORS

    def test_detect_unknown_section(self):
        text = "The quick brown fox jumped over the lazy dog."
        assert _detect_section(text) == SectionType.UNKNOWN

    def test_token_count_is_word_count(self):
        assert _count_tokens("hello world foo bar") == 4

    def test_chunk_text_is_not_empty(self):
        """Every chunk should have non-empty text."""
        pages = [
            {"page_number": 1, "text": "Financial statement data for the year.", "char_count": 40},
        ]
        chunks = chunk_pages(pages)
        for chunk in chunks:
            assert len(chunk["chunk_text"].strip()) > 0

    def test_section_type_is_enum_instance(self):
        """section_type should be a SectionType enum, not a string."""
        pages = [{"page_number": 1, "text": "Risk Factors: major risks ahead.", "char_count": 30}]
        chunks = chunk_pages(pages)
        assert isinstance(chunks[0]["section_type"], SectionType)


# ── LLM Generator tests ───────────────────────────────────────────────────────

class TestLLMGenerator:

    def test_build_prompt_includes_query(self):
        chunks = [{"chunk_text": "Revenue was 1.2 billion.", "page_number": 5, "section_type": "MD_AND_A"}]
        prompt = _build_prompt("What was the revenue?", chunks)
        assert "What was the revenue?" in prompt

    def test_build_prompt_numbers_chunks(self):
        chunks = [
            {"chunk_text": "First chunk text.", "page_number": 1, "section_type": "MD_AND_A"},
            {"chunk_text": "Second chunk text.", "page_number": 2, "section_type": "RISK_FACTORS"},
        ]
        prompt = _build_prompt("test question", chunks)
        assert "[Chunk 1]" in prompt
        assert "[Chunk 2]" in prompt

    def test_build_prompt_includes_page_numbers(self):
        chunks = [{"chunk_text": "Some text.", "page_number": 23, "section_type": "RISK_FACTORS"}]
        prompt = _build_prompt("question", chunks)
        assert "Page 23" in prompt

    def test_build_prompt_with_no_chunks(self):
        # Should not crash with empty chunks
        prompt = _build_prompt("question", [])
        assert "question" in prompt


# ── Retriever tests ───────────────────────────────────────────────────────────

class TestRRF:

    def test_rrf_combines_results(self):
        dense = [
            {"chunk_db_id": "chunk1", "chunk_text": "text1", "page_number": 1, "section_type": "MD_AND_A"},
            {"chunk_db_id": "chunk2", "chunk_text": "text2", "page_number": 2, "section_type": "RISK_FACTORS"},
        ]
        sparse = [
            {"chunk_db_id": "chunk2", "chunk_text": "text2", "page_number": 2, "section_type": "RISK_FACTORS"},
            {"chunk_db_id": "chunk3", "chunk_text": "text3", "page_number": 3, "section_type": "UNKNOWN"},
        ]
        result = _reciprocal_rank_fusion(dense, sparse)
        assert len(result) > 0
        # chunk2 appears in both lists so should rank highest
        assert result[0]["chunk_db_id"] == "chunk2"

    def test_rrf_handles_empty_dense(self):
        sparse = [{"chunk_db_id": "chunk1", "chunk_text": "text", "page_number": 1, "section_type": "MD_AND_A"}]
        result = _reciprocal_rank_fusion([], sparse)
        assert len(result) > 0

    def test_rrf_handles_empty_sparse(self):
        dense = [{"chunk_db_id": "chunk1", "chunk_text": "text", "page_number": 1, "section_type": "MD_AND_A"}]
        result = _reciprocal_rank_fusion(dense, [])
        assert len(result) > 0

    def test_rrf_deduplicates(self):
        same = [{"chunk_db_id": "chunk1", "chunk_text": "text", "page_number": 1, "section_type": "MD_AND_A"}]
        result = _reciprocal_rank_fusion(same, same)
        # Should not return duplicates
        ids = [r["chunk_db_id"] for r in result]
        assert len(ids) == len(set(ids))