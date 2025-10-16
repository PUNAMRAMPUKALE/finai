from typing import List, Dict, Any
from .weaviate_client import get_client, PROD

def insert_product(prod: Dict[str, Any], vector: list | None):
    coll = get_client().collections.get(PROD)
    payload = {
        "productId": prod.get("productId") or prod.get("id") or prod.get("name"),
        "name": prod.get("name", ""),
        "type": prod.get("type", ""),
        "terms": (prod.get("terms", "") + " " + prod.get("description", "")).strip(),
        "fees": prod.get("fees", ""),
        "eligibility": prod.get("eligibility", ""),
        "region": prod.get("region", ""),
        "riskLabel": prod.get("riskLabel", ""),
        "description": prod.get("description", ""),
    }
    coll.data.insert(payload, vector=vector)

def search_similar_in_products(query_vector: list, limit: int = 5):
    coll = get_client().collections.get(PROD)
    res = coll.query.near_vector(query_vector, limit=limit, return_metadata=["distance"])
    items = []
    for o in res.objects:
        p = o.properties
        dist = getattr(o.metadata, "distance", None)
        items.append({
            "productId": p.get("productId"),
            "name": p.get("name"),
            "type": p.get("type"),
            "terms": p.get("terms"),
            "fees": p.get("fees"),
            "eligibility": p.get("eligibility"),
            "region": p.get("region"),
            "riskLabel": p.get("riskLabel"),
            "description": p.get("description"),
            "distance": dist,
        })
    return items