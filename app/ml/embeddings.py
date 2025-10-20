from functools import lru_cache
from typing import List
from sentence_transformers import SentenceTransformer

@lru_cache(maxsize=1)
def _model():
    # small, fast, widely available
    return SentenceTransformer("all-MiniLM-L6-v2")

def embed_texts(texts: List[str]) -> List[list]:
    return _model().encode(texts, normalize_embeddings=True).tolist()

def embed_text(text: str) -> list:
    return embed_texts([text])[0]