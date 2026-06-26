# tests/unit/test_llm_generator_edge_cases.py
"""
Unit tests for LLMGenerator — prompt building, citation extraction,
and edge cases. No Ollama server needed — we test the logic directly.
"""

import pytest
from app.engines.rag.llm_generator import _build_prompt, LLMGenerator


# ── Prompt Building Tests ─────────────────────────────────────────────────────

class TestBuildPrompt:

    def test_includes_query(self):
        chunks = [{"chunk_text": "Revenue data.", "page_number": 1, "section_type": "MD_AND_A"}]
        prompt = _build_prompt("What was the revenue?", chunks)
        assert "What was the revenue?" in prompt

    def test_numbers_chunks_correctly(self):
        chunks = [
            {"chunk_text": f"Chunk {i} text.", "page_number": i, "section_type": "MD_AND_A"}
            for i in range(1, 6)
        ]
        prompt = _build_prompt("question", chunks)
        for i in range(1, 6):
            assert f"[Chunk {i}]" in prompt

    def test_includes_page_numbers(self):
        chunks = [{"chunk_text": "Text.", "page_number": 42, "section_type": "RISK_FACTORS"}]
        prompt = _build_prompt("q", chunks)
        assert "Page 42" in prompt

    def test_includes_section_type(self):
        chunks = [{"chunk_text": "Text.", "page_number": 1, "section_type": "RISK_FACTORS"}]
        prompt = _build_prompt("q", chunks)
        assert "RISK_FACTORS" in prompt

    def test_handles_missing_page_number(self):
        chunks = [{"chunk_text": "Text.", "page_number": None, "section_type": "UNKNOWN"}]
        prompt = _build_prompt("q", chunks)
        assert "Unknown page" in prompt

    def test_empty_chunks_list(self):
        prompt = _build_prompt("What happened?", [])
        assert "What happened?" in prompt

    def test_large_number_of_chunks(self):
        chunks = [
            {"chunk_text": f"Chunk {i}.", "page_number": i, "section_type": "UNKNOWN"}
            for i in range(1, 21)
        ]
        prompt = _build_prompt("q", chunks)
        assert "[Chunk 20]" in prompt

    def test_chunk_text_included_in_prompt(self):
        chunks = [{"chunk_text": "UNIQUE_FINANCIAL_DATA_12345", "page_number": 1, "section_type": "MD_AND_A"}]
        prompt = _build_prompt("q", chunks)
        assert "UNIQUE_FINANCIAL_DATA_12345" in prompt


# ── Citation Extraction Tests ─────────────────────────────────────────────────

class TestCitationExtraction:

    @pytest.fixture
    def generator(self):
        """Create LLMGenerator without connecting to Ollama."""
        gen = LLMGenerator.__new__(LLMGenerator)
        gen.base_url = "http://localhost:11434"
        gen.model = "llama3"
        return gen

    def test_extract_single_citation(self, generator):
        answer = "Revenue grew by 15%. [Chunk 1]"
        chunks = [{"chunk_text": "Revenue data.", "page_number": 1, "section_type": "MD_AND_A"}]
        citations = generator._extract_citations(answer, chunks)
        assert len(citations) == 1
        assert citations[0]["chunk_index"] == 1

    def test_extract_multiple_citations(self, generator):
        answer = "Revenue grew [Chunk 1] and risks increased [Chunk 3]."
        chunks = [
            {"chunk_text": "Revenue data.", "page_number": 1, "section_type": "MD_AND_A"},
            {"chunk_text": "Profit data.", "page_number": 2, "section_type": "MD_AND_A"},
            {"chunk_text": "Risk data.", "page_number": 3, "section_type": "RISK_FACTORS"},
        ]
        citations = generator._extract_citations(answer, chunks)
        assert len(citations) == 2
        indices = {c["chunk_index"] for c in citations}
        assert indices == {1, 3}

    def test_duplicate_citations_deduplicated(self, generator):
        answer = "Revenue [Chunk 2] grew significantly [Chunk 2] this year."
        chunks = [
            {"chunk_text": "data1.", "page_number": 1, "section_type": "MD_AND_A"},
            {"chunk_text": "data2.", "page_number": 2, "section_type": "MD_AND_A"},
        ]
        citations = generator._extract_citations(answer, chunks)
        assert len(citations) == 1

    def test_no_citations_returns_empty(self, generator):
        answer = "The company performed well this year."
        chunks = [{"chunk_text": "data.", "page_number": 1, "section_type": "MD_AND_A"}]
        citations = generator._extract_citations(answer, chunks)
        assert citations == []

    def test_invalid_citation_number_skipped(self, generator):
        answer = "Revenue data [Chunk 99]."
        chunks = [{"chunk_text": "data.", "page_number": 1, "section_type": "MD_AND_A"}]
        citations = generator._extract_citations(answer, chunks)
        assert citations == []

    def test_zero_citation_skipped(self, generator):
        answer = "Data [Chunk 0]."
        chunks = [{"chunk_text": "data.", "page_number": 1, "section_type": "MD_AND_A"}]
        citations = generator._extract_citations(answer, chunks)
        # [Chunk 0] maps to index -1 which is out of range
        assert citations == []

    def test_double_digit_citation(self, generator):
        answer = "See [Chunk 10] for details."
        chunks = [
            {"chunk_text": f"chunk {i}.", "page_number": i, "section_type": "MD_AND_A"}
            for i in range(1, 11)
        ]
        citations = generator._extract_citations(answer, chunks)
        assert len(citations) == 1
        assert citations[0]["chunk_index"] == 10

    def test_chunk_text_truncation(self, generator):
        """Long chunk text should be truncated to 300 chars + '...'."""
        long_text = "A" * 500
        answer = "See [Chunk 1]."
        chunks = [{"chunk_text": long_text, "page_number": 1, "section_type": "MD_AND_A"}]
        citations = generator._extract_citations(answer, chunks)
        assert len(citations[0]["chunk_text"]) == 303  # 300 + "..."
        assert citations[0]["chunk_text"].endswith("...")

    def test_short_chunk_text_not_truncated(self, generator):
        """Short chunk text should not be truncated."""
        short_text = "Revenue was strong."
        answer = "See [Chunk 1]."
        chunks = [{"chunk_text": short_text, "page_number": 1, "section_type": "MD_AND_A"}]
        citations = generator._extract_citations(answer, chunks)
        assert citations[0]["chunk_text"] == short_text

    def test_citation_includes_metadata(self, generator):
        answer = "Data [Chunk 1]."
        chunks = [{"chunk_text": "text.", "page_number": 42, "section_type": "RISK_FACTORS"}]
        citations = generator._extract_citations(answer, chunks)
        assert citations[0]["page_number"] == 42
        assert citations[0]["section_type"] == "RISK_FACTORS"

    def test_missing_section_type_defaults(self, generator):
        answer = "Data [Chunk 1]."
        chunks = [{"chunk_text": "text.", "page_number": 1}]
        citations = generator._extract_citations(answer, chunks)
        assert citations[0]["section_type"] == "UNKNOWN"


# ── Generate Method Tests ─────────────────────────────────────────────────────

class TestGenerateMethod:

    @pytest.fixture
    def generator(self):
        gen = LLMGenerator.__new__(LLMGenerator)
        gen.base_url = "http://localhost:11434"
        gen.model = "llama3"
        return gen

    def test_generate_with_empty_chunks(self, generator):
        """Empty chunks should return a 'no information' message."""
        result = generator.generate("What is revenue?", [])
        assert "No relevant information" in result["answer"]
        assert result["citations"] == []
        assert result["model"] == "llama3"
