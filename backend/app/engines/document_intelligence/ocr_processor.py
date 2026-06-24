# app/engines/document_intelligence/ocr_processor.py
"""
OCR fallback using PaddleOCR.

This runs ONLY when PDFProcessor detects the PDF is scanned
(very little extractable text). We convert each page to an image
and run OCR on it.
"""

import fitz  # PyMuPDF - used to convert PDF pages to images
from paddleocr import PaddleOCR
import numpy as np


class OCRProcessor:
    """
    Runs OCR on a scanned PDF by converting pages to images first.

    PaddleOCR is initialized once and reused across pages
    because loading the model is slow (~3-5 seconds).

    Usage:
        ocr = OCRProcessor("path/to/scanned.pdf")
        result = ocr.extract()
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        # use_angle_cls=True handles rotated text
        # lang='en' for English financial documents
        self.ocr_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    def extract(self) -> dict:
        """
        Converts each PDF page to an image, then runs OCR.

        Returns same format as PDFProcessor.extract() so the rest
        of the pipeline doesn't need to know which method was used.
        """
        doc = fitz.open(self.file_path)

        pages = []
        full_text = ""

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Convert page to image (matrix=2 means 2x zoom for better OCR accuracy)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)

            # Convert to numpy array for PaddleOCR
            img_array = np.frombuffer(pix.samples, dtype=np.uint8)
            img_array = img_array.reshape(pix.height, pix.width, pix.n)

            # Run OCR - returns list of [bbox, (text, confidence)]
            ocr_result = self.ocr_engine.ocr(img_array, cls=True)

            # Extract just the text from OCR results
            page_text = ""
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    text, confidence = line[1]
                    # Only include text with confidence > 60%
                    if confidence > 0.6:
                        page_text += text + " "

            pages.append({
                "page_number": page_num + 1,
                "text": page_text,
                "char_count": len(page_text),
            })

            full_text += f"\n--- Page {page_num + 1} ---\n{page_text}"

        doc.close()

        return {
            "pages": pages,
            "page_count": len(pages),
            "full_text": full_text,
            "needs_ocr": False,  # Already done OCR, no need to flag again
            "metadata": {},
            "extraction_method": "paddleocr",
        }
