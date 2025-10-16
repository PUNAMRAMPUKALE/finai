# app/utils/text_chunker.py
def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150):
    """
    Breaks long text into overlapping chunks so search works well.
    max_chars: size of each piece
    overlap: few characters repeated to keep context between pieces
    """
    text = text.strip().replace("\x00", " ")
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(i + max_chars, n)
        chunks.append(text[i:j])
        # step forward but keep a small overlap
        i = j - overlap if j < n else j
        if i < 0:
            i = 0
    return chunks
