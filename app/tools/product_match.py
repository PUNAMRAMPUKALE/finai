# app/tools/product_match.py
from typing import Any, Dict, List

def product_match(*, profile_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal, dependency-free matcher. Returns a dict with 'products' and 'explanation'.
    This is intentionally simple so it can be imported and called from services/matching.py.
    """
    risk = str(profile_json.get("riskTolerance", "")).lower()
    goal = str(profile_json.get("investmentGoal", "")).lower()

    products: List[Dict[str, Any]] = []

    if risk in ("low", "conservative"):
        products.append({"ticker": "BND", "name": "Vanguard Total Bond Market ETF", "fee": 0.03})
        products.append({"ticker": "VWRA", "name": "Vanguard FTSE All-World UCITS ETF (Acc)", "fee": 0.22})
    elif risk in ("medium", "moderate"):
        products.append({"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "fee": 0.03})
        products.append({"ticker": "VXUS", "name": "Vanguard Total International Stock ETF", "fee": 0.07})
    else:
        products.append({"ticker": "QQQ", "name": "Invesco QQQ Trust", "fee": 0.20})
        products.append({"ticker": "VT", "name": "Vanguard Total World Stock ETF", "fee": 0.07})

    explanation = f"Matched for goal='{goal}', risk='{risk}'. Prioritized broad, low-fee funds."

    return {"products": products, "explanation": explanation}

__all__ = ["product_match"]
