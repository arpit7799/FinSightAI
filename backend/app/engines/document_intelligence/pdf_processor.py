# app/engines/document_intelligence/pdf_processor.py
"""
PDF text extraction using PyMuPDF (fitz).

This is the first step in the document pipeline.
It extracts raw text from each page of the uploaded PDF.
If the text is too short (scanned PDF), we flag it for OCR.
"""

import fitz  # PyMuPDF


# If average characters per page is below this, the PDF is probably scanned
OCR_THRESHOLD = 100


class PDFProcessor:
    """
    Extracts text and metadata from a PDF file using PyMuPDF.

    Usage:
        processor = PDFProcessor("path/to/file.pdf")
        result = processor.extract()
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def extract(self) -> dict:
        """
        Opens the PDF and extracts text from every page.

        Returns a dict with:
            - pages: list of { page_number, text, char_count }
            - page_count: total number of pages
            - full_text: all pages joined together
            - needs_ocr: True if text is too sparse (scanned PDF)
            - metadata: title, author, etc from PDF properties
        """
        doc = fitz.open(self.file_path)

        pages = []
        full_text = ""

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            pages.append({
                "page_number": page_num + 1,  # 1-indexed for humans
                "text": text,
                "char_count": len(text),
            })

            full_text += f"\n--- Page {page_num + 1} ---\n{text}"

        page_count = len(doc)
        metadata = doc.metadata  # title, author, creator, etc

        doc.close()

        # Check if PDF needs OCR
        total_chars = sum(p["char_count"] for p in pages)
        avg_chars_per_page = total_chars / page_count if page_count > 0 else 0
        needs_ocr = avg_chars_per_page < OCR_THRESHOLD

        return {
            "pages": pages,
            "page_count": page_count,
            "full_text": full_text,
            "needs_ocr": needs_ocr,
            "metadata": metadata,
            "avg_chars_per_page": avg_chars_per_page,
        }
