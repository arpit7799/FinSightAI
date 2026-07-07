from pathlib import Path

import pdfplumber
import pytesseract
from docx import Document
from PIL import Image


class OCRService:

    @staticmethod
    def extract_text(file_path: Path) -> str:
        extension = file_path.suffix.lower()

        if extension == ".pdf":
            return OCRService._extract_pdf(file_path)

        if extension == ".docx":
            return OCRService._extract_docx(file_path)

        if extension in [".png", ".jpg", ".jpeg"]:
            return OCRService._extract_image(file_path)

        raise ValueError("Unsupported file type.")

    @staticmethod
    def _extract_pdf(file_path: Path) -> str:
        text = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    text += page_text + "\n"

        return text.strip()

    @staticmethod
    def _extract_docx(file_path: Path) -> str:
        document = Document(file_path)

        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    @staticmethod
    def _extract_image(file_path: Path) -> str:
        image = Image.open(file_path)

        return pytesseract.image_to_string(image).strip()