# app/services/embeddings.py
from sentence_transformers import SentenceTransformer
from functools import lru_cache
from typing import List

@lru_cache(maxsize=1)
def _model():
    """
    Loads a small, good-quality model once (fast & free to run locally).
    """
    return SentenceTransformer("all-MiniLM-L6-v2")

def embed_texts(texts: List[str]) -> List[list]:
    """
    Turns a list of texts into vectors (numbers) for searching.
    """
    return _model().encode(texts, normalize_embeddings=True).tolist()

def embed_text(text: str) -> list:
    return embed_texts([text])[0]
