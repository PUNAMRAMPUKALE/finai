from typing import Dict, Any
from app.ml.embeddings import embed_text
from app.adapters.vector.weaviate_products import search_similar_in_products
from app.tools.product_match_llm import llm_select

def recommend(profile: Dict[str, Any], candidate_k: int = 12, top_n: int = 3):
    risk = profile.get("riskTolerance") or profile.get("risk") or ""
    goal = profile.get("investmentGoal") or profile.get("goal") or ""
    horizon = profile.get("horizonYears") or profile.get("horizon_years") or ""
    prefs = profile.get("preferences") or []
    cons  = profile.get("constraints") or []

    text = (
        f"goal={goal}; horizon={horizon} years; risk={risk}; "
        f"preferences={', '.join(prefs)}; constraints={', '.join(cons)}"
    )
    vec = embed_text(text)
    cands = search_similar_in_products(vec, limit=candidate_k)
    return llm_select(profile_text=text, candidates=cands, top_n=top_n)