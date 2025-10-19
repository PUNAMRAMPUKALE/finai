# app/adapters/vector/weaviate_investors.py
from typing import List, Dict, Any
from app.adapters.vector.weaviate_client import get_client, INVESTOR

def insert_investor(i: Dict[str, Any], vector: list | None):
    coll = get_client().collections.get(INVESTOR)
    payload = {
        "name": i["name"],
        "sectors": i.get("sectors",""),
        "stages": i.get("stages",""),
        "geo": i.get("geo",""),
        "checkSize": i.get("checkSize",""),
        "thesis": i.get("thesis",""),
        "constraints": i.get("constraints",""),
    }
    coll.data.insert(payload, vector=vector)

def search_similar_in_investors(query_vector: list, limit: int = 10) -> List[Dict[str, Any]]:
    coll = get_client().collections.get(INVESTOR)
    res = coll.query.near_vector(query_vector, limit=limit, return_metadata=["distance"])
    out: List[Dict[str, Any]] = []
    for o in res.objects:
        p = o.properties
        dist = getattr(o.metadata, "distance", None)
        out.append({**p, "distance": dist})
    return out