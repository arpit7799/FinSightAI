# app/engines/rag/chunker.py
"""
Splits filing text into semantic chunks for embedding.

Uses LangChain's RecursiveCharacterTextSplitter for robust,
production-grade text chunking that handles edge cases like
abbreviations ("Mr.", "Inc."), numbered lists, and section breaks
far better than regex-based splitting.

Strategy:
- Combine all page texts into a single document
- Split using RecursiveCharacterTextSplitter with separators
  optimised for financial documents (\n\n, \n, ". ", " ", "")
- chunk_size=2048 chars (~512 tokens at ~4 chars/token)
- chunk_overlap=200 chars (~50 tokens) for context continuity
- Map each chunk back to its source page number
- Tag each chunk with its detected section type
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.domain.models.enums import SectionType


# Target chunk size in characters (~512 tokens at ~4 chars/token)
TARGET_CHUNK_SIZE = 2048
# Overlap in characters (~50 tokens)
CHUNK_OVERLAP = 200

# Keywords that indicate which section of the report we're in
SECTION_KEYWORDS = {
    SectionType.MD_AND_A: [
        "management discussion", "management's discussion",
        "discussion and analysis", "md&a",
    ],
    SectionType.RISK_FACTORS: [
        "risk factors", "risks and concerns",
        "key risks", "principal risks",
    ],
    SectionType.FINANCIAL_STATEMENTS: [
        "balance sheet", "income statement", "profit and loss",
        "cash flow statement", "statement of financial position",
    ],
    SectionType.NOTES_TO_FINANCIALS: [
        "notes to financial", "notes forming part",
        "notes to accounts",
    ],
    SectionType.AUDITOR_REPORT: [
        "auditor's report", "independent auditor",
        "statutory auditor",
    ],
}


def _detect_section(text: str) -> SectionType:
    """
    Detect which section of the annual report this text belongs to
    based on keyword matching.
    """
    text_lower = text.lower()

    for section_type, keywords in SECTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return section_type

    return SectionType.UNKNOWN


def _count_tokens(text: str) -> int:
    """Rough token count — words are close enough for chunking purposes."""
    return len(text.split())


def _find_page_number(chunk_text: str, page_boundaries: list[tuple[int, int, int]]) -> int:
    """
    Determine which page a chunk belongs to based on its position
    in the concatenated document.

    page_boundaries: [(start_offset, end_offset, page_number), ...]

    We find the page whose range contains the midpoint of the chunk's
    first occurrence in the combined text, preferring the page where
    the majority of the chunk's text originates.
    """
    # This is called with chunk_start already computed
    # Fallback to first page if boundaries are empty
    if not page_boundaries:
        return 1
    return page_boundaries[0][2]


def chunk_pages(pages: list[dict]) -> list[dict]:
    """
    Takes a list of page dicts from PDFProcessor and returns
    a list of chunk dicts ready to be embedded.

    Input pages format:
        [{"page_number": 1, "text": "...", "char_count": 1200}, ...]

    Output chunks format:
        [{"chunk_index": 0, "chunk_text": "...", "page_number": 1,
          "section_type": SectionType.MD_AND_A, "token_count": 487,
          "char_count": 2100}, ...]
    """
    if not pages:
        return []

    # ── Build combined document with page boundary tracking ───────────
    combined_text_parts = []
    page_boundaries = []  # (start_offset, end_offset, page_number)
    current_offset = 0

    for page in pages:
        text = page["text"].strip()
        if not text:
            continue

        page_num = page["page_number"]
        start = current_offset
        combined_text_parts.append(text)
        current_offset += len(text) + 1  # +1 for the join separator
        page_boundaries.append((start, current_offset - 1, page_num))

    if not combined_text_parts:
        return []

    combined_text = "\n".join(combined_text_parts)

    # ── Split with LangChain RecursiveCharacterTextSplitter ───────────
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=TARGET_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,  # character-based splitting
        strip_whitespace=True,
    )

    raw_chunks = splitter.split_text(combined_text)

    # ── Map chunks back to page numbers and build output ──────────────
    chunks = []
    search_start = 0  # Track position for finding chunks in order

    for chunk_index, chunk_text in enumerate(raw_chunks):
        if not chunk_text.strip():
            continue

        # Find the position of this chunk in the combined text
        chunk_start = combined_text.find(chunk_text, search_start)
        if chunk_start == -1:
            # Fallback: search from beginning (can happen with overlaps)
            chunk_start = combined_text.find(chunk_text)
        if chunk_start == -1:
            # If still not found (very rare with strip), use midpoint heuristic
            chunk_start = search_start

        # Update search position (allow overlap by not jumping past full chunk)
        search_start = chunk_start + 1

        # Find the page number for the chunk's starting position
        page_number = page_boundaries[-1][2] if page_boundaries else 1
        for start, end, page_num in page_boundaries:
            if start <= chunk_start < end:
                page_number = page_num
                break

        chunks.append({
            "chunk_index": len(chunks),  # Sequential, gap-free indexing
            "chunk_text": chunk_text,
            "page_number": page_number,
            "section_type": _detect_section(chunk_text),
            "token_count": _count_tokens(chunk_text),
            "char_count": len(chunk_text),
        })

    return chunks