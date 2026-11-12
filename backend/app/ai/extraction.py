import re
from pathlib import Path

from pypdf import PdfReader
from docx import Document
from PIL import Image


MAX_FILE_CHARS = 20000
MAX_FILE_SIZE = 10 * 1024 * 1024

TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".html", ".py"
}

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp"
}


def extract_text(file_path: str) -> dict:
    path = Path(file_path)

    result = {
        "filename": path.name,
        "text": "",
        "supported": False,
        "truncated": False,
        "file_type": path.suffix.lower(),
    }

    try:
        if not path.is_file():
            result["error"] = "File not found."
            return result

        if path.stat().st_size > MAX_FILE_SIZE:
            result["error"] = "File exceeds 10 MB limit."
            return result

        extension = path.suffix.lower()

        if extension in IMAGE_EXTENSIONS:
            with Image.open(path) as image:
                image.verify()

            result["supported"] = True
            result["file_type"] = "image"
            return result

        if extension == ".pdf":
            reader = PdfReader(str(path))
            text = "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        elif extension == ".docx":
            document = Document(str(path))

            paragraphs = [
                paragraph.text
                for paragraph in document.paragraphs
            ]

            tables = [
                " ".join(cell.text for cell in row.cells)
                for table in document.tables
                for row in table.rows
            ]

            text = "\n".join(paragraphs + tables)

        elif extension in TEXT_EXTENSIONS:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            if extension == ".html":
                text = re.sub(r"<[^>]+>", " ", text)

        else:
            result["error"] = "Unsupported file format."
            return result

        result["truncated"] = len(text) > MAX_FILE_CHARS
        result["text"] = text[:MAX_FILE_CHARS]
        result["supported"] = True

        return result

    except Exception as exc:
        result["error"] = type(exc).__name__
        return result