# app/adapters/vector/weaviate_investors.py
from __future__ import annotations

from typing import List, Dict, Any, Optional
from .weaviate_client import get_client, INVESTOR


def _dist_to_pct(dist: Optional[float]) -> int:
    """
    Convert cosine distance in [0, 2] to a 0..100 "match %" where higher = better.
    If distance is None or invalid, return 0.
    """
    if dist is None:
        return 0
    try:
        d = float(dist)
    except Exception:
        return 0
    # clamp into valid range
    if d < 0:
        d = 0.0
    if d > 2:
        d = 2.0
    return int(round((1.0 - (d / 2.0)) * 100))


def insert_investor(i: Dict[str, Any], vector: Optional[list]) -> None:
    """
    Insert a single investor object with an optional precomputed vector.
    Expected keys on `i`: name, sectors, stages, geo, checkSize, thesis, constraints, profile (optional).
    """
    coll = get_client().collections.get(INVESTOR)
    payload = {
        "name":        i.get("name", ""),
        "sectors":     i.get("sectors", ""),
        "stages":      i.get("stages", ""),
        "geo":         i.get("geo", ""),
        "checkSize":   i.get("checkSize", ""),
        "thesis":      i.get("thesis", ""),
        "constraints": i.get("constraints", ""),
        "profile":     i.get("profile", ""),   # long-form text used by RAG (optional)
    }
    coll.data.insert(payload, vector=vector)


def get_investor_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single investor by exact name. Returns a dict of fields or None if not found.
    """
    coll = get_client().collections.get(INVESTOR)

    # v4 Python SDK filter structure
    filt = {
        "operator": "Equal",
        "path": ["name"],
        "valueText": name,
    }

    res = coll.query.fetch_objects(
        limit=1,
        filters=filt,
    )

    if not res.objects:
        return None

    p = res.objects[0].properties
    return {
        "name":        p.get("name"),
        "sectors":     p.get("sectors"),
        "stages":      p.get("stages"),
        "geo":         p.get("geo"),
        "checkSize":   p.get("checkSize"),
        "thesis":      p.get("thesis"),
        "constraints": p.get("constraints"),
        "profile":     p.get("profile"),
    }


def search_similar_investors(query_vector: list, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Vector search for nearest investors. Returns a list of dicts with properties plus:
      - distance: cosine distance (if returned by Weaviate)
      - score_pct: 0..100 percentage where higher is better
    The percentage is computed as:
      - if 'certainty' was returned by Weaviate → score_pct = round(certainty * 100)
      - else fallback to distance via a monotonic transform (see _dist_to_pct)
    """
    coll = get_client().collections.get(INVESTOR)

    # --- IMPORTANT LINE YOU ASKED TO ADD ---
    # ask Weaviate to return both distance and certainty in metadata.
    # (certainty may be None depending on the configured distance/certainty settings)
    res = coll.query.near_vector(
        query_vector,
        limit=limit,
        return_metadata=["distance", "certainty"],
    )

    out: List[Dict[str, Any]] = []
    for o in res.objects:
        p = o.properties or {}
        dist = getattr(o.metadata, "distance", None)
        certainty = getattr(o.metadata, "certainty", None)  # 0..1 if available

        # --- REQUESTED BEHAVIOR ---
        # Ensure score_pct always exists when either distance or certainty is returned.
        score_pct = (
            int(round(float(certainty) * 100))
            if certainty is not None
            else _dist_to_pct(dist)
        )

        out.append({
            "name":        p.get("name"),
            "sectors":     p.get("sectors"),
            "stages":      p.get("stages"),
            "geo":         p.get("geo"),
            "checkSize":   p.get("checkSize"),
            "thesis":      p.get("thesis"),
            "constraints": p.get("constraints"),
            # RAG long text is not necessary in the match list, but keep if you want it upstream:
            # "profile":     p.get("profile"),
            "distance":    dist,
            "score_pct":   score_pct,
        })

    return out