# tests/unit/test_document_intelligence.py
"""
Unit tests for Phase 4 document intelligence components.

These tests don't need a real PDF or database.
We test the logic in isolation using small fake inputs.
"""

import pytest
from app.engines.document_intelligence.statement_classifier import (
    classify_table,
    classify_all_tables,
)
from app.engines.document_intelligence.data_normalizer import (
    _clean_label,
    _parse_number,
    normalize_table,
)


# ── Fake table fixtures ───────────────────────────────────────────────────────

def make_table(rows: list, page: int = 1) -> dict:
    """Helper to create a table dict like TableExtractor produces."""
    return {
        "page_number": page,
        "rows": rows,
        "row_count": len(rows),
        "col_count": len(rows[0]) if rows else 0,
    }


# ── StatementClassifier tests ─────────────────────────────────────────────────

class TestStatementClassifier:

    def test_classifies_balance_sheet(self):
        table = make_table([
            ["Particulars", "2023", "2022"],
            ["Total Assets", "3,200,000", "2,800,000"],
            ["Current Assets", "890,000", "750,000"],
            ["Total Liabilities", "1,800,000", "1,500,000"],
            ["Shareholders Equity", "1,400,000", "1,300,000"],
        ])
        assert classify_table(table) == "BALANCE_SHEET"

    def test_classifies_income_statement(self):
        table = make_table([
            ["Particulars", "2023", "2022"],
            ["Total Revenue", "1,250,000", "1,050,000"],
            ["Gross Profit", "470,000", "380,000"],
            ["Net Income", "198,000", "165,000"],
            ["Earnings Per Share", "25.5", "21.2"],
        ])
        assert classify_table(table) == "INCOME_STATEMENT"

    def test_classifies_cash_flow(self):
        table = make_table([
            ["Particulars", "2023", "2022"],
            ["Net Cash from Operating Activities", "280,000", "240,000"],
            ["Net Cash used in Investing Activities", "(150,000)", "(120,000)"],
            ["Net Cash from Financing Activities", "(80,000)", "(70,000)"],
            ["Cash and Cash Equivalents", "210,000", "160,000"],
        ])
        assert classify_table(table) == "CASH_FLOW_STATEMENT"

    def test_returns_none_for_non_financial_table(self):
        table = make_table([
            ["Name", "Department", "Location"],
            ["John", "Engineering", "Mumbai"],
            ["Jane", "Finance", "Delhi"],
        ])
        assert classify_table(table) is None

    def test_classify_all_returns_only_financial_tables(self):
        financial_table = make_table([
            ["Particulars", "2023"],
            ["Total Revenue", "1,250,000"],
            ["Net Income", "198,000"],
            ["Gross Profit", "470,000"],
        ])
        random_table = make_table([
            ["Name", "City"],
            ["Alice", "Delhi"],
        ])
        result = classify_all_tables([financial_table, random_table])
        assert len(result) == 1
        assert result[0]["statement_type"] == "INCOME_STATEMENT"

    def test_keeps_largest_table_when_duplicates(self):
        """When two tables classify as the same type, keep the bigger one."""
        small_bs = make_table([
            ["Total Assets", "3,200,000"],
            ["Total Liabilities", "1,800,000"],
            ["Shareholders Equity", "1,400,000"],
        ])
        large_bs = make_table([
            ["Total Assets", "3,200,000"],
            ["Current Assets", "890,000"],
            ["Non-current Assets", "2,310,000"],
            ["Total Liabilities", "1,800,000"],
            ["Current Liabilities", "560,000"],
            ["Shareholders Equity", "1,400,000"],
        ])
        result = classify_all_tables([small_bs, large_bs])
        assert len(result) == 1
        assert result[0]["row_count"] == 6  # larger table kept


# ── DataNormalizer tests ──────────────────────────────────────────────────────

class TestDataNormalizer:

    def test_clean_label_lowercases_and_strips(self):
        assert _clean_label("  Total Revenue  ") == "total revenue"
        assert _clean_label("NET INCOME") == "net income"

    def test_clean_label_collapses_extra_spaces(self):
        assert _clean_label("total   assets") == "total assets"

    def test_parse_number_handles_commas(self):
        assert _parse_number("1,25,000") == 125000.0

    def test_parse_number_handles_parentheses_as_negative(self):
        assert _parse_number("(45,678)") == -45678.0

    def test_parse_number_handles_currency_symbols(self):
        assert _parse_number("₹1,250") == 1250.0
        assert _parse_number("$98,000") == 98000.0

    def test_parse_number_returns_none_for_empty(self):
        assert _parse_number("") is None
        assert _parse_number("-") is None
        assert _parse_number(None) is None

    def test_parse_number_returns_none_for_text(self):
        assert _parse_number("N/A") is None
        assert _parse_number("Revenue") is None

    def test_normalize_income_statement_table(self):
        table = make_table([
            ["Particulars", "FY2023", "FY2022"],
            ["Total Revenue", "1,250,000", "1,050,000"],
            ["Net Income", "198,000", "165,000"],
            ["Gross Profit", "470,000", "380,000"],
        ])
        table["statement_type"] = "INCOME_STATEMENT"

        result = normalize_table(table)

        assert "total_revenue" in result
        assert result["total_revenue"] == 1250000.0
        assert "net_income" in result
        assert result["net_income"] == 198000.0
        assert "gross_profit" in result

    def test_normalize_skips_unknown_labels(self):
        table = make_table([
            ["Some Random Label", "999,999"],
            ["Total Revenue", "500,000"],
        ])
        table["statement_type"] = "INCOME_STATEMENT"

        result = normalize_table(table)
        # Only known labels should be in result
        assert "total_revenue" in result
        assert len(result) == 1  # "Some Random Label" was skipped

    def test_normalize_picks_first_year_value(self):
        """Should pick the first numeric column (current year), not prior year."""
        table = make_table([
            ["Particulars", "FY2023", "FY2022"],
            ["Net Income", "198,000", "165,000"],
        ])
        table["statement_type"] = "INCOME_STATEMENT"

        result = normalize_table(table)
        assert result["net_income"] == 198000.0  # Not 165000

    def test_normalize_handles_pat_abbreviation(self):
        """PAT (Profit After Tax) is common in Indian annual reports."""
        table = make_table([
            ["PAT", "85,000"],
            ["Total Revenue", "500,000"],
        ])
        table["statement_type"] = "INCOME_STATEMENT"

        result = normalize_table(table)
        assert "net_income" in result
        assert result["net_income"] == 85000.0
