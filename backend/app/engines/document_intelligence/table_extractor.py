# app/engines/document_intelligence/table_extractor.py
"""
Financial table extraction using pdfplumber.

pdfplumber is better than PyMuPDF for tables because it understands
cell boundaries. We use PyMuPDF for text and pdfplumber for tables.

This extracts ALL tables from the PDF, then we filter down to
the ones that look like financial statements.
"""

import pdfplumber


# A table must have at least this many rows to be worth looking at
MIN_ROWS = 3

# At least this fraction of cells should contain numbers
# to be considered a financial table
MIN_NUMERIC_RATIO = 0.2


def _is_numeric(value: str) -> bool:
    """Check if a cell value looks like a number."""
    if not value:
        return False
    # Remove common financial formatting
    cleaned = value.replace(",", "").replace("(", "").replace(")", "")
    cleaned = cleaned.replace("%", "").replace("₹", "").replace("$", "").strip()
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def _looks_like_financial_table(table: list) -> bool:
    """
    Check if a table looks like a financial statement.
    Financial tables have a mix of text labels and numbers.
    """
    if len(table) < MIN_ROWS:
        return False

    # Count how many cells have numbers
    total_cells = 0
    numeric_cells = 0

    for row in table:
        for cell in row:
            if cell is not None:
                total_cells += 1
                if _is_numeric(str(cell)):
                    numeric_cells += 1

    if total_cells == 0:
        return False

    numeric_ratio = numeric_cells / total_cells
    return numeric_ratio >= MIN_NUMERIC_RATIO


class TableExtractor:
    """
    Extracts financial tables from a PDF using pdfplumber.

    Usage:
        extractor = TableExtractor("path/to/file.pdf")
        tables = extractor.extract()
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def extract(self) -> list:
        """
        Scans every page for tables and returns the ones that
        look like financial statements.

        Returns a list of dicts:
            - page_number: which page the table was on
            - rows: the table as a list of rows (each row is a list of cells)
            - row_count: number of rows
            - col_count: number of columns
        """
        financial_tables = []

        with pdfplumber.open(self.file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract all tables from this page
                tables = page.extract_tables()

                if not tables:
                    continue

                for table in tables:
                    # Skip tables that don't look financial
                    if not _looks_like_financial_table(table):
                        continue

                    # Clean up None values
                    cleaned_rows = []
                    for row in table:
                        cleaned_row = [
                            str(cell).strip() if cell is not None else ""
                            for cell in row
                        ]
                        cleaned_rows.append(cleaned_row)

                    financial_tables.append({
                        "page_number": page_num + 1,
                        "rows": cleaned_rows,
                        "row_count": len(cleaned_rows),
                        "col_count": len(cleaned_rows[0]) if cleaned_rows else 0,
                    })

        return financial_tables
