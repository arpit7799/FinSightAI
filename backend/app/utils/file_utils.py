from pathlib import Path
from uuid import uuid4


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
}


def allowed_file(filename: str) -> bool:

    extension = Path(filename).suffix.lower()

    return extension in ALLOWED_EXTENSIONS


def generate_filename(filename: str) -> str:

    extension = Path(filename).suffix.lower()

    return f"{uuid4().hex}{extension}"