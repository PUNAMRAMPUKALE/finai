from typing import List, Tuple
import numpy as np
from app.ml.embeddings import embed_texts

def rerank_pairs(pairs: List[Tuple[str, str]]) -> List[float]:
    """
    Returns similarity in [0,1] for each (query, doc) pair.
    We use normalized ST embeddings → dot product == cosine ∈ [-1,1].
    Scale to [0,1] for 'higher is better'.
    """
    if not pairs:
        return []
    q_texts = [q for q, _ in pairs]
    d_texts = [d for _, d in pairs]
    q_vecs = np.array(embed_texts(q_texts))  # normalized
    d_vecs = np.array(embed_texts(d_texts))  # normalized
    cos = np.sum(q_vecs * d_vecs, axis=1)    # [-1, 1]
    sim01 = (cos + 1.0) / 2.0                # [0, 1]
    return sim01.tolist()