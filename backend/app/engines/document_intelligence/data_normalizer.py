# app/engines/document_intelligence/data_normalizer.py
"""
Normalizes raw extracted table data into standard financial key-value pairs.

Indian annual reports use many different labels for the same line item.
For example "Revenue from Operations", "Net Sales", "Total Revenue" all
mean the same thing. This maps all variations to one standard key.

The output of this module is what the Financial Ratio Calculator uses.
"""

import re


# Maps various label variations → standard key
# Indian companies (Tata, Infosys, etc.) use these terms heavily
INCOME_STATEMENT_MAP = {
    # Revenue
    "revenue from operations": "total_revenue",
    "net revenue": "total_revenue",
    "net sales": "total_revenue",
    "total revenue": "total_revenue",
    "sales": "total_revenue",
    "turnover": "total_revenue",
    "income from operations": "total_revenue",

    # Cost
    "cost of goods sold": "cost_of_goods_sold",
    "cost of revenue": "cost_of_goods_sold",
    "cost of materials consumed": "cost_of_goods_sold",
    "cost of sales": "cost_of_goods_sold",
    "direct costs": "cost_of_goods_sold",

    # Gross profit
    "gross profit": "gross_profit",

    # Operating
    "ebitda": "ebitda",
    "operating profit": "ebitda",
    "profit before interest and tax": "ebitda",

    # Depreciation
    "depreciation": "depreciation_amortization",
    "depreciation and amortization": "depreciation_amortization",
    "depreciation & amortization": "depreciation_amortization",

    # EBIT
    "ebit": "ebit",
    "profit before interest": "ebit",

    # Interest
    "interest expense": "interest_expense",
    "finance costs": "interest_expense",
    "interest and finance charges": "interest_expense",
    "borrowing costs": "interest_expense",

    # Net income
    "net income": "net_income",
    "profit after tax": "net_income",
    "pat": "net_income",
    "profit for the year": "net_income",
    "profit for the period": "net_income",
    "net profit": "net_income",

    # Tax
    "income tax": "income_tax",
    "tax expense": "income_tax",
    "provision for taxation": "income_tax",

    # EPS
    "earnings per share": "eps",
    "basic eps": "eps",
    "eps": "eps",
}

BALANCE_SHEET_MAP = {
    # Assets
    "total assets": "total_assets",
    "total assets": "total_assets",
    "fixed assets": "fixed_assets",
    "property plant and equipment": "fixed_assets",
    "tangible assets": "fixed_assets",

    # Current assets
    "current assets": "current_assets",
    "total current assets": "current_assets",

    # Cash
    "cash and cash equivalents": "cash_and_equivalents",
    "cash and bank balances": "cash_and_equivalents",
    "cash": "cash_and_equivalents",

    # Receivables
    "trade receivables": "accounts_receivable",
    "accounts receivable": "accounts_receivable",
    "debtors": "accounts_receivable",
    "sundry debtors": "accounts_receivable",

    # Inventory
    "inventories": "inventory",
    "inventory": "inventory",
    "stock in trade": "inventory",

    # Liabilities
    "total liabilities": "total_liabilities",
    "current liabilities": "current_liabilities",
    "total current liabilities": "current_liabilities",
    "non-current liabilities": "non_current_liabilities",

    # Debt
    "long-term borrowings": "total_debt",
    "short-term borrowings": "short_term_debt",
    "borrowings": "total_debt",
    "total debt": "total_debt",

    # Equity
    "total equity": "total_equity",
    "shareholders equity": "total_equity",
    "stockholders equity": "total_equity",
    "net worth": "total_equity",

    # Retained earnings
    "retained earnings": "retained_earnings",
    "reserves and surplus": "retained_earnings",
}

CASH_FLOW_MAP = {
    "net cash from operating activities": "operating_cash_flow",
    "cash from operations": "operating_cash_flow",
    "operating cash flow": "operating_cash_flow",
    "net cash used in investing activities": "investing_cash_flow",
    "investing activities": "investing_cash_flow",
    "net cash from financing activities": "financing_cash_flow",
    "financing activities": "financing_cash_flow",
    "capital expenditure": "capex",
    "capex": "capex",
    "purchase of fixed assets": "capex",
}

# Combined map for convenience
ALL_MAPS = {
    "INCOME_STATEMENT": INCOME_STATEMENT_MAP,
    "BALANCE_SHEET": BALANCE_SHEET_MAP,
    "CASH_FLOW_STATEMENT": CASH_FLOW_MAP,
}


def _clean_label(label: str) -> str:
    """Lowercase, strip whitespace, remove extra spaces."""
    return re.sub(r"\s+", " ", label.lower().strip())


def _parse_number(value: str) -> float | None:
    """
    Convert a string like "1,23,456.78" or "(45,678)" to a float.
    Handles Indian number formatting and parentheses for negatives.
    """
    if not value or value.strip() == "-" or value.strip() == "":
        return None

    is_negative = "(" in value  # Accountants use (123) for -123

    # Remove everything except digits and decimal point
    cleaned = re.sub(r"[^\d.]", "", value)

    if not cleaned:
        return None

    try:
        number = float(cleaned)
        return -number if is_negative else number
    except ValueError:
        return None


def normalize_table(table: dict) -> dict:
    """
    Convert a classified financial table into a standard key-value dict.

    The table has rows like:
        ["Total Revenue", "125,000", "98,000"]
        ["Net Income", "18,500", "14,200"]

    We return:
        {"total_revenue": 125000.0, "net_income": 18500.0}

    We pick the FIRST numeric column (usually current year).
    """
    statement_type = table.get("statement_type")
    label_map = ALL_MAPS.get(statement_type, {})

    normalized = {}

    for row in table["rows"]:
        if not row or len(row) < 2:
            continue

        # First cell is usually the label
        label = _clean_label(row[0])

        # Find the standard key for this label
        standard_key = label_map.get(label)
        if not standard_key:
            continue

        # Find the first numeric value in the row (skip label column)
        for cell in row[1:]:
            number = _parse_number(str(cell))
            if number is not None:
                normalized[standard_key] = number
                break  # Use first valid number (current year)

    return normalized


def normalize_all_statements(classified_tables: list) -> dict:
    """
    Normalize all classified tables.

    Returns a dict keyed by statement type:
        {
            "BALANCE_SHEET": {"total_assets": 3200000, ...},
            "INCOME_STATEMENT": {"total_revenue": 1250000, ...},
            "CASH_FLOW_STATEMENT": {"operating_cash_flow": 280000, ...},
        }
    """
    result = {}

    for table in classified_tables:
        statement_type = table.get("statement_type")
        if not statement_type:
            continue

        normalized = normalize_table(table)

        if normalized:  # Only include if we extracted something
            result[statement_type] = {
                "normalized_data": normalized,
                "raw_data": {"rows": table["rows"]},
                "page_number": table.get("page_number"),
                "extraction_confidence": _calculate_confidence(normalized, statement_type),
            }

    return result


def _calculate_confidence(normalized: dict, statement_type: str) -> float:
    """
    Estimate how complete the extraction was.
    Checks how many of the expected key fields were found.
    """
    # Key fields we expect for each statement type
    expected_keys = {
        "INCOME_STATEMENT": ["total_revenue", "gross_profit", "net_income"],
        "BALANCE_SHEET": ["total_assets", "total_equity", "current_assets"],
        "CASH_FLOW_STATEMENT": ["operating_cash_flow"],
    }

    expected = expected_keys.get(statement_type, [])
    if not expected:
        return 0.5  # Unknown type, moderate confidence

    found = sum(1 for key in expected if key in normalized)
    return round(found / len(expected), 2)
