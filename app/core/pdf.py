# app/core/pdf.py
from typing import Union
from io import BytesIO
from pypdf import PdfReader  # pypdf is the modern package

def pdf_to_text(content: Union[bytes, BytesIO]) -> str:
    bio = BytesIO(content) if isinstance(content, bytes) else content
    reader = PdfReader(bio)
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(texts).strip()