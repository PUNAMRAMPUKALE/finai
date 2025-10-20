from typing import Union
from io import BytesIO
from pypdf import PdfReader

class PdfExtractError(Exception):
    pass

def pdf_to_text(file: Union[str, bytes, BytesIO]) -> str:
    try:
        if isinstance(file, (bytes, bytearray)):
            bio = BytesIO(file)
            reader = PdfReader(bio)
        elif isinstance(file, str):
            with open(file, "rb") as f:
                reader = PdfReader(f)
        else:
            reader = PdfReader(file)
        return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    except Exception as e:
        raise PdfExtractError(f"Could not read PDF: {e}")
