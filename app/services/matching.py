# app/services/matching.py
from __future__ import annotations
from typing import Any, Dict, List
import json
from typing import Any, Dict, List, Optional
from app.tools.product_match import product_match  # <-- this exists

def find_top_products_for_profile(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Returns only the list of matched products for the given profile.
    """
    result = product_match(profile_json=profile)
    return result.get("products", [])

def explain_recommendations(
    profile: Dict[str, Any],
    products: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Return a natural-language explanation. Accepts an optional `products`
    argument so callers can pass already-computed hits.
    """
    # We rely on the LLM/tool's own explanation for consistency.
    result = product_match(profile_json=profile)
    return result.get("explanation", "No explanation available.")

def product_match_json_for_profile(profile: Dict[str, Any]) -> str:
    """
    Returns the full product_match output as a JSON string.
    Used by the Crew route that interpolates {product_match_json}.
    """
    result = product_match(profile_json=profile)
    return json.dumps(result)

__all__ = [
    "find_top_products_for_profile",
    "explain_recommendations",
    "product_match_json_for_profile",
]