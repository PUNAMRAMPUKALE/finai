from typing import List, Dict
from .weaviate_client import get_client, DOCS
from app.core.logging import get_logger

log = get_logger("weaviate.docs")

def insert_document(title: str, content: str, source: str, vector: list | None):
    coll = get_client().collections.get(DOCS)
    try:
        coll.data.insert({"title": title, "content": content, "source": source}, vector=vector)
    except Exception:
        log.exception("weaviate_insert_document_failed", extra={"title": title, "source": source})
        raise

def search_similar_in_docs(query_vector: list, limit: int = 5) -> List[Dict]:
    coll = get_client().collections.get(DOCS)
    try:
        res = coll.query.near_vector(query_vector, limit=limit, return_metadata=["distance"])
    except Exception:
        log.exception("weaviate_search_docs_failed", extra={"limit": limit})
        raise

    out = []
    for o in res.objects:
        p = o.properties
        dist = getattr(o.metadata, "distance", None)
        out.append({"title": p.get("title"), "content": p.get("content"), "source": p.get("source"), "distance": dist})
    return out
