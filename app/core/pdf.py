# app/utils/pdf_loader.py
from pypdf import PdfReader

def pdf_to_text(path: str) -> str:
    """
    Opens a PDF and returns all text in order.
    Works fine for 10–20 (or more) pages.
    """
    reader = PdfReader(path)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)
