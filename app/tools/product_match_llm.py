# app/tools/product_match.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple
import json
import re

from app.services.embeddings import embed_text
from app.services.weaviate_db import search_similar_in_products
from app.services.openai_client import chat_complete


def _profile_to_text(profile: Dict[str, Any]) -> str:
    """
    Accepts both shapes:
    - { risk, goal, horizon_years, preferences[], constraints[] }
    - { riskTolerance, investmentGoal, horizonYears, preferences[], constraints[] }
    """
    risk = (profile.get("riskTolerance") or profile.get("risk") or "").lower()
    goal = (profile.get("investmentGoal") or profile.get("goal") or "").lower()
    horizon = profile.get("horizonYears") or profile.get("horizon_years") or ""
    prefs = profile.get("preferences") or []
    cons = profile.get("constraints") or []
    return (
        f"goal={goal}; horizon={horizon} years; risk={risk}; "
        f"preferences={', '.join(map(str, prefs))}; constraints={', '.join(map(str, cons))}"
    )


def _llm_select(profile_text: str, candidates: List[Dict[str, Any]], top_n: int = 3) -> Tuple[List[Dict[str, Any]], str]:
    """
    Ask the LLM to pick the best products for the profile from retrieved candidates.
    Returns (products, explanation).
    """
    # Keep candidate payload lean to fit context comfortably.
    compact = [
        {
            "id": c.get("productId") or c.get("id") or c.get("name"),
            "name": c.get("name"),
            "type": c.get("type"),
            "region": c.get("region"),
            "fees": c.get("fees"),
            "riskLabel": c.get("riskLabel"),
            "terms": (c.get("terms") or "")[:400],
            "description": (c.get("description") or "")[:400],
            "distance": c.get("distance"),
        }
        for c in candidates
    ]

    system = (
        "You are a fiduciary-quality investment assistant. "
        "Choose diversified, suitable products that match the user's risk, goal, horizon, and constraints. "
        "Prefer lower fees when quality is similar. Output STRICT JSON only."
    )

    user = f"""User Profile (text):
{profile_text}

Candidate Products (JSON list):
{json.dumps(compact, ensure_ascii=False, indent=2)}

Task:
Return STRICT JSON with this schema (no extra text):

{{
  "products": [
    {{
      "id": "string",
      "name": "string",
      "why": "1–3 bullet sentences",
      "score": 0-100
    }}
  ],
  "explanation": "Short paragraph explaining the selection and tradeoffs"
}}

Rules:
- Select the top {top_n} products max.
- Be specific about risk/fees/region.
- Do not invent products; only choose from candidates.
- JSON only. No markdown, no commentary.
"""

    raw = chat_complete(
        prompt=f"{system}\n\n{user}",
    )

    # Robust JSON extraction (LLMs occasionally wrap).
    match = re.search(r"\{.*\}\s*$", raw, flags=re.S)
    text = match.group(0) if match else raw
    try:
        data = json.loads(text)
        products = data.get("products", [])
        explanation = data.get("explanation", "")
        # normalize fields
        out = []
        for p in products[:top_n]:
            out.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "why": p.get("why") or "",
                "score": float(p.get("score") or 0),
            })
        return out, explanation
    except Exception:
        # If parsing fails, degrade gracefully with a minimal message.
        return [], "LLM could not produce valid JSON."
    

def product_match(*, profile_json: Dict[str, Any], candidate_k: int = 12, top_n: int = 3) -> Dict[str, Any]:
    """
    LLM-based product match:
    1) embed profile text
    2) retrieve candidates from Weaviate
    3) LLM selects top-N and explains
    """
    profile_text = _profile_to_text(profile_json)
    vec = embed_text(profile_text)
    candidates = search_similar_in_products(vec, limit=candidate_k) or []
    selected, explanation = _llm_select(profile_text, candidates, top_n=top_n)

    return {
        "products": selected,
        "explanation": explanation,
        "candidate_count": len(candidates),
    }


__all__ = ["product_match"]