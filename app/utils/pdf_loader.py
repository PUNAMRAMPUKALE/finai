from __future__ import annotations

from io import BytesIO
from typing import Iterable, List, Tuple, Union

from pypdf import PdfReader


class PdfExtractError(Exception):
    pass


def pdf_to_text(file: Union[str, bytes, BytesIO]) -> str:
    """
    Read a PDF from path/bytes/BytesIO and return the full plain text.
    """
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
        raise PdfExtractError(f"Could not read PDF: {e}") from e


def _chunk_lines(lines: Iterable[str], max_chars: int = 1200) -> List[str]:
    """
    Very small, dependency-free chunker: packs lines into ~max_chars chunks.
    Keeps paragraphs intact when possible.
    """
    chunks: List[str] = []
    buf: List[str] = []
    size = 0

    for ln in lines:
        ln = (ln or "").rstrip()
        if not ln:
            # paragraph break helps readability
            ln = "\n"
        add = (len(ln) + 1)
        if size + add > max_chars and buf:
            chunks.append("\n".join(buf).strip())
            buf = [ln]
            size = add
        else:
            buf.append(ln)
            size += add

    if buf:
        chunks.append("\n".join(buf).strip())

    # drop any empty tails
    return [c for c in chunks if c]


def load_pdf_chunks(
    file: Union[str, bytes, BytesIO],
    max_chars: int = 1200,
) -> Tuple[List[str], int]:
    """
    Returns (chunks, page_count).
    - chunks: list[str] sized for embedding/RAG
    - page_count: number of pages detected
    """
    try:
        # Build a reader once to get page_count and page-wise text
        if isinstance(file, (bytes, bytearray)):
            reader = PdfReader(BytesIO(file))
        elif isinstance(file, str):
            with open(file, "rb") as f:
                reader = PdfReader(f)
        else:
            reader = PdfReader(file)

        page_count = len(reader.pages)
        lines: List[str] = []
        for p in reader.pages:
            txt = p.extract_text() or ""
            # keep a hard page divider to avoid accidental joins
            lines.extend(txt.splitlines())
            lines.append("")  # paragraph break between pages

        chunks = _chunk_lines(lines, max_chars=max_chars)
        return chunks, page_count
    except Exception as e:
        raise PdfExtractError(f"Could not chunk PDF: {e}") from e