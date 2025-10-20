# app/adapters/vector/weaviate_investors.py
from typing import List, Dict, Any
from .weaviate_client import get_client, INVESTOR

def _dist_to_pct(dist: float | None) -> int:
    if dist is None:
        return 0
    try:
        d = float(dist)
    except Exception:
        return 0
    # cosine distance ∈ [0,2] → higher is better after invert
    if d < 0: d = 0.0
    if d > 2: d = 2.0
    return int(round((1.0 - (d / 2.0)) * 100))

def insert_investor(i: Dict[str, Any], vector: list | None):
    coll = get_client().collections.get(INVESTOR)
    payload = {
        "name":        i.get("name", ""),
        "sectors":     i.get("sectors", ""),
        "stages":      i.get("stages", ""),
        "geo":         i.get("geo", ""),
        "checkSize":   i.get("checkSize", ""),
        "thesis":      i.get("thesis", ""),
        "constraints": i.get("constraints", ""),
    }
    coll.data.insert(payload, vector=vector)

def search_similar_investors(query_vector: list, limit: int = 10) -> List[Dict[str, Any]]:
    coll = get_client().collections.get(INVESTOR)
    # ask for both distance and certainty (if available)
    res = coll.query.near_vector(query_vector, limit=limit, return_metadata=["distance", "certainty"])

    out: List[Dict[str, Any]] = []
    for o in res.objects:
        p = o.properties
        dist = getattr(o.metadata, "distance", None)
        certainty = getattr(o.metadata, "certainty", None)  # 0..1 if enabled
        score_pct = int(round(float(certainty) * 100)) if certainty is not None else _dist_to_pct(dist)
        out.append({
            "name": p.get("name"),
            "sectors": p.get("sectors"),
            "stages": p.get("stages"),
            "geo": p.get("geo"),
            "checkSize": p.get("checkSize"),
            "thesis": p.get("thesis"),
            "constraints": p.get("constraints"),
            "distance": dist,
            "score_pct": score_pct,   # <-- add this
        })
    return out
