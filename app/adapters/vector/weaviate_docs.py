from typing import List, Dict
from .weaviate_client import get_client, DOCS

def insert_document(title: str, content: str, source: str, vector: list | None):
    coll = get_client().collections.get(DOCS)
    coll.data.insert({"title": title, "content": content, "source": source}, vector=vector)

def search_similar_in_docs(query_vector: list, limit: int = 5) -> List[Dict]:
    coll = get_client().collections.get(DOCS)
    res = coll.query.near_vector(query_vector, limit=limit, return_metadata=["distance"])
    out = []
    for o in res.objects:
        p = o.properties
        dist = getattr(o.metadata, "distance", None)
        out.append({"title": p.get("title"), "content": p.get("content"), "source": p.get("source"), "distance": dist})
    return out