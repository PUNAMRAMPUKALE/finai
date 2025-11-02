# app/ml/embeddings.py
from __future__ import annotations

from functools import lru_cache
from typing import List
import os

# Avoid tokenizer parallel warnings in production logs
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# You can switch models without touching code:
# export EMBEDDING_MODEL_NAME="mixedbread-ai/mxbai-embed-large-v1"  (or any sentence-transformers compatible model)
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

try:
    from sentence_transformers import SentenceTransformer
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "sentence-transformers is required. Install with: pip install sentence-transformers"
    ) from e


@lru_cache(maxsize=1)
def _model() -> "SentenceTransformer":
    """
    Lazily load the embedding model once per process.
    all-MiniLM-L6-v2 → 384-dim, fast, widely used for RAG.
    """
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts with L2-normalized vectors (cosine-ready).
    Returns a list of float vectors with unit length.
    """
    if not texts:
        return []
    # normalize_embeddings=True ensures vectors are unit length
    vecs = _model().encode(texts, normalize_embeddings=True)
    # Some backends return numpy arrays; convert to plain lists
    return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vecs]


def embed_text(text: str) -> List[float]:
    """
    Convenience wrapper to embed a single text; returns a unit-length vector.
    """
    return embed_texts([text])[0] if text else []
