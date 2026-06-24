# app/engines/document_intelligence/statement_classifier.py
"""
Classifies extracted tables into Balance Sheet, Income Statement,
or Cash Flow Statement using keyword matching.

No ML needed here - keyword rules work well enough and are
fully explainable (important for financial applications).
"""


# Keywords that strongly indicate each statement type.
# We check if these appear in the table's text content.
BALANCE_SHEET_KEYWORDS = [
    "total assets",
    "total liabilities",
    "shareholders equity",
    "stockholders equity",
    "equity",
    "non-current assets",
    "current assets",
    "current liabilities",
    "non-current liabilities",
    "retained earnings",
    "share capital",
    "reserves and surplus",
    "fixed assets",
    "capital employed",
]

INCOME_STATEMENT_KEYWORDS = [
    "revenue from operations",
    "total revenue",
    "net revenue",
    "net sales",
    "gross profit",
    "operating profit",
    "profit before tax",
    "profit after tax",
    "net income",
    "earnings per share",
    "ebitda",
    "cost of goods sold",
    "cost of revenue",
    "operating expenses",
    "income from operations",
]

CASH_FLOW_KEYWORDS = [
    "operating activities",
    "investing activities",
    "financing activities",
    "cash and cash equivalents",
    "net cash",
    "cash flow from",
    "capital expenditure",
    "proceeds from",
    "repayment of",
]


def _get_table_text(table: dict) -> str:
    """Join all cell values in a table into one lowercase string for matching."""
    all_text = ""
    for row in table["rows"]:
        all_text += " ".join(row).lower() + " "
    return all_text


def _count_keyword_matches(table_text: str, keywords: list) -> int:
    """Count how many keywords from the list appear in the table text."""
    return sum(1 for keyword in keywords if keyword in table_text)


def classify_table(table: dict) -> str | None:
    """
    Classify a single table as one of:
        - "BALANCE_SHEET"
        - "INCOME_STATEMENT"
        - "CASH_FLOW_STATEMENT"
        - None (not a financial statement we recognize)

    We count keyword matches for each type and pick the winner.
    Requires at least 2 matches to avoid false positives.
    """
    table_text = _get_table_text(table)

    bs_score = _count_keyword_matches(table_text, BALANCE_SHEET_KEYWORDS)
    is_score = _count_keyword_matches(table_text, INCOME_STATEMENT_KEYWORDS)
    cf_score = _count_keyword_matches(table_text, CASH_FLOW_KEYWORDS)

    # Need at least 2 keyword matches to be confident
    if max(bs_score, is_score, cf_score) < 2:
        return None

    # Pick the statement type with the most keyword matches
    scores = {
        "BALANCE_SHEET": bs_score,
        "INCOME_STATEMENT": is_score,
        "CASH_FLOW_STATEMENT": cf_score,
    }

    return max(scores, key=scores.get)


def classify_all_tables(tables: list) -> list:
    """
    Classify all extracted tables.

    Returns the same tables but with a 'statement_type' field added.
    Tables that can't be classified are excluded.

    If multiple tables classify as the same type, we keep the one
    with more rows (likely the more complete statement).
    """
    classified = {}

    for table in tables:
        statement_type = classify_table(table)

        if statement_type is None:
            continue

        # Keep only the largest table for each statement type
        if statement_type not in classified:
            classified[statement_type] = {**table, "statement_type": statement_type}
        else:
            # Replace if this table has more rows
            if table["row_count"] > classified[statement_type]["row_count"]:
                classified[statement_type] = {**table, "statement_type": statement_type}

    return list(classified.values())
