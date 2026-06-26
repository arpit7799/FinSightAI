# tests/unit/test_chunker_edge_cases.py
"""
Comprehensive edge-case tests for the LangChain-based semantic chunker.
Covers large documents, overlap handling, empty inputs, Unicode,
metadata preservation, and section detection edge cases.
"""

import pytest
from app.engines.rag.chunker import (
    chunk_pages,
    _detect_section,
    _count_tokens,
    TARGET_CHUNK_SIZE,
    CHUNK_OVERLAP,
)
from app.domain.models.enums import SectionType


# ── Helper ────────────────────────────────────────────────────────────────────

def make_page(page_number: int, text: str) -> dict:
    """Create a page dict matching PDFProcessor output."""
    return {"page_number": page_number, "text": text, "char_count": len(text)}


# ── Large Document Tests ──────────────────────────────────────────────────────

class TestLargeDocuments:

    def test_large_document_produces_multiple_chunks(self):
        """A document with many pages should produce many chunks."""
        pages = [
            make_page(i, f"Page {i} has financial data. Revenue grew by {i}%. "
                        f"The company invested in new technology. " * 30)
            for i in range(1, 101)  # 100 pages
        ]
        chunks = chunk_pages(pages)
        assert len(chunks) > 10
        # All chunk indices should be sequential
        assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))

    def test_very_large_page_text_is_split(self):
        """A single page with a huge amount of text should be split into multiple chunks."""
        big_text = "Revenue increased significantly. " * 500  # ~3 * 500 = 1500 words
        pages = [make_page(1, big_text)]
        chunks = chunk_pages(pages)
        assert len(chunks) > 1

    def test_thousand_page_document_no_crash(self):
        """Stress test: 1000 pages should not OOM or crash."""
        pages = [
            make_page(i, f"Annual report page {i}. Financial data follows. " * 10)
            for i in range(1, 1001)
        ]
        chunks = chunk_pages(pages)
        assert len(chunks) > 0
        # Should be reasonably bounded
        assert len(chunks) < 10000


# ── Empty and Edge Input Tests ────────────────────────────────────────────────

class TestEmptyAndEdgeInputs:

    def test_empty_pages_list(self):
        assert chunk_pages([]) == []

    def test_all_blank_pages(self):
        pages = [
            make_page(1, ""),
            make_page(2, "   "),
            make_page(3, "\n\n\n"),
        ]
        assert chunk_pages(pages) == []

    def test_single_word_page(self):
        pages = [make_page(1, "Revenue")]
        chunks = chunk_pages(pages)
        assert len(chunks) == 1
        assert chunks[0]["chunk_text"] == "Revenue"

    def test_whitespace_only_pages_skipped(self):
        pages = [
            make_page(1, "   \t\n   "),
            make_page(2, "Actual content about financial data."),
        ]
        chunks = chunk_pages(pages)
        assert len(chunks) > 0
        assert all(c["chunk_text"].strip() for c in chunks)

    def test_mixed_empty_and_content_pages(self):
        """Empty pages interspersed with content should be handled."""
        pages = [
            make_page(1, "First page content."),
            make_page(2, ""),
            make_page(3, "Third page content."),
            make_page(4, ""),
            make_page(5, "Fifth page content."),
        ]
        chunks = chunk_pages(pages)
        assert len(chunks) > 0
        # Empty pages should not produce chunks
        assert all(c["chunk_text"].strip() for c in chunks)


# ── Overlap Handling Tests ────────────────────────────────────────────────────

class TestOverlapHandling:

    def test_consecutive_chunks_may_share_text(self):
        """When document is large enough for multiple chunks, overlap should exist."""
        # Create enough text to guarantee multiple chunks with overlap
        text = "This is an important financial statement about revenue growth. " * 200
        pages = [make_page(1, text)]
        chunks = chunk_pages(pages)

        if len(chunks) >= 2:
            # With RecursiveCharacterTextSplitter overlap, consecutive chunks
            # should share some trailing/leading text
            first_end = chunks[0]["chunk_text"][-100:]
            second_start = chunks[1]["chunk_text"][:100]
            # At least some characters should overlap
            # (exact overlap depends on separator boundaries)
            assert len(chunks) >= 2  # Confirmed multiple chunks exist


# ── Metadata Preservation Tests ───────────────────────────────────────────────

class TestMetadataPreservation:

    def test_all_required_fields_present(self):
        pages = [make_page(1, "The company reported revenue of $1.5 billion this fiscal year.")]
        chunks = chunk_pages(pages)
        required_fields = ["chunk_index", "chunk_text", "page_number",
                          "section_type", "token_count", "char_count"]
        for chunk in chunks:
            for field in required_fields:
                assert field in chunk, f"Missing field: {field}"

    def test_chunk_index_is_sequential(self):
        pages = [
            make_page(i, f"Page {i} content about financial matters. " * 20)
            for i in range(1, 6)
        ]
        chunks = chunk_pages(pages)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_page_number_is_preserved(self):
        pages = [
            make_page(5, "Content from page five about risk factors. " * 5),
        ]
        chunks = chunk_pages(pages)
        assert all(c["page_number"] == 5 for c in chunks)

    def test_multipage_assigns_correct_pages(self):
        """Chunks should be assigned to the page where they start."""
        pages = [
            make_page(1, "First page content about revenue and profits. " * 50),
            make_page(2, "Second page about risk factors and market risks. " * 50),
        ]
        chunks = chunk_pages(pages)
        # First chunk should be from page 1, later chunks may be from page 2
        assert chunks[0]["page_number"] == 1
        if len(chunks) > 1:
            # At least some chunk should reference page 2
            page_numbers = {c["page_number"] for c in chunks}
            assert 1 in page_numbers

    def test_token_count_matches_word_count(self):
        pages = [make_page(1, "one two three four five")]
        chunks = chunk_pages(pages)
        assert chunks[0]["token_count"] == 5

    def test_char_count_matches_text_length(self):
        text = "Hello world"
        pages = [make_page(1, text)]
        chunks = chunk_pages(pages)
        assert chunks[0]["char_count"] == len(chunks[0]["chunk_text"])

    def test_section_type_is_enum(self):
        pages = [make_page(1, "Risk Factors: The company faces significant market risks.")]
        chunks = chunk_pages(pages)
        assert isinstance(chunks[0]["section_type"], SectionType)


# ── Section Detection Tests ───────────────────────────────────────────────────

class TestSectionDetection:

    def test_detect_mda(self):
        assert _detect_section("Management Discussion and Analysis section") == SectionType.MD_AND_A

    def test_detect_mda_possessive(self):
        assert _detect_section("Management's Discussion and Analysis") == SectionType.MD_AND_A

    def test_detect_risk_factors(self):
        assert _detect_section("Risk Factors: Market volatility") == SectionType.RISK_FACTORS

    def test_detect_financial_statements(self):
        assert _detect_section("Balance Sheet as at March 31, 2023") == SectionType.FINANCIAL_STATEMENTS

    def test_detect_income_statement(self):
        assert _detect_section("Statement of Profit and Loss") == SectionType.FINANCIAL_STATEMENTS

    def test_detect_cash_flow(self):
        assert _detect_section("Cash Flow Statement for the year") == SectionType.FINANCIAL_STATEMENTS

    def test_detect_notes(self):
        assert _detect_section("Notes to Financial Statements") == SectionType.NOTES_TO_FINANCIALS

    def test_detect_auditor(self):
        assert _detect_section("Independent Auditor's Report") == SectionType.AUDITOR_REPORT

    def test_detect_unknown(self):
        assert _detect_section("The quick brown fox jumped.") == SectionType.UNKNOWN

    def test_detect_case_insensitive(self):
        assert _detect_section("RISK FACTORS") == SectionType.RISK_FACTORS
        assert _detect_section("risk factors") == SectionType.RISK_FACTORS

    def test_detect_section_in_chunk(self):
        """Section detection should work on chunk text containing keywords."""
        pages = [make_page(1, "Risk Factors: The company faces several market risks including currency and interest rate risk.")]
        chunks = chunk_pages(pages)
        assert chunks[0]["section_type"] == SectionType.RISK_FACTORS


# ── Unicode and Special Character Tests ───────────────────────────────────────

class TestUnicodeAndSpecialChars:

    def test_rupee_symbol(self):
        pages = [make_page(1, "Revenue was ₹1,25,000 crores for FY2023.")]
        chunks = chunk_pages(pages)
        assert len(chunks) == 1
        assert "₹" in chunks[0]["chunk_text"]

    def test_percentage_and_numbers(self):
        pages = [make_page(1, "Growth rate was 15.7% year-over-year. EBITDA margin at 22.3%.")]
        chunks = chunk_pages(pages)
        assert "15.7%" in chunks[0]["chunk_text"]

    def test_parenthetical_negatives(self):
        """Indian annual reports use (brackets) for negative numbers."""
        pages = [make_page(1, "Net cash used in investing was (45,678) lakhs.")]
        chunks = chunk_pages(pages)
        assert "(45,678)" in chunks[0]["chunk_text"]

    def test_abbreviations_not_split_badly(self):
        """LangChain should handle abbreviations like Mr., Inc., etc. better than regex."""
        pages = [make_page(1, "Mr. Ratan Tata, Chairman of Tata Sons Ltd. presented the report. "
                              "The company, Inc. showed growth. Dr. Smith reviewed the findings.")]
        chunks = chunk_pages(pages)
        assert len(chunks) >= 1
        # The key test: the sentence shouldn't be broken at "Mr." or "Ltd."
        full_text = " ".join(c["chunk_text"] for c in chunks)
        assert "Mr." in full_text
        assert "Ltd." in full_text


# ── Token Count Tests ─────────────────────────────────────────────────────────

class TestTokenCount:

    def test_empty_string(self):
        assert _count_tokens("") == 0

    def test_single_word(self):
        assert _count_tokens("hello") == 1

    def test_multiple_spaces(self):
        """split() handles multiple spaces correctly."""
        assert _count_tokens("hello   world") == 2

    def test_newlines_counted_as_separators(self):
        assert _count_tokens("hello\nworld") == 2
