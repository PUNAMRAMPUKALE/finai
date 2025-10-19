# app/utils/pdf_loader.py
from typing import Union
from io import BytesIO
from PyPDF2 import PdfReader

def pdf_to_text(file: Union[str, BytesIO]) -> str:
    """
    Extracts text from a PDF file path or file-like object.
    Works for uploaded FastAPI files or local files.
    """
    text = ""
    if isinstance(file, str):
        with open(file, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    else:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text.strip()